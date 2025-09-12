"""
Utility functions for sandbox-claude.
"""

import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def get_git_worktree_info(path: Path) -> tuple[bool, Optional[Path]]:
    """Check if a directory is a git worktree and return the main git directory.
    
    Returns:
        (is_worktree, main_git_dir)
        - is_worktree: True if the path is a git worktree
        - main_git_dir: Path to the main git directory if it's a worktree, None otherwise
    """
    git_path = path / ".git"

    if not git_path.exists():
        return False, None

    # If .git is a directory, it's not a worktree
    if git_path.is_dir():
        return False, None

    # If .git is a file, it's likely a worktree
    try:
        with open(git_path) as f:
            content = f.read().strip()
            # Format is usually: gitdir: /path/to/main/.git/worktrees/worktree-name
            if content.startswith("gitdir:"):
                gitdir_path = content.split("gitdir:", 1)[1].strip()
                gitdir = Path(gitdir_path)

                # The main git directory is two levels up from the worktree git directory
                # e.g., /path/to/main/.git/worktrees/name -> /path/to/main/.git
                if gitdir.exists() and "worktrees" in gitdir.parts:
                    # Find the .git directory (parent of worktrees)
                    for i, part in enumerate(gitdir.parts):
                        if part == "worktrees" and i > 0:
                            # Check if the previous part is .git (exact match) or ends with .git
                            prev_part = gitdir.parts[i-1]
                            if prev_part == ".git" or prev_part.endswith(".git"):
                                main_git_dir = Path(*gitdir.parts[:i])
                                return True, main_git_dir

    except Exception:
        pass

    return False, None


def generate_container_name(project: str, feature: str) -> str:
    """Generate a unique container name."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Use secrets for cryptographically secure random generation
    random_suffix = secrets.token_hex(2)  # 4 hex characters

    # Sanitize project and feature names
    project_clean = sanitize_name(project)
    feature_clean = sanitize_name(feature)

    return f"sandbox-claude-{project_clean}-{feature_clean}-{timestamp}-{random_suffix}"


def sanitize_name(name: str) -> str:
    """Sanitize a name for use in container names."""
    # Replace non-alphanumeric characters (except hyphens and underscores) with hyphens
    sanitized = re.sub(r"[^a-zA-Z0-9-_]", "-", name)
    # Replace consecutive underscores with single hyphen
    sanitized = re.sub(r"_+", "-", sanitized)
    # Remove consecutive hyphens
    sanitized = re.sub(r"-+", "-", sanitized)
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip("-")
    # Truncate if too long
    if len(sanitized) > 30:
        sanitized = sanitized[:30]

    return sanitized.lower()


def validate_name(name: str) -> bool:
    """Validate a project or feature name."""
    # Only allow alphanumeric, hyphens, and underscores
    pattern = r"^[a-zA-Z0-9-_]+$"
    return bool(re.match(pattern, name))


def format_timestamp(timestamp: str) -> str:
    """Format a timestamp for display."""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        now = datetime.now()
        diff = now - dt.replace(tzinfo=None)

        if diff.days > 7:
            return dt.strftime("%Y-%m-%d")
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "just now"
    except Exception:
        return timestamp


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    size_float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_float < 1024.0:
            return f"{size_float:.1f} {unit}"
        size_float /= 1024.0
    return f"{size_float:.1f} PB"


def get_docker_socket() -> Optional[Path]:
    """Get the Docker socket path."""
    # Common Docker socket locations
    socket_paths = [
        Path("/var/run/docker.sock"),  # Linux
        Path("/run/docker.sock"),  # Alternative Linux
        Path.home() / ".docker" / "run" / "docker.sock",  # Docker Desktop
    ]

    for socket_path in socket_paths:
        if socket_path.exists():
            return socket_path

    return None


def check_docker_installed() -> bool:
    """Check if Docker is installed and accessible."""
    import subprocess

    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def check_docker_running() -> bool:
    """Check if Docker daemon is running."""
    import subprocess

    try:
        result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_host_info() -> dict[str, str]:
    """Get information about the host system."""
    import os
    import platform

    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "user": os.getenv("USER", "unknown"),
        "home": str(Path.home()),
    }


def parse_ports(ports_str: str) -> dict[str, int]:
    """Parse port mapping string to dict."""
    port_mapping: dict[str, int] = {}

    if not ports_str:
        return port_mapping

    # Parse formats like "8080:80,3000:3000"
    for mapping in ports_str.split(","):
        parts = mapping.strip().split(":")
        if len(parts) == 2:
            try:
                host_port = int(parts[0])
                container_port = int(parts[1])
                port_mapping[f"{container_port}/tcp"] = host_port
            except ValueError:
                continue
        elif len(parts) == 1:
            try:
                port = int(parts[0])
                port_mapping[f"{port}/tcp"] = port
            except ValueError:
                continue

    return port_mapping


def parse_environment(env_str: str) -> dict[str, str]:
    """Parse environment variables string to dict."""
    env_vars: dict[str, str] = {}

    if not env_str:
        return env_vars

    # Parse formats like "KEY=value,KEY2=value2"
    for var in env_str.split(","):
        parts = var.strip().split("=", 1)
        if len(parts) == 2:
            env_vars[parts[0]] = parts[1]

    return env_vars


def find_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find the project root directory (containing .git, package.json, etc.)."""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path

    # Markers that indicate project root
    markers = [".git", "package.json", "pyproject.toml", "Cargo.toml", "go.mod"]

    while current != current.parent:
        for marker in markers:
            if (current / marker).exists():
                return current
        current = current.parent

    # If no project root found, return current directory
    return start_path


def load_project_config(project_root: Path) -> Optional[dict[str, Any]]:
    """Load project-specific sandbox configuration."""
    config_file = project_root / ".sandbox-claude.yml"

    if not config_file.exists():
        config_file = project_root / ".sandbox-claude.yaml"

    if not config_file.exists():
        return None

    try:
        import yaml

        with open(config_file) as f:
            config: dict[str, Any] = yaml.safe_load(f)
            return config
    except Exception:
        return None


def create_progress_bar(total: int, desc: str = "") -> Any:
    """Create a progress bar for long-running operations."""
    try:
        from tqdm import tqdm

        return tqdm(total=total, desc=desc, unit="item")
    except ImportError:
        # Fallback if tqdm is not installed
        class FakeProgress:
            def update(self, n: int = 1) -> None:
                pass

            def close(self) -> None:
                pass

        return FakeProgress()


def confirm_action(message: str, default: bool = False) -> bool:
    """Ask user for confirmation."""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{message} [{default_str}]: ").strip().lower()

    if not response:
        return default

    return response in ["y", "yes"]
