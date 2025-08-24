"""
Tests for configuration synchronization.
"""

import pytest
import tempfile
import json
from pathlib import Path
from sandbox_claude.config_sync import ConfigSync


@pytest.fixture
def temp_home():
    """Create a temporary home directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        home_path = Path(tmpdir)
        yield home_path


@pytest.fixture
def config_sync(temp_home, monkeypatch):
    """Create a ConfigSync instance with temporary home."""
    monkeypatch.setattr(Path, "home", lambda: temp_home)
    return ConfigSync()


class TestConfigSync:
    """Test ConfigSync functionality."""

    def test_check_claude_config(self, config_sync, temp_home):
        """Test checking Claude configuration."""
        # Initially no config
        result = config_sync.check_claude_config()
        assert result["claude_dir"] is False
        assert result["claude_json"] is False
        assert result["has_config"] is False

        # Create .claude directory
        claude_dir = temp_home / ".claude"
        claude_dir.mkdir()
        result = config_sync.check_claude_config()
        assert result["claude_dir"] is True
        assert result["has_config"] is True

        # Create .claude.json
        claude_json = temp_home / ".claude.json"
        claude_json.write_text("{}")
        result = config_sync.check_claude_config()
        assert result["claude_json"] is True

    def test_get_config_files(self, config_sync, temp_home):
        """Test getting configuration files."""
        # Create config files
        claude_dir = temp_home / ".claude"
        claude_dir.mkdir()

        config1 = claude_dir / "config.yml"
        config1.write_text("test: config")

        config2 = claude_dir / "commands"
        config2.mkdir()
        config3 = config2 / "custom.md"
        config3.write_text("# Custom commands")

        claude_json = temp_home / ".claude.json"
        claude_json.write_text("{}")

        # Get files
        files = config_sync.get_config_files()
        assert len(files) == 3
        assert config1 in files
        assert config3 in files
        assert claude_json in files

    def test_validate_config(self, config_sync, temp_home):
        """Test configuration validation."""
        # No config - should be valid but with warnings
        result = config_sync.validate_config()
        assert result["valid"] is True

        # Valid JSON config
        claude_json = temp_home / ".claude.json"
        claude_json.write_text('{"api_key": "test-key"}')
        result = config_sync.validate_config()
        assert result["valid"] is True
        assert len(result["warnings"]) == 0

        # Invalid JSON
        claude_json.write_text("{invalid json}")
        result = config_sync.validate_config()
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_create_default_config(self, config_sync, temp_home):
        """Test creating default configuration."""
        # Create default config
        created = config_sync.create_default_config()
        assert created is True

        # Check files were created
        claude_dir = temp_home / ".claude"
        assert claude_dir.exists()
        assert (claude_dir / "CLAUDE.md").exists()

        claude_json = temp_home / ".claude.json"
        assert claude_json.exists()

        # Check JSON content
        with open(claude_json) as f:
            config = json.load(f)
            assert "api_key" in config
            assert "model" in config

        # Creating again should not recreate
        created = config_sync.create_default_config()
        assert created is False

    def test_project_config(self, config_sync, temp_home):
        """Test project-specific configuration."""
        # Save project config
        config = {
            "image": "custom-image:latest",
            "environment": ["DEBUG=true"],
            "ports": [8080, 3000],
        }

        result = config_sync.save_project_config("myproject", config)
        assert result is True

        # Get project config
        loaded = config_sync.get_project_config("myproject")
        assert loaded == config

        # Non-existent project
        loaded = config_sync.get_project_config("nonexistent")
        assert loaded is None

    def test_prepare_container_config(self, config_sync, temp_home):
        """Test preparing container configuration."""
        # No config files
        mounts = config_sync.prepare_container_config("test123")
        assert len(mounts) == 0

        # Create config files
        claude_dir = temp_home / ".claude"
        claude_dir.mkdir()

        claude_json = temp_home / ".claude.json"
        claude_json.write_text("{}")

        # Prepare mounts
        mounts = config_sync.prepare_container_config("test123")
        assert len(mounts) == 2
        assert "claude_config" in mounts
        assert "claude_json_host" in mounts

        # Check mount properties
        assert mounts["claude_config"]["read_only"] is True
        assert mounts["claude_json_host"]["read_only"] is True
        # Check that claude.json is mounted to temp location
        assert mounts["claude_json_host"]["target"] == "/tmp/.claude.json.host"
