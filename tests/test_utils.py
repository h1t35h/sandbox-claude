"""
Tests for utility functions.
"""

from sandbox_claude.utils import (
    format_size,
    format_timestamp,
    generate_container_name,
    parse_environment,
    parse_ports,
    sanitize_name,
    validate_name,
)


class TestContainerNaming:
    """Test container naming functions."""

    def test_generate_container_name(self):
        """Test container name generation."""
        name = generate_container_name("myproject", "feature1")
        assert name.startswith("sandbox-claude-myproject-feature1-")
        assert len(name.split("-")) >= 6  # Has timestamp and random suffix

    def test_sanitize_name(self):
        """Test name sanitization."""
        assert sanitize_name("my-project") == "my-project"
        assert sanitize_name("My Project!") == "my-project"
        assert sanitize_name("feature@123") == "feature-123"
        assert sanitize_name("test__feature") == "test-feature"
        assert sanitize_name("-leading-") == "leading"

    def test_validate_name(self):
        """Test name validation."""
        assert validate_name("valid-name_123") is True
        assert validate_name("invalid name") is False
        assert validate_name("invalid@name") is False
        assert validate_name("") is False


class TestFormatting:
    """Test formatting functions."""

    def test_format_size(self):
        """Test size formatting."""
        assert format_size(100) == "100.0 B"
        assert format_size(1024) == "1.0 KB"
        assert format_size(1024 * 1024) == "1.0 MB"
        assert format_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        # Recent timestamp
        from datetime import datetime, timedelta

        now = datetime.now()
        recent = (now - timedelta(minutes=5)).isoformat()
        result = format_timestamp(recent)
        assert "minute" in result or "just now" in result

        # Old timestamp
        old = (now - timedelta(days=30)).isoformat()
        result = format_timestamp(old)
        assert "-" in result  # Should show date


class TestParsing:
    """Test parsing functions."""

    def test_parse_ports(self):
        """Test port parsing."""
        # Single port
        ports = parse_ports("8080")
        assert ports == {"8080/tcp": 8080}

        # Port mapping
        ports = parse_ports("8080:80")
        assert ports == {"80/tcp": 8080}

        # Multiple ports
        ports = parse_ports("8080:80,3000:3000")
        assert ports == {"80/tcp": 8080, "3000/tcp": 3000}

        # Invalid input
        ports = parse_ports("invalid")
        assert ports == {}

    def test_parse_environment(self):
        """Test environment variable parsing."""
        # Single variable
        env = parse_environment("KEY=value")
        assert env == {"KEY": "value"}

        # Multiple variables
        env = parse_environment("KEY1=value1,KEY2=value2")
        assert env == {"KEY1": "value1", "KEY2": "value2"}

        # With equals in value
        env = parse_environment("KEY=value=with=equals")
        assert env == {"KEY": "value=with=equals"}

        # Empty input
        env = parse_environment("")
        assert env == {}
