"""
Constants used throughout sandbox-claude application.
"""

# Application metadata
APP_VERSION = "1.0.0"
APP_NAME = "sandbox-claude"

# Docker configuration
DEFAULT_DOCKER_IMAGE = "sandbox-claude-base:latest"
DEFAULT_DOCKER_USER = "sandman"
DOCKER_WORKSPACE_PATH = "/workspace"
DOCKER_BUILD_TIMEOUT_SECONDS = 600
DOCKER_STOP_TIMEOUT_SECONDS = 10

# Container configuration
CONTAINER_NAME_PREFIX = "sandbox-claude"
CONTAINER_LABEL_PREFIX = "sandbox.claude"
CONTAINER_LABEL_VERSION = f"{CONTAINER_LABEL_PREFIX}.version"
CONTAINER_LABEL_PROJECT = f"{CONTAINER_LABEL_PREFIX}.project"
CONTAINER_LABEL_FEATURE = f"{CONTAINER_LABEL_PREFIX}.feature"
CONTAINER_LABEL_CREATED = f"{CONTAINER_LABEL_PREFIX}.created"

# Path constants
CLAUDE_CONFIG_DIR_NAME = ".claude"
CLAUDE_CONFIG_FILE_NAME = ".claude.json"
CLAUDE_CREDS_OLD_FILE_NAME = ".claude_creds.json"
CLAUDE_CREDS_NEW_FILE_NAME = ".credentials.json"
SANDBOX_CONFIG_DIR_NAME = ".sandbox_claude"
SHARED_CONFIG_TEMP_DIR = "/tmp/csandbox/.claude"

# Container mount paths
CONTAINER_CLAUDE_CONFIG_PATH = "/root/.claude"
CONTAINER_CLAUDE_JSON_PATH = "/root/.claude.json"
CONTAINER_HOST_CONFIG_MOUNT = "/host-claude-config"
CONTAINER_TEMP_CLAUDE_HOST = "/tmp/.claude.host"
CONTAINER_TEMP_CLAUDE_JSON_HOST = "/tmp/.claude.json.host"
CONTAINER_TEMP_CLAUDE_CREDS_HOST = "/tmp/.claude_creds.json.host"

# Name validation and sanitization
MAX_NAME_LENGTH_SANITIZED = 30
MIN_NAME_LENGTH = 1
MAX_NAME_LENGTH = 50
NAME_VALIDATION_PATTERN = r"^[a-zA-Z0-9-_]+$"

# Time constants (in seconds)
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400
DAYS_FOR_OLD_TIMESTAMP = 7

# Size constants
BYTES_PER_KB = 1024.0

# Database and cleanup
DEFAULT_CLEANUP_DAYS = 30
DEFAULT_LOG_TAIL_LINES = 100

# File permissions
SENSITIVE_FILE_PERMISSION_MASK = 0o077

# Backup configuration
BACKUP_IGNORE_PATTERNS = ["*.log", "*.tmp", "__pycache__"]

# Logging
DEFAULT_LOG_LEVEL = "INFO"
LOG_DIR_NAME = "logs"
LOG_FILE_NAME = "sandbox-claude.log"
