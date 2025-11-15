"""
Configuration synchronization for sandbox-claude.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .constants import (
    BACKUP_IGNORE_PATTERNS,
    CLAUDE_CONFIG_DIR_NAME,
    CLAUDE_CONFIG_FILE_NAME,
    CONTAINER_CLAUDE_CONFIG_PATH,
    CONTAINER_TEMP_CLAUDE_JSON_HOST,
    SANDBOX_CONFIG_DIR_NAME,
    SENSITIVE_FILE_PERMISSION_MASK,
)
from .logging_config import get_logger

logger = get_logger(__name__)


class ConfigSync:
    """Manages configuration synchronization between host and containers."""

    def __init__(self) -> None:
        """Initialize configuration sync manager."""
        self.home_dir = Path.home()
        self.claude_config_dir = self.home_dir / CLAUDE_CONFIG_DIR_NAME
        self.claude_json = self.home_dir / CLAUDE_CONFIG_FILE_NAME
        self.sandbox_config_dir = self.home_dir / SANDBOX_CONFIG_DIR_NAME

        # Ensure sandbox config directory exists
        self.sandbox_config_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"ConfigSync initialized with sandbox dir: {self.sandbox_config_dir}")

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
                "target": CONTAINER_CLAUDE_CONFIG_PATH,
                "type": "bind",
                "read_only": True,
            }
            logger.debug(f"Prepared claude config mount for container {container_id[:12]}")

        # Check for .claude.json
        # Mount to a temporary location so entrypoint can copy it
        # This allows Claude to modify the copy without affecting the host file
        if self.claude_json.exists():
            mounts["claude_json_host"] = {
                "source": str(self.claude_json),
                "target": CONTAINER_TEMP_CLAUDE_JSON_HOST,
                "type": "bind",
                "read_only": True,
            }
            logger.debug(f"Prepared claude.json mount for container {container_id[:12]}")

        return mounts

    def _validate_claude_json(self, results: dict[str, Any]) -> None:
        """Validate .claude.json file format and content."""
        if not self.claude_json.exists():
            return

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

    def _validate_claude_directory(self, results: dict[str, Any]) -> None:
        """Validate .claude directory permissions and sensitive files."""
        if not self.claude_config_dir.exists():
            return

        # Check if directory is readable
        if not os.access(self.claude_config_dir, os.R_OK):
            results["valid"] = False
            results["errors"].append(".claude directory is not readable")
            return

        # Check for sensitive files
        self._check_sensitive_file_permissions(results)

    def _check_sensitive_file_permissions(self, results: dict[str, Any]) -> None:
        """Check permissions on sensitive files in .claude directory."""
        sensitive_files = ["credentials", "tokens", "keys"]

        for file_path in self.claude_config_dir.rglob("*"):
            if not file_path.is_file():
                continue

            for sensitive in sensitive_files:
                if sensitive in file_path.name.lower():
                    stat_info = file_path.stat()
                    if stat_info.st_mode & SENSITIVE_FILE_PERMISSION_MASK:
                        warning_msg = f"Sensitive file {file_path.name} has permissive permissions"
                        results["warnings"].append(warning_msg)
                        logger.warning(warning_msg)

    def validate_config(self) -> dict[str, Any]:
        """Validate Claude configuration files."""
        results: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }

        self._validate_claude_json(results)
        self._validate_claude_directory(results)

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
                backup_dir / CLAUDE_CONFIG_DIR_NAME,
                ignore=shutil.ignore_patterns(*BACKUP_IGNORE_PATTERNS),
            )
            logger.info(f"Backed up {CLAUDE_CONFIG_DIR_NAME} directory")

        # Backup .claude.json
        if self.claude_json.exists():
            shutil.copy2(self.claude_json, backup_dir / CLAUDE_CONFIG_FILE_NAME)
            logger.info(f"Backed up {CLAUDE_CONFIG_FILE_NAME} file")

        # Create backup metadata
        metadata = {
            "timestamp": timestamp,
            "files_backed_up": len(list(backup_dir.rglob("*"))),
            "backup_path": str(backup_dir),
        }

        with open(backup_dir / "backup_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Config backup created at {backup_dir}")
        return backup_dir

    def restore_config(self, backup_path: Path) -> bool:
        """Restore Claude configuration from backup."""
        if not backup_path.exists():
            logger.error(f"Backup path does not exist: {backup_path}")
            return False

        try:
            # Restore .claude directory
            claude_backup = backup_path / CLAUDE_CONFIG_DIR_NAME
            if claude_backup.exists():
                if self.claude_config_dir.exists():
                    shutil.rmtree(self.claude_config_dir)
                shutil.copytree(claude_backup, self.claude_config_dir)
                logger.info(f"Restored {CLAUDE_CONFIG_DIR_NAME} directory")

            # Restore .claude.json
            json_backup = backup_path / CLAUDE_CONFIG_FILE_NAME
            if json_backup.exists():
                shutil.copy2(json_backup, self.claude_json)
                logger.info(f"Restored {CLAUDE_CONFIG_FILE_NAME} file")

            logger.info(f"Config restored from {backup_path}")
            return True
        except (OSError, shutil.Error) as e:
            logger.error(f"Error restoring config: {e}")
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
""",
            )
            logger.info(f"Created default {CLAUDE_CONFIG_DIR_NAME} directory with CLAUDE.md")
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

            logger.info(f"Created template {CLAUDE_CONFIG_FILE_NAME} at {self.claude_json}")
            logger.warning("Please add your API key to this file")
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
