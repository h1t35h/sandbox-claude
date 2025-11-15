"""
Tests for session store functionality.
"""

import tempfile
from pathlib import Path

import pytest

from sandbox_claude.session_store import SessionStore


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def store(temp_db):
    """Create a SessionStore instance with temporary database."""
    return SessionStore(db_path=temp_db)


class TestSessionStore:
    """Test SessionStore functionality."""

    def test_init_database(self, store):
        """Test database initialization."""
        # Database should be created
        assert store.db_path.exists()

    def test_add_container(self, store):
        """Test adding a container."""
        result = store.add_container(
            container_id="test123",
            container_name="sandbox-claude-test-feature-123",
            project_name="test",
            feature_name="feature",
            working_dir="/workspace",
            docker_image="sandbox-claude-base:latest",
        )
        assert result is True

        # Adding duplicate should fail
        result = store.add_container(
            container_id="test123",
            container_name="sandbox-claude-test-feature-123",
            project_name="test",
            feature_name="feature",
        )
        assert result is False

    def test_get_container(self, store):
        """Test getting container by ID."""
        # Add a container
        store.add_container(
            container_id="test123",
            container_name="sandbox-claude-test-feature-123",
            project_name="test",
            feature_name="feature",
        )

        # Get it back
        container = store.get_container("test123")
        assert container is not None
        assert container["container_id"] == "test123"
        assert container["project_name"] == "test"
        assert container["feature_name"] == "feature"

        # Non-existent container
        container = store.get_container("nonexistent")
        assert container is None

    def test_find_container(self, store):
        """Test finding containers by project/feature."""
        # Add containers
        store.add_container(
            container_id="test1",
            container_name="sandbox-1",
            project_name="project1",
            feature_name="feature1",
        )
        store.add_container(
            container_id="test2",
            container_name="sandbox-2",
            project_name="project1",
            feature_name="feature2",
        )
        store.add_container(
            container_id="test3",
            container_name="sandbox-3",
            project_name="project2",
            feature_name="feature1",
        )

        # Find by project
        container = store.find_container(project="project1")
        assert container is not None
        assert container["project_name"] == "project1"

        # Find by feature
        container = store.find_container(feature="feature1")
        assert container is not None
        assert container["feature_name"] == "feature1"

        # Find by both
        container = store.find_container(project="project1", feature="feature2")
        assert container is not None
        assert container["container_id"] == "test2"

    def test_list_containers(self, store):
        """Test listing containers."""
        # Add multiple containers
        for i in range(3):
            store.add_container(
                container_id=f"test{i}",
                container_name=f"sandbox-{i}",
                project_name="project",
                feature_name=f"feature{i}",
            )

        # List all
        containers = store.list_containers()
        assert len(containers) == 3

        # List with limit
        containers = store.list_containers(limit=2)
        assert len(containers) == 2

        # List by project
        containers = store.list_containers(project="project")
        assert len(containers) == 3

        # List by non-existent project
        containers = store.list_containers(project="nonexistent")
        assert len(containers) == 0

    def test_update_container_status(self, store):
        """Test updating container status."""
        # Add container
        store.add_container(
            container_id="test123",
            container_name="sandbox-test",
            project_name="test",
            feature_name="feature",
        )

        # Update status
        result = store.update_container_status("test123", "stopped")
        assert result is True

        # Verify update
        container = store.get_container("test123")
        assert container["status"] == "stopped"

        # Update non-existent container
        result = store.update_container_status("nonexistent", "stopped")
        assert result is False

    def test_remove_container(self, store):
        """Test removing a container."""
        # Add container
        store.add_container(
            container_id="test123",
            container_name="sandbox-test",
            project_name="test",
            feature_name="feature",
        )

        # Remove it
        result = store.remove_container("test123")
        assert result is True

        # Verify removal
        container = store.get_container("test123")
        assert container is None

        # Remove non-existent container
        result = store.remove_container("nonexistent")
        assert result is False

    def test_get_statistics(self, store):
        """Test getting statistics."""
        # Add containers with different statuses
        store.add_container(
            container_id="test1",
            container_name="sandbox-1",
            project_name="project1",
            feature_name="feature1",
        )
        store.add_container(
            container_id="test2",
            container_name="sandbox-2",
            project_name="project1",
            feature_name="feature2",
        )
        store.add_container(
            container_id="test3",
            container_name="sandbox-3",
            project_name="project2",
            feature_name="feature1",
        )

        # Update one to stopped
        store.update_container_status("test3", "stopped")

        # Get statistics
        stats = store.get_statistics()
        assert stats["total"] == 3
        assert stats["running"] == 2
        assert len(stats["by_project"]) == 2
