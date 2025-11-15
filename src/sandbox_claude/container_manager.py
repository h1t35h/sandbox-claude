"""
Docker container management for sandbox-claude.
"""

import datetime
import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, Optional

import docker
from docker.errors import APIError, DockerException, NotFound
from docker.models.containers import Container
from docker.types import Mount

from .constants import (
    CONTAINER_LABEL_CREATED,
    CONTAINER_LABEL_VERSION,
    DEFAULT_DOCKER_IMAGE,
    DEFAULT_DOCKER_USER,
    DOCKER_BUILD_TIMEOUT_SECONDS,
    DOCKER_STOP_TIMEOUT_SECONDS,
    DOCKER_WORKSPACE_PATH,
)
from .logging_config import get_logger

logger = get_logger(__name__)


class ContainerManager:
    """Manages Docker containers for sandbox environments."""

    def __init__(self) -> None:
        """Initialize Docker client."""
        try:
            self.client = docker.from_env()  # type: ignore
            # Test connection
            self.client.ping()
            logger.debug("Docker client initialized successfully")
        except DockerException as e:
            logger.error(f"Cannot connect to Docker daemon: {e}")
            logger.error("Error: Cannot connect to Docker. Is Docker running?")
            sys.exit(1)

    def image_exists(self, image_name: str) -> bool:
        """Check if a Docker image exists locally."""
        try:
            self.client.images.get(image_name)
            logger.debug(f"Image {image_name} found locally")
            return True
        except NotFound:
            logger.debug(f"Image {image_name} not found locally")
            return False
        except APIError as e:
            logger.error(f"Failed to check image {image_name}: {e}")
            return False

    def pull_image(self, image_name: str) -> bool:
        """Pull a Docker image from registry."""
        try:
            logger.info(f"Pulling image {image_name}...")
            self.client.images.pull(image_name)
            logger.info(f"Successfully pulled image {image_name}")
            return True
        except (DockerException, APIError) as e:
            logger.error(f"Failed to pull image {image_name}: {e}")
            return False

    def build_base_image(self) -> bool:
        """Build the base Docker image from Dockerfile."""
        dockerfile_path = Path(__file__).parent.parent.parent / "docker" / "Dockerfile"

        if not dockerfile_path.exists():
            logger.error(f"Dockerfile not found at {dockerfile_path}")
            return False

        try:
            logger.info("Building base Docker image...")
            # Use subprocess for better output streaming
            result = subprocess.run(
                [
                    "docker",
                    "build",
                    "-t",
                    DEFAULT_DOCKER_IMAGE,
                    "-f",
                    str(dockerfile_path),
                    str(dockerfile_path.parent),
                ],
                check=False,
                capture_output=False,
                text=True,
                timeout=DOCKER_BUILD_TIMEOUT_SECONDS,
            )
            success = result.returncode == 0
            if success:
                logger.info("Base image built successfully")
            else:
                logger.error(f"Build failed with exit code {result.returncode}")
            return success
        except subprocess.TimeoutExpired:
            timeout_minutes = DOCKER_BUILD_TIMEOUT_SECONDS // 60
            logger.error(f"Build timed out after {timeout_minutes} minutes")
            return False
        except Exception as e:
            logger.error(f"Build failed with exception: {e}")
            return False

    def create_container(
        self,
        name: str,
        image: str,
        mounts: Optional[dict[str, dict[str, Any]]] = None,
        labels: Optional[dict[str, str]] = None,
        environment: Optional[dict[str, str]] = None,
        ports: Optional[dict[str, int]] = None,
    ) -> Optional[Container]:
        """Create a new Docker container."""
        try:
            # Prepare mount configurations
            mount_configs = []
            if mounts:
                for _mount_name, config in mounts.items():
                    mount_configs.append(
                        Mount(
                            target=config["target"],
                            source=config["source"],
                            type=config.get("type", "bind"),
                            read_only=config.get("read_only", False),
                        ),
                    )

            # Create container
            container = self.client.containers.create(
                image=image,
                name=name,
                command="/bin/bash",
                stdin_open=True,
                tty=True,
                detach=True,
                mounts=mount_configs,
                labels=labels or {},
                environment=environment or {},
                ports=ports or {},
                working_dir=DOCKER_WORKSPACE_PATH,
                user=DEFAULT_DOCKER_USER,
                hostname=name.split("-")[-1][:12],  # Use part of name as hostname
            )

            return container

        except APIError as e:
            logger.error(f"Failed to create container {name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating container {name}: {e}")
            return None

    def start_container(self, container_id: str) -> bool:
        """Start a Docker container."""
        try:
            container = self.client.containers.get(container_id)
            container.start()
            logger.info(f"Started container {container_id[:12]}")
            return True
        except NotFound as e:
            logger.error(f"Container not found: {container_id[:12]} - {e}")
            return False
        except APIError as e:
            logger.error(f"Failed to start container {container_id[:12]}: {e}")
            return False

    def stop_container(self, container_id: str) -> bool:
        """Stop a Docker container."""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=DOCKER_STOP_TIMEOUT_SECONDS)
            logger.info(f"Stopped container {container_id[:12]}")
            return True
        except NotFound as e:
            logger.error(f"Container not found: {container_id[:12]} - {e}")
            return False
        except APIError as e:
            logger.error(f"Failed to stop container {container_id[:12]}: {e}")
            return False

    def remove_container(self, container_id: str) -> bool:
        """Remove a Docker container."""
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=True)
            logger.info(f"Removed container {container_id[:12]}")
            return True
        except NotFound:
            logger.warning(f"Container not found (may already be removed): {container_id[:12]}")
            return False
        except APIError as e:
            logger.error(f"Failed to remove container {container_id[:12]}: {e}")
            return False

    def get_container_status(self, container_id: str) -> str:
        """Get the status of a Docker container."""
        try:
            container = self.client.containers.get(container_id)
            return str(container.status)
        except NotFound:
            return "not_found"
        except APIError:
            return "error"

    def attach_to_container(self, container_id: str) -> None:
        """Attach to a running container (interactive shell)."""
        try:
            # Use subprocess for proper TTY handling
            subprocess.run(
                ["docker", "exec", "-it", "-u", DEFAULT_DOCKER_USER, container_id, "/bin/bash"],
                check=False,
            )
        except Exception as e:
            logger.error(f"Failed to attach to container {container_id[:12]}: {e}")

    def exec_command(self, container_id: str, command: str) -> dict[str, Any]:
        """Execute a command in a container."""
        try:
            container = self.client.containers.get(container_id)
            result = container.exec_run(command, demux=True, user=DEFAULT_DOCKER_USER)

            stdout, stderr = result.output if result.output else (None, None)

            return {
                "exit_code": result.exit_code,
                "stdout": stdout.decode("utf-8") if stdout else "",
                "stderr": stderr.decode("utf-8") if stderr else "",
            }
        except NotFound as e:
            logger.error(f"Container not found: {container_id[:12]}")
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": f"Container not found: {str(e)}",
            }
        except APIError as e:
            logger.error(f"Failed to execute command in container {container_id[:12]}: {e}")
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
            }

    def list_sandbox_containers(self) -> list[Container]:
        """List all sandbox-claude containers."""
        try:
            containers: list[Container] = self.client.containers.list(
                all=True,
                filters={"label": CONTAINER_LABEL_VERSION},
            )
            return containers
        except APIError as e:
            logger.error(f"Failed to list containers: {e}")
            return []

    def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        """Get container logs."""
        try:
            container = self.client.containers.get(container_id)
            logs: str = container.logs(tail=tail).decode("utf-8")
            return logs
        except NotFound:
            logger.warning(f"Container not found for logs: {container_id[:12]}")
            return ""
        except APIError as e:
            logger.error(f"Failed to get logs for container {container_id[:12]}: {e}")
            return ""

    def copy_to_container(self, container_id: str, src: Path, dest: str) -> bool:
        """Copy files to a container."""
        try:
            container = self.client.containers.get(container_id)

            # Create tar archive of source
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                tar.add(src, arcname=os.path.basename(src))

            tar_stream.seek(0)
            container.put_archive(dest, tar_stream)
            logger.debug(f"Copied {src} to container {container_id[:12]}:{dest}")
            return True

        except NotFound:
            logger.error(f"Container not found: {container_id[:12]}")
            return False
        except APIError as e:
            logger.error(f"Failed to copy to container {container_id[:12]}: {e}")
            return False

    def cleanup_old_containers(self, days: int = 7) -> int:
        """Remove containers older than specified days."""
        removed_count = 0
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)

        for container in self.list_sandbox_containers():
            if container.status == "exited":
                created_str = container.labels.get(CONTAINER_LABEL_CREATED, "")
                if created_str:
                    try:
                        created_date = datetime.datetime.fromisoformat(created_str)
                        if created_date < cutoff_date:
                            container.remove()
                            removed_count += 1
                            logger.info(
                                f"Cleaned up old container: {container.name} "
                                f"(created: {created_str})"
                            )
                    except ValueError:
                        logger.warning(f"Invalid date format in container label: {created_str}")
                    except APIError as e:
                        logger.error(f"Failed to remove old container {container.name}: {e}")

        logger.info(f"Cleanup complete: removed {removed_count} container(s)")
        return removed_count
