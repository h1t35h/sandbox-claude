"""
Configuration synchronization for sandbox-claude.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class ConfigSync:
    """Manages configuration synchronization between host and containers."""

    def __init__(self) -> None:
        """Initialize configuration sync manager."""
        self.home_dir = Path.home()
        self.claude_config_dir = self.home_dir / ".claude"
        self.claude_json = self.home_dir / ".claude.json"
        self.sandbox_config_dir = self.home_dir / ".sandbox_claude"

        # Ensure sandbox config directory exists
        self.sandbox_config_dir.mkdir(parents=True, exist_ok=True)

    def check_claude_config(self) -> dict[str, bool]:
        """Check which Claude configuration files exist."""
        return {
            "claude_dir": self.claude_config_dir.exists(),
            "claude_json": self.claude_json.exists(),
            "has_config": self.claude_config_dir.exists() or self.claude_json.exists(),
        }

    def get_config_files(self) -> list[Path]:
        """Get list of Claude configuration files."""
        config_files = []

        if self.claude_config_dir.exists():
            # Get all files in .claude directory
            for file_path in self.claude_config_dir.rglob("*"):
                if file_path.is_file():
                    config_files.append(file_path)

        if self.claude_json.exists():
            config_files.append(self.claude_json)

        return config_files

    def prepare_container_config(self, container_id: str) -> dict[str, Any]:
        """Prepare configuration mounts for a container."""
        mounts = {}

        # Check for .claude directory
        if self.claude_config_dir.exists():
            mounts["claude_config"] = {
                "source": str(self.claude_config_dir),
                "target": "/root/.claude",
                "type": "bind",
                "read_only": True,
            }

        # Check for .claude.json
        # Mount to a temporary location so entrypoint can copy it
        # This allows Claude to modify the copy without affecting the host file
        if self.claude_json.exists():
            mounts["claude_json_host"] = {
                "source": str(self.claude_json),
                "target": "/tmp/.claude.json.host",
                "type": "bind",
                "read_only": True,
            }

        return mounts

    def validate_config(self) -> dict[str, Any]:
        """Validate Claude configuration files."""
        results: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }

        # Check .claude.json format
        if self.claude_json.exists():
            try:
                with open(self.claude_json) as f:
                    config = json.load(f)

                    # Check for required fields
                    if not config.get("api_key") and not config.get("token"):
                        results["warnings"].append("No API key or token found in .claude.json")
            except json.JSONDecodeError as e:
                results["valid"] = False
                results["errors"].append(f"Invalid JSON in .claude.json: {e}")
            except Exception as e:
                results["valid"] = False
                results["errors"].append(f"Error reading .claude.json: {e}")

        # Check .claude directory permissions
        if self.claude_config_dir.exists():
            # Check if directory is readable
            if not os.access(self.claude_config_dir, os.R_OK):
                results["valid"] = False
                results["errors"].append(".claude directory is not readable")

            # Check for sensitive files
            sensitive_files = ["credentials", "tokens", "keys"]
            for file_path in self.claude_config_dir.rglob("*"):
                if file_path.is_file():
                    for sensitive in sensitive_files:
                        if sensitive in file_path.name.lower():
                            # Check file permissions
                            stat_info = file_path.stat()
                            if stat_info.st_mode & 0o077:
                                results["warnings"].append(
                                    f"Sensitive file {file_path.name} has permissive permissions"
                                )

        return results

    def backup_config(self) -> Path:
        """Create a backup of Claude configuration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.sandbox_config_dir / "backups" / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup .claude directory
        if self.claude_config_dir.exists():
            shutil.copytree(
                self.claude_config_dir,
                backup_dir / ".claude",
                ignore=shutil.ignore_patterns("*.log", "*.tmp", "__pycache__"),
            )

        # Backup .claude.json
        if self.claude_json.exists():
            shutil.copy2(self.claude_json, backup_dir / ".claude.json")

        # Create backup metadata
        metadata = {
            "timestamp": timestamp,
            "files_backed_up": len(list(backup_dir.rglob("*"))),
            "backup_path": str(backup_dir),
        }

        with open(backup_dir / "backup_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        return backup_dir

    def restore_config(self, backup_path: Path) -> bool:
        """Restore Claude configuration from backup."""
        if not backup_path.exists():
            return False

        try:
            # Restore .claude directory
            claude_backup = backup_path / ".claude"
            if claude_backup.exists():
                if self.claude_config_dir.exists():
                    shutil.rmtree(self.claude_config_dir)
                shutil.copytree(claude_backup, self.claude_config_dir)

            # Restore .claude.json
            json_backup = backup_path / ".claude.json"
            if json_backup.exists():
                shutil.copy2(json_backup, self.claude_json)

            return True
        except Exception as e:
            print(f"Error restoring config: {e}")
            return False

    def create_default_config(self) -> bool:
        """Create default Claude configuration if none exists."""
        created = False

        # Create .claude directory if it doesn't exist
        if not self.claude_config_dir.exists():
            self.claude_config_dir.mkdir(parents=True, exist_ok=True)

            # Create default CLAUDE.md
            claude_md = self.claude_config_dir / "CLAUDE.md"
            claude_md.write_text(
                """# Claude Configuration

This directory contains configuration for Claude Code.

## Project Settings

Add your project-specific settings here.

## Custom Commands

Define custom commands for your workflow.
"""
            )
            created = True

        # Create .claude.json template if it doesn't exist
        if not self.claude_json.exists():
            template = {
                "api_key": "",
                "model": "claude-3-opus-20240229",
                "max_tokens": 4096,
                "temperature": 0.7,
            }

            with open(self.claude_json, "w") as f:
                json.dump(template, f, indent=2)

            print(f"Created template .claude.json at {self.claude_json}")
            print("Please add your API key to this file.")
            created = True

        return created

    def get_project_config(self, project_name: str) -> Optional[dict[str, Any]]:
        """Get project-specific configuration."""
        project_config_file = self.sandbox_config_dir / "projects" / f"{project_name}.json"

        if project_config_file.exists():
            try:
                with open(project_config_file) as f:
                    config: dict[str, Any] = json.load(f)
                    return config
            except Exception:
                return None

        return None

    def save_project_config(self, project_name: str, config: dict[str, Any]) -> bool:
        """Save project-specific configuration."""
        projects_dir = self.sandbox_config_dir / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)

        project_config_file = projects_dir / f"{project_name}.json"

        try:
            with open(project_config_file, "w") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception:
            return False

    def sync_container_config(self, container_id: str, files_to_sync: list[str]) -> bool:
        """Sync specific configuration files to a running container."""
        from .container_manager import ContainerManager

        manager = ContainerManager()

        for file_path in files_to_sync:
            source = Path(file_path)
            if source.exists():
                # Determine destination path
                if str(source).startswith(str(self.claude_config_dir)):
                    # File is in .claude directory
                    rel_path = source.relative_to(self.claude_config_dir)
                    dest = f"/root/.claude/{rel_path}"
                elif source == self.claude_json:
                    dest = "/root/.claude.json"
                else:
                    # Other files go to /root
                    dest = f"/root/{source.name}"

                # Copy file to container
                if not manager.copy_to_container(container_id, source, os.path.dirname(dest)):
                    return False

        return True
