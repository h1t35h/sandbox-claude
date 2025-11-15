"""
Main CLI interface for sandbox-claude.
"""

import os
import sys
from builtins import list as builtin_list
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from docker.models.containers import Container

from .config_sync import ConfigSync
from .container_manager import ContainerManager
from .logging_config import get_logger, setup_logging
from .session_store import SessionStore
from .utils import format_timestamp, generate_container_name, get_git_worktree_info, validate_name

logger = get_logger(__name__)

console = Console()
manager = ContainerManager()
store = SessionStore()
config_sync = ConfigSync()


def _validate_project_feature_names(project: str, feature: str) -> None:
    """Validate project and feature names, exit on invalid names."""
    if not validate_name(project):
        console.print(
            "[red]Invalid project name. Use only letters, numbers, hyphens, and underscores.[/red]",
        )
        sys.exit(1)

    if not validate_name(feature):
        console.print(
            "[red]Invalid feature name. Use only letters, numbers, hyphens, and underscores.[/red]",
        )
        sys.exit(1)


def _try_reuse_existing_container(project: str, feature: str, detach: bool) -> bool:
    """Try to reuse existing container if available. Returns True if reused."""
    existing = store.find_container(project=project, feature=feature, status="running")
    if not existing:
        return False

    console.print(f"[green]♻️  Reusing container: {existing['container_name']}[/green]")
    console.print(f"[dim]Container ID: {existing['container_id'][:12]}[/dim]")

    if not detach:
        console.print("\n[yellow]Attaching to container...[/yellow]")
        manager.attach_to_container(existing["container_id"])
    return True


def _ensure_image_available(image: str, progress: Progress, task: Any) -> None:
    """Ensure Docker image is available, pull or build if necessary."""
    if manager.image_exists(image):
        return

    progress.update(task, description=f"Pulling image {image}...")
    success = manager.pull_image(image)
    if success:
        return

    console.print(f"[red]Failed to pull image {image}[/red]")
    console.print("[yellow]Building image locally...[/yellow]")
    if not manager.build_base_image():
        console.print("[red]Failed to build base image[/red]")
        sys.exit(1)


def _create_and_start_container(
    container_name: str,
    image: str,
    project: str,
    feature: str,
    mounts: dict[str, dict[str, Any]],
    progress: Progress,
    task: Any,
) -> Container:
    """Create and start a new container."""
    progress.update(task, description="Creating container...")

    container = manager.create_container(
        name=container_name,
        image=image,
        mounts=mounts,
        labels={
            "sandbox.claude.project": project,
            "sandbox.claude.feature": feature,
            "sandbox.claude.created": datetime.now().isoformat(),
            "sandbox.claude.version": "1.0.0",
        },
        environment={
            "SANDBOX_PROJECT": project,
            "SANDBOX_FEATURE": feature,
        },
    )

    if not container:
        console.print("[red]Failed to create container[/red]")
        sys.exit(1)

    progress.update(task, description="Starting container...")
    manager.start_container(container.id)

    # Store in database
    store.add_container(
        container_id=container.id,
        container_name=container_name,
        project_name=project,
        feature_name=feature,
        working_dir=os.getcwd(),
        docker_image=image,
    )

    progress.update(task, description="Container ready!", completed=True)
    return container


def _sync_container_statuses(project: Optional[str] = None) -> None:
    """Sync container statuses with Docker."""
    all_containers = store.list_containers(project=project)
    for container in all_containers:
        docker_status = manager.get_container_status(container["container_id"])
        if docker_status != container["status"]:
            store.update_container_status(container["container_id"], docker_status)


def _get_containers_to_remove(
    project: Optional[str],
    all_containers: bool,
) -> builtin_list[dict[str, Any]]:
    """Get list of containers to remove based on filters."""
    removable_statuses = ["stopped", "exited", "not_found", "error"]

    if all_containers:
        containers = store.list_containers()
    elif project:
        containers = store.list_containers(project=project)
    else:
        console.print("[red]Specify --project or --all[/red]")
        sys.exit(1)

    return [c for c in containers if c["status"] in removable_statuses]


def _confirm_container_removal(containers: builtin_list[dict[str, Any]]) -> bool:
    """Ask for confirmation before removing containers."""
    console.print(f"[yellow]Will remove {len(containers)} container(s):[/yellow]")
    for c in containers:
        console.print(f"  - {c['project_name']}/{c['feature_name']} ({c['container_id'][:12]})")
    return click.confirm("Continue?")


def _remove_containers(containers: builtin_list[dict[str, Any]]) -> None:
    """Remove containers with progress display."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Removing {len(containers)} container(s)...",
            total=len(containers),
        )

        for container in containers:
            # Try to remove from Docker first (force=True handles both running and stopped)
            if container["status"] != "not_found":
                manager.remove_container(container["container_id"])
            # Always remove from database
            store.remove_container(container["container_id"])
            progress.advance(task)


def _add_workspace_mount(mounts: dict[str, dict[str, Any]]) -> None:
    """Add workspace mount configuration."""
    current_dir = Path(os.getcwd())
    mounts["workspace"] = {
        "source": str(current_dir),
        "target": "/workspace",
        "type": "bind",
    }


def _add_git_worktree_mount(mounts: dict[str, dict[str, Any]]) -> None:
    """Add git worktree mount if applicable."""
    current_dir = Path(os.getcwd())
    is_worktree, main_git_dir = get_git_worktree_info(current_dir)

    if not (is_worktree and main_git_dir):
        return

    # Verify the main git directory exists and is accessible
    if main_git_dir.exists() and main_git_dir.is_dir():
        # Mount the main .git directory as READ-ONLY to prevent breaking host worktree
        mounts["main_git"] = {
            "source": str(main_git_dir),
            "target": "/workspace/.git_main",
            "type": "bind",
            "read_only": True,  # Critical: prevent modifications to host git metadata
        }
        console.print("[dim]Detected git worktree, mounting main repository (read-only)[/dim]")
        logger.info(f"Mounted git worktree main directory: {main_git_dir}")
    else:
        console.print(
            "[yellow]Warning: Git worktree detected but main repository not accessible[/yellow]",
        )
        logger.warning(f"Git worktree detected but main repository not accessible: {main_git_dir}")


def _add_claude_config_mounts(mounts: dict[str, dict[str, Any]]) -> None:
    """Add Claude configuration mounts."""
    # Create a shared config directory that's writable
    shared_config_dir = Path("/tmp/csandbox/.claude")
    shared_config_dir.mkdir(parents=True, exist_ok=True)

    # Mount the shared config directory as writable
    mounts["shared_config"] = {
        "source": str(shared_config_dir),
        "target": "/host-claude-config",
        "type": "bind",
        "read_only": False,  # Writable mount for syncing back
    }

    claude_config = Path.home() / ".claude"
    claude_json = Path.home() / ".claude.json"
    # Check for credentials in both old and new locations
    claude_creds_old = Path.home() / ".claude_creds.json"
    claude_creds_new = Path.home() / ".claude" / ".credentials.json"

    # Also mount original configs as read-only for initial copy
    if claude_config.exists():
        mounts["claude_config"] = {
            "source": str(claude_config),
            "target": "/tmp/.claude.host",
            "type": "bind",
            "read_only": True,
        }

    if claude_json.exists():
        mounts["claude_json"] = {
            "source": str(claude_json),
            "target": "/tmp/.claude.json.host",
            "type": "bind",
            "read_only": True,
        }

    # Mount credentials file from either location
    if claude_creds_new.exists():
        mounts["claude_creds"] = {
            "source": str(claude_creds_new),
            "target": "/tmp/.claude_creds.json.host",
            "type": "bind",
            "read_only": True,
        }
    elif claude_creds_old.exists():
        mounts["claude_creds"] = {
            "source": str(claude_creds_old),
            "target": "/tmp/.claude_creds.json.host",
            "type": "bind",
            "read_only": True,
        }


def _prepare_mounts(no_mount_config: bool) -> dict[str, dict[str, Any]]:
    """Prepare mount configurations for container."""
    mounts: dict[str, dict[str, Any]] = {}

    # Add workspace mount
    _add_workspace_mount(mounts)

    # Add git worktree mount if applicable
    _add_git_worktree_mount(mounts)

    # Add Claude configuration mounts if not disabled
    if not no_mount_config:
        _add_claude_config_mounts(mounts)

    logger.debug(f"Prepared {len(mounts)} mount configurations")
    return mounts


def _find_container_by_project_feature(
    project: Optional[str],
    feature: Optional[str],
) -> Optional[str]:
    """Find container ID by project and/or feature."""
    container = store.find_container(project=project, feature=feature, status="running")
    if not container:
        return None

    return container.get("container_id")


@click.group()
@click.version_option(version="1.0.0", prog_name="sandbox-claude")
def cli() -> None:
    """Sandbox Claude - Manage sandboxed Claude Code environments in Docker."""


@cli.command()
@click.option("--project", "-p", required=True, help="Project name for grouping containers")
@click.option("--feature", "-f", required=True, help="Feature or task being worked on")
@click.option("--reuse", "-r", is_flag=True, help="Reuse existing container if available")
@click.option("--detach", "-d", is_flag=True, help="Run container in background")
@click.option(
    "--image",
    default="sandbox-claude-base:latest",
    help="Docker image to use",
)
@click.option(
    "--no-mount-config",
    is_flag=True,
    help="Skip mounting ~/.claude configuration",
)
def new(
    project: str,
    feature: str,
    reuse: bool,
    detach: bool,
    image: str,
    no_mount_config: bool,
) -> None:
    """Create a new sandbox container for development."""
    _validate_project_feature_names(project, feature)

    # Check for reuse
    if reuse and _try_reuse_existing_container(project, feature, detach):
        return

    # Generate container name
    container_name = generate_container_name(project, feature)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Ensure image is available
        task = progress.add_task("Checking Docker image...", total=None)
        _ensure_image_available(image, progress, task)

        # Prepare mounts and create container
        mounts = _prepare_mounts(no_mount_config)
        container = _create_and_start_container(
            container_name,
            image,
            project,
            feature,
            mounts,
            progress,
            task,
        )

    # Success output
    console.print(f"\n[green]✅ Created sandbox: {container_name}[/green]")
    console.print(f"[dim]Container ID: {container.id[:12]}[/dim]")
    console.print("[dim]Workspace: /workspace[/dim]")
    console.print("[dim]Claude Code ready![/dim]")

    if not detach:
        console.print("\n[yellow]Attaching to container...[/yellow]")
        console.print("[dim]Exit with Ctrl+D or 'exit'[/dim]\n")
        manager.attach_to_container(container.id)


@cli.command()
@click.option("--project", "-p", help="Filter by project name")
@click.option("--feature", "-f", help="Filter by feature name")
@click.option("--active", is_flag=True, help="Show only running containers")
@click.option("--all", "-a", is_flag=True, help="Show all containers including stopped")
def list(project: Optional[str], feature: Optional[str], active: bool, all: bool) -> None:
    """List all sandbox containers."""

    containers = store.list_containers(
        project=project,
        feature=feature,
        status="running" if active and not all else None,
    )

    if not containers:
        console.print("[yellow]No sandbox containers found[/yellow]")
        return

    table = Table(title="Sandbox Containers")
    table.add_column("PROJECT", style="cyan")
    table.add_column("FEATURE", style="magenta")
    table.add_column("CONTAINER ID", style="dim")
    table.add_column("STATUS", style="green")
    table.add_column("CREATED", style="dim")

    for container in containers:
        # Update status from Docker
        docker_status = manager.get_container_status(container["container_id"])
        if docker_status != container["status"]:
            store.update_container_status(container["container_id"], docker_status)
            container["status"] = docker_status

        status_color = (
            "green"
            if container["status"] == "running"
            else "yellow" if container["status"] == "exited" else "red"
        )

        table.add_row(
            container["project_name"],
            container["feature_name"],
            container["container_id"][:12],
            f"[{status_color}]{container['status']}[/{status_color}]",
            format_timestamp(container["created_at"]),
        )

    console.print(table)


@cli.command()
@click.argument("container_ref", required=False)
@click.option("--project", "-p", help="Project name to find container")
@click.option("--feature", "-f", help="Feature name to find container")
@click.option("--latest", "-l", is_flag=True, help="Connect to most recent container")
def ssh(
    container_ref: Optional[str],
    project: Optional[str],
    feature: Optional[str],
    latest: bool,
) -> None:
    """SSH into a sandbox container."""

    container_id = None

    if container_ref:
        # Direct container ID or name provided
        container_id = container_ref
    elif latest:
        # Get most recent container
        containers = store.list_containers(status="running", limit=1)
        if containers:
            container_id = containers[0]["container_id"]
    elif project or feature:
        # Find by project/feature
        container_id = _find_container_by_project_feature(project, feature)

    if not container_id:
        console.print("[red]No container found[/red]")
        console.print("[dim]Use 'sandbox-claude list' to see available containers[/dim]")
        sys.exit(1)

    # Get container info
    container_info = store.get_container(container_id)
    if container_info:
        console.print(
            f"[green]📦 Connecting to {container_info['project_name']}/{container_info['feature_name']}...[/green]",
        )

    # Attach to container
    manager.attach_to_container(container_id)


@cli.command()
@click.argument("container_ref", required=False)
@click.option("--project", "-p", help="Stop all containers for project")
@click.option("--all", "-a", is_flag=True, help="Stop all sandbox containers")
def stop(container_ref: Optional[str], project: Optional[str], all: bool) -> None:
    """Stop sandbox container(s)."""

    containers_to_stop = []

    if all:
        containers = store.list_containers(status="running")
        containers_to_stop = [c["container_id"] for c in containers]
    elif project:
        containers = store.list_containers(project=project, status="running")
        containers_to_stop = [c["container_id"] for c in containers]
    elif container_ref:
        containers_to_stop = [container_ref]
    else:
        console.print("[red]Specify a container, project, or use --all[/red]")
        sys.exit(1)

    if not containers_to_stop:
        console.print("[yellow]No running containers found[/yellow]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Stopping {len(containers_to_stop)} container(s)...",
            total=len(containers_to_stop),
        )

        for container_id in containers_to_stop:
            manager.stop_container(container_id)
            store.update_container_status(container_id, "stopped")
            progress.advance(task)

    console.print(f"[green]✅ Stopped {len(containers_to_stop)} container(s)[/green]")


@cli.command()
@click.option("--project", "-p", help="Clean containers for specific project")
@click.option("--all", "-a", is_flag=True, help="Clean all stopped containers")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def clean(project: Optional[str], all: bool, force: bool) -> None:
    """Remove stopped sandbox containers."""
    # Sync container statuses with Docker first
    _sync_container_statuses(project if not all else None)

    # Get containers to remove
    containers_to_remove = _get_containers_to_remove(project, all)

    if not containers_to_remove:
        console.print("[yellow]No stopped containers to clean[/yellow]")
        return

    # Ask for confirmation unless force is used
    if not force and not _confirm_container_removal(containers_to_remove):
        console.print("[dim]Cancelled[/dim]")
        return

    # Remove containers
    _remove_containers(containers_to_remove)
    console.print(f"[green]✅ Removed {len(containers_to_remove)} container(s)[/green]")


@cli.command()
@click.argument("container_ref")
@click.argument("command", nargs=-1, required=True)
def exec(container_ref: str, command: tuple) -> None:
    """Execute a command in a sandbox container."""

    # Join command parts
    cmd = " ".join(command)

    # Execute in container
    result = manager.exec_command(container_ref, cmd)

    if result["exit_code"] != 0:
        console.print(f"[red]Command failed with exit code {result['exit_code']}[/red]")
        if result["stderr"]:
            console.print(result["stderr"])
        sys.exit(result["exit_code"])

    if result["stdout"]:
        console.print(result["stdout"])


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Force rebuild even if image exists")
def build(force: bool) -> None:
    """Build or rebuild the base Docker image."""

    if (
        not force
        and manager.image_exists("sandbox-claude-base:latest")
        and not click.confirm("Base image already exists. Rebuild?")
    ):
        console.print("[dim]Cancelled[/dim]")
        return

    console.print("[yellow]Building base image...[/yellow]")
    console.print("[dim]This may take several minutes on first build[/dim]\n")

    success = manager.build_base_image()

    if success:
        console.print("\n[green]✅ Base image built successfully![/green]")
        console.print("[dim]Image: sandbox-claude-base:latest[/dim]")
    else:
        console.print("\n[red]❌ Failed to build base image[/red]")
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    # Set up logging
    log_dir = Path.home() / ".sandbox_claude" / "logs"
    log_file = log_dir / "sandbox-claude.log"
    setup_logging(level="INFO", log_file=log_file)

    try:
        logger.info("Starting sandbox-claude CLI")
        cli()
    except KeyboardInterrupt:
        logger.info("User interrupted the operation")
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unexpected error in CLI: {e}")
        console.print(f"[red]Error: {e}[/red]")
        console.print("[dim]Check ~/.sandbox_claude/logs/sandbox-claude.log for details[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
