"""
Docker container management for sandbox-claude.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import docker
from docker.errors import APIError, DockerException, NotFound
from docker.models.containers import Container
from docker.types import Mount


class ContainerManager:
    """Manages Docker containers for sandbox environments."""

    def __init__(self) -> None:
        """Initialize Docker client."""
        try:
            self.client = docker.from_env()  # type: ignore
            # Test connection
            self.client.ping()
        except DockerException as e:
            print("Error: Cannot connect to Docker. Is Docker running?")
            print(f"Details: {e}")
            sys.exit(1)

    def image_exists(self, image_name: str) -> bool:
        """Check if a Docker image exists locally."""
        try:
            self.client.images.get(image_name)
            return True
        except NotFound:
            return False

    def pull_image(self, image_name: str) -> bool:
        """Pull a Docker image from registry."""
        try:
            self.client.images.pull(image_name)
            return True
        except (DockerException, APIError) as e:
            print(f"Failed to pull image: {e}")
            return False

    def build_base_image(self) -> bool:
        """Build the base Docker image from Dockerfile."""
        dockerfile_path = Path(__file__).parent.parent.parent / "docker" / "Dockerfile"

        if not dockerfile_path.exists():
            print(f"Dockerfile not found at {dockerfile_path}")
            return False

        try:
            # Use subprocess for better output streaming
            result = subprocess.run(
                [
                    "docker",
                    "build",
                    "-t",
                    "sandbox-claude-base:latest",
                    "-f",
                    str(dockerfile_path),
                    str(dockerfile_path.parent),
                ],
                capture_output=False,
                text=True,
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Build failed: {e}")
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
                        )
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
                working_dir="/workspace",
                user="sandman",  # Use sandman user by default
                hostname=name.split("-")[-1][:12],  # Use part of name as hostname
            )

            return container

        except APIError as e:
            print(f"Failed to create container: {e}")
            return None

    def start_container(self, container_id: str) -> bool:
        """Start a Docker container."""
        try:
            container = self.client.containers.get(container_id)
            container.start()
            return True
        except (NotFound, APIError) as e:
            print(f"Failed to start container: {e}")
            return False

    def stop_container(self, container_id: str) -> bool:
        """Stop a Docker container."""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=10)
            return True
        except (NotFound, APIError) as e:
            print(f"Failed to stop container: {e}")
            return False

    def remove_container(self, container_id: str) -> bool:
        """Remove a Docker container."""
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=True)
            return True
        except (NotFound, APIError) as e:
            print(f"Failed to remove container: {e}")
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
            # Use subprocess for proper TTY handling, run as sandman user
            subprocess.run(["docker", "exec", "-it", "-u", "sandman", container_id, "/bin/bash"], check=False)
        except Exception as e:
            print(f"Failed to attach to container: {e}")

    def exec_command(self, container_id: str, command: str) -> dict[str, Any]:
        """Execute a command in a container."""
        try:
            container = self.client.containers.get(container_id)
            result = container.exec_run(command, demux=True, user="sandman")

            stdout, stderr = result.output if result.output else (None, None)

            return {
                "exit_code": result.exit_code,
                "stdout": stdout.decode("utf-8") if stdout else "",
                "stderr": stderr.decode("utf-8") if stderr else "",
            }
        except (NotFound, APIError) as e:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
            }

    def list_sandbox_containers(self) -> list[Container]:
        """List all sandbox-claude containers."""
        try:
            containers: list[Container] = self.client.containers.list(
                all=True, filters={"label": "sandbox.claude.version"}
            )
            return containers
        except APIError:
            return []

    def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        """Get container logs."""
        try:
            container = self.client.containers.get(container_id)
            logs: str = container.logs(tail=tail).decode("utf-8")
            return logs
        except (NotFound, APIError):
            return ""

    def copy_to_container(self, container_id: str, src: Path, dest: str) -> bool:
        """Copy files to a container."""
        try:
            container = self.client.containers.get(container_id)

            # Create tar archive of source
            import io
            import tarfile

            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                tar.add(src, arcname=os.path.basename(src))

            tar_stream.seek(0)
            container.put_archive(dest, tar_stream)
            return True

        except (NotFound, APIError) as e:
            print(f"Failed to copy to container: {e}")
            return False

    def cleanup_old_containers(self, days: int = 7) -> int:
        """Remove containers older than specified days."""
        import datetime

        removed_count = 0
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)

        for container in self.list_sandbox_containers():
            if container.status == "exited":
                created_str = container.labels.get("sandbox.claude.created", "")
                if created_str:
                    try:
                        created_date = datetime.datetime.fromisoformat(created_str)
                        if created_date < cutoff_date:
                            container.remove()
                            removed_count += 1
                    except (ValueError, APIError):
                        pass

        return removed_count
