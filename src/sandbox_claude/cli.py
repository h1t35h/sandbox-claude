"""
Main CLI interface for sandbox-claude.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .config_sync import ConfigSync
from .container_manager import ContainerManager
from .session_store import SessionStore
from .utils import format_timestamp, generate_container_name, validate_name

console = Console()
manager = ContainerManager()
store = SessionStore()
config_sync = ConfigSync()


def _prepare_mounts(no_mount_config: bool) -> dict[str, dict[str, Any]]:
    """Prepare mount configurations for container."""
    mounts: dict[str, dict[str, Any]] = {
        "workspace": {
            "source": os.getcwd(),
            "target": "/workspace",
            "type": "bind",
        }
    }

    if not no_mount_config:
        claude_config = Path.home() / ".claude"
        claude_json = Path.home() / ".claude.json"

        if claude_config.exists():
            mounts["claude_config"] = {
                "source": str(claude_config),
                "target": "/root/.claude",
                "type": "bind",
                "read_only": True,
            }

        if claude_json.exists():
            mounts["claude_json"] = {
                "source": str(claude_json),
                "target": "/root/.claude.json",
                "type": "bind",
                "read_only": True,
            }

    return mounts


def _find_container_by_project_feature(
    project: Optional[str], feature: Optional[str]
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
    pass


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

    # Validate names
    if not validate_name(project):
        console.print(
            "[red]Invalid project name. Use only letters, numbers, hyphens, and underscores.[/red]"
        )
        sys.exit(1)

    if not validate_name(feature):
        console.print(
            "[red]Invalid feature name. Use only letters, numbers, hyphens, and underscores.[/red]"
        )
        sys.exit(1)

    # Check for reuse
    if reuse:
        existing = store.find_container(project=project, feature=feature, status="running")
        if existing:
            console.print(f"[green]♻️  Reusing container: {existing['container_name']}[/green]")
            console.print(f"[dim]Container ID: {existing['container_id'][:12]}[/dim]")

            if not detach:
                console.print("\n[yellow]Attaching to container...[/yellow]")
                manager.attach_to_container(existing["container_id"])
            return

    # Generate container name
    container_name = generate_container_name(project, feature)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Check if image exists
        task = progress.add_task("Checking Docker image...", total=None)
        if not manager.image_exists(image):
            progress.update(task, description=f"Pulling image {image}...")
            success = manager.pull_image(image)
            if not success:
                console.print(f"[red]Failed to pull image {image}[/red]")
                console.print("[yellow]Building image locally...[/yellow]")
                if not manager.build_base_image():
                    console.print("[red]Failed to build base image[/red]")
                    sys.exit(1)

        progress.update(task, description="Creating container...")

        # Prepare mounts
        mounts = _prepare_mounts(no_mount_config)

        # Create container
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

        status_color = "green" if container["status"] == "running" else "red"

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
            f"[green]📦 Connecting to {container_info['project_name']}/{container_info['feature_name']}...[/green]"
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
            f"Stopping {len(containers_to_stop)} container(s)...", total=len(containers_to_stop)
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

    containers_to_remove = []

    if all:
        containers = store.list_containers(status="stopped")
        containers_to_remove = containers
    elif project:
        containers = store.list_containers(project=project, status="stopped")
        containers_to_remove = containers
    else:
        console.print("[red]Specify --project or --all[/red]")
        sys.exit(1)

    if not containers_to_remove:
        console.print("[yellow]No stopped containers to clean[/yellow]")
        return

    if not force:
        console.print(f"[yellow]Will remove {len(containers_to_remove)} container(s):[/yellow]")
        for c in containers_to_remove:
            console.print(f"  - {c['project_name']}/{c['feature_name']} ({c['container_id'][:12]})")

        if not click.confirm("Continue?"):
            console.print("[dim]Cancelled[/dim]")
            return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Removing {len(containers_to_remove)} container(s)...",
            total=len(containers_to_remove),
        )

        for container in containers_to_remove:
            manager.remove_container(container["container_id"])
            store.remove_container(container["container_id"])
            progress.advance(task)

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

    if not force and manager.image_exists("sandbox-claude-base:latest") and not click.confirm("Base image already exists. Rebuild?"):
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
    try:
        cli()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
