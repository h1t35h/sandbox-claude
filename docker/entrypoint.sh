#!/bin/bash
# Entrypoint script for sandbox-claude containers
# Handles environment setup, git configuration, and Claude CLI initialization

set -e

# ================================================================================
# LOGGING FUNCTIONS
# ================================================================================

print_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

print_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

print_separator() {
    echo "────────────────────────────────────────────────────────────────"
}

print_header() {
    echo "════════════════════════════════════════════════════════════════"
    echo "     🚀 Sandbox Claude Container Environment"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
}

# ================================================================================
# ENVIRONMENT SETUP
# ================================================================================

# Initialize user environment
setup_user_environment() {
    # Determine user home directory
    if [ "$(id -u)" = "0" ]; then
        USER_HOME="/root"
        USER_NAME="root"
    else
        USER_HOME="/home/sandman"
        USER_NAME="sandman"
    fi
    
    # Set Claude config directory (can be overridden by environment)
    # Default to /claude-config which should be mounted from host's /tmp/csandbox/.claude
    CLAUDE_CONFIG_DIR=${CLAUDE_CONFIG_DIR:-/claude-config}
    export CLAUDE_CONFIG_DIR
}

# Display environment information
show_environment_info() {
    print_info "Running as user: $USER_NAME (UID: $(id -u))"
    print_info "Container Information:"
    echo "  • Project: ${SANDBOX_PROJECT:-undefined}"
    echo "  • Feature: ${SANDBOX_FEATURE:-undefined}"
    echo "  • Workspace: /workspace"
    echo "  • Python: $(python --version 2>&1)"
    echo "  • Node: $(node --version)"
    echo "  • Git: $(git --version)"
    echo ""
}

# ================================================================================
# CLAUDE CONFIGURATION MANAGEMENT
# ================================================================================

# Setup Claude configuration directory
setup_claude_config_dir() {
    if [ -d "$CLAUDE_CONFIG_DIR" ] && [ -w "$CLAUDE_CONFIG_DIR" ]; then
        print_success "Claude config directory mounted at: $CLAUDE_CONFIG_DIR"
        CONFIG_MODE="mounted"
    elif [ -d "$CLAUDE_CONFIG_DIR" ]; then
        fix_config_dir_permissions
    else
        fallback_to_workspace_config
    fi
    
    # Ensure workspace config directory exists if needed
    if [ "$CONFIG_MODE" = "workspace" ]; then
        mkdir -p "$CLAUDE_CONFIG_DIR"
        chown $(id -u):$(id -g) "$CLAUDE_CONFIG_DIR"
        chmod 755 "$CLAUDE_CONFIG_DIR"
    fi
}

# Fix permissions for existing config directory
fix_config_dir_permissions() {
    if [ "$(id -u)" = "0" ]; then
        # Running as root, can fix permissions
        chown sandman:sandman "$CLAUDE_CONFIG_DIR"
        chmod 755 "$CLAUDE_CONFIG_DIR"
        print_info "Fixed permissions for Claude config directory: $CLAUDE_CONFIG_DIR"
        CONFIG_MODE="mounted"
    else
        # Running as sandman, check if we own it
        if [ "$(stat -c %u $CLAUDE_CONFIG_DIR)" = "$(id -u)" ]; then
            chmod 755 "$CLAUDE_CONFIG_DIR"
            CONFIG_MODE="mounted"
        else
            print_error "Claude config directory exists but is not writable: $CLAUDE_CONFIG_DIR"
            fallback_to_workspace_config
        fi
    fi
}

# Fallback to workspace-based configuration
fallback_to_workspace_config() {
    print_info "Falling back to workspace-based config"
    CLAUDE_CONFIG_DIR="/workspace/.claude-config"
    export CLAUDE_CONFIG_DIR
    CONFIG_MODE="workspace"
}

# Copy configuration file with proper permissions
copy_config_file() {
    local src="$1"
    local dst="$2"
    local perms="$3"
    local name="$4"
    
    if [ -f "$src" ]; then
        cp "$src" "$dst"
        chmod "$perms" "$dst"
        print_success "Loaded $name from shared host directory"
        return 0
    fi
    return 1
}

# Load Claude configuration from shared host directory
load_shared_host_config() {
    if [ -d "/host-claude-config" ] && [ -r "/host-claude-config" ]; then
        print_info "Checking shared host config directory for updates..."

        copy_config_file "/host-claude-config/.claude.json" \
                        "$CLAUDE_CONFIG_DIR/.claude.json" \
                        600 ".claude.json" || true

        copy_config_file "/host-claude-config/.credentials.json" \
                        "$CLAUDE_CONFIG_DIR/.credentials.json" \
                        600 ".credentials.json" || true

        copy_config_file "/host-claude-config/CLAUDE.md" \
                        "$CLAUDE_CONFIG_DIR/CLAUDE.md" \
                        644 "CLAUDE.md" || true
    fi
}

# Setup initial Claude configuration files
setup_claude_config_files() {
    # Setup .claude.json
    if [ ! -f "$CLAUDE_CONFIG_DIR/.claude.json" ]; then
        if [ -f "/tmp/.claude.json.host" ]; then
            print_info "Copying Claude configuration from host to $CLAUDE_CONFIG_DIR"
            cp /tmp/.claude.json.host "$CLAUDE_CONFIG_DIR/.claude.json"
            chmod 600 "$CLAUDE_CONFIG_DIR/.claude.json"
            print_success "Claude configuration copied from host"
        else
            print_info "Creating new Claude configuration file at $CLAUDE_CONFIG_DIR"
            echo '{}' > "$CLAUDE_CONFIG_DIR/.claude.json"
            chmod 600 "$CLAUDE_CONFIG_DIR/.claude.json"
            print_info "Claude will configure on first run. Remember to add your API key."
        fi
    else
        print_success "Using existing Claude configuration from $CLAUDE_CONFIG_DIR"
    fi
    
    # Copy .claude directory contents from host if needed
    if [ ! -f "$CLAUDE_CONFIG_DIR/.credentials.json" ] && [ ! -f "$CLAUDE_CONFIG_DIR/CLAUDE.md" ]; then
        if [ -d "/tmp/.claude.host" ]; then
            print_info "Copying .claude directory contents from host to $CLAUDE_CONFIG_DIR"
            cp -r /tmp/.claude.host/. "$CLAUDE_CONFIG_DIR/"
            chmod -R 700 "$CLAUDE_CONFIG_DIR"
            print_success "Claude directory contents copied from host"
        fi
    fi
    
    # Setup credentials file
    if [ ! -f "$CLAUDE_CONFIG_DIR/.credentials.json" ]; then
        if [ -f "/tmp/.claude_creds.json.host" ]; then
            print_info "Copying credentials from host to $CLAUDE_CONFIG_DIR"
            cp /tmp/.claude_creds.json.host "$CLAUDE_CONFIG_DIR/.credentials.json"
            chmod 600 "$CLAUDE_CONFIG_DIR/.credentials.json"
            print_success "Claude credentials copied from host"
        else
            print_info "No credentials file found. Claude will prompt for authentication on first use."
        fi
    else
        print_success "Using existing credentials from $CLAUDE_CONFIG_DIR"
    fi
}

# List configuration files
list_config_files() {
    if [ "$(ls -A $CLAUDE_CONFIG_DIR 2>/dev/null)" ]; then
        echo "  Configuration files:"
        ls -la "$CLAUDE_CONFIG_DIR" | grep -E "^-" | awk '{print "    • " $9}'
    fi
}

# ================================================================================
# WORKSPACE SETUP
# ================================================================================

# Check and setup workspace
setup_workspace() {
    if [ ! -d "/workspace" ]; then
        print_error "Workspace directory not found"
        return 1
    fi

    cd /workspace
    print_success "Workspace mounted at /workspace"

    # Check if it's a git repository
    if [ -d ".git" ] || [ -f ".git" ]; then
        echo "  Git repository detected:"
        echo "    • Branch: $(git branch --show-current 2>/dev/null || echo 'detached')"
        echo "    • Status: $(git status --porcelain 2>/dev/null | wc -l) modified files"
    fi

    detect_project_type
}

# Detect project type from files
detect_project_type() {
    if [ -f "package.json" ]; then
        echo "  Node.js project detected"
    fi
    if [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]; then
        echo "  Python project detected"
    fi
}

# ================================================================================
# GIT CONFIGURATION
# ================================================================================

# Initialize git global configuration
setup_git_config() {
    if ! git config --global user.email >/dev/null 2>&1; then
        print_info "Setting up Git global configuration..."
        git config --global user.email "sandbox@claude.local" 2>/dev/null || true
        git config --global user.name "Sandbox Claude" 2>/dev/null || true
        # Note: init.defaultBranch, safe.directory, and core.excludesfile are set in Dockerfile
        # Only set user identity here to avoid overriding Dockerfile settings
    fi
}

# ================================================================================
# SESSION MANAGEMENT
# ================================================================================

# Create session file
create_session_file() {
    local session_file="/tmp/.sandbox_session"
    cat > "$session_file" << EOF
SESSION_ID=$(uuidgen 2>/dev/null || echo "$(date +%s)")
PROJECT=${SANDBOX_PROJECT:-unknown}
FEATURE=${SANDBOX_FEATURE:-unknown}
STARTED=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF
}

# Setup shell history
setup_shell_history() {
    export HISTFILE=/workspace/.sandbox_history
    export HISTSIZE=10000
    export HISTFILESIZE=10000
    export HISTCONTROL=ignoreboth:erasedups
}

# ================================================================================
# ALIASES AND FUNCTIONS
# ================================================================================

# Setup command aliases
setup_aliases() {
    # Sandbox management aliases
    alias sandbox-info='cat /tmp/.sandbox_session'
    alias sandbox-update='apt-get update && apt-get upgrade -y'
    alias sandbox-install='apt-get install -y'
    
    # Claude command with proper config directory
    alias claude='CLAUDE_CONFIG_DIR=$CLAUDE_CONFIG_DIR claude --dangerously-skip-permissions'
    
    # Configuration sync aliases
    alias claude-sync='/usr/local/bin/sync-claude-config.sh'
    alias sync-claude='/usr/local/bin/sync-claude-config.sh'
    alias claude-save='/usr/local/bin/sync-claude-config.sh'
    
    # Configuration pull aliases
    alias claude-pull='/usr/local/bin/pull-claude-config.sh'
    alias pull-claude='/usr/local/bin/pull-claude-config.sh'
    alias claude-refresh='/usr/local/bin/pull-claude-config.sh'
    
    # Status alias
    alias claude-config-status='show_claude_config'
}

# Show Claude configuration status
show_claude_config() {
    echo "[INFO] Claude configuration directory: $CLAUDE_CONFIG_DIR" >&2
    echo "[INFO] Config mode: $CONFIG_MODE" >&2
    
    [ -f "$CLAUDE_CONFIG_DIR/.claude.json" ] && echo "  • .claude.json exists" >&2
    [ -f "$CLAUDE_CONFIG_DIR/.credentials.json" ] && echo "  • .credentials.json exists" >&2
    [ -f "$CLAUDE_CONFIG_DIR/CLAUDE.md" ] && echo "  • CLAUDE.md exists" >&2
    
    if [ "$CONFIG_MODE" = "mounted" ]; then
        echo "[INFO] Configuration shared across containers (mounted volume)" >&2
    else
        echo "[INFO] Configuration stored in workspace (container-specific)" >&2
    fi
}

# Export functions for subshells
export -f show_claude_config

# Check Claude Code CLI availability
check_claude_cli() {
    if command -v claude &> /dev/null; then
        print_success "Claude Code CLI is available"
        echo "  • Command: claude"
        echo "  • Version: $(claude --version 2>/dev/null || echo 'version check failed')"
        echo "  • Usage: Type 'claude --help' for commands"
    else
        print_info "Claude Code CLI not found. Installing might have failed."
        print_info "You can try: npm install -g @anthropic-ai/claude-code"
    fi
}

# Display Claude configuration help
show_claude_help() {
    print_separator
    echo "Claude Configuration Commands:"
    echo "  Push to host:"
    echo "    • claude-sync   - Sync updated configs back to host"
    echo "    • claude-save   - Same as claude-sync"
    echo "    • claude-login  - Login to Claude and auto-sync"
    echo "  Pull from host:"
    echo "    • claude-pull   - Pull latest configs from host"
    echo "    • claude-refresh - Same as claude-pull"
    echo ""
    print_info "Use 'claude-pull' to refresh configs, 'claude-sync' to save them"
    print_separator
}

# ================================================================================
# MAIN EXECUTION
# ================================================================================

main() {
    # Display header
    print_header
    
    # Setup environment
    setup_user_environment
    show_environment_info
    
    # Setup Claude configuration
    setup_claude_config_dir
    print_info "Claude config directory: $CLAUDE_CONFIG_DIR (mode: $CONFIG_MODE)"
    
    # Load configurations
    load_shared_host_config
    setup_claude_config_files
    list_config_files

    # Setup workspace and git
    setup_workspace
    setup_git_config
    
    echo ""
    print_separator
    
    # Setup session and shell
    create_session_file
    setup_shell_history
    setup_aliases
    
    # Check Claude CLI
    check_claude_cli
    
    echo ""
    show_claude_help
    echo ""
    
    print_success "Container ready! Type 'exit' to leave the sandbox."
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    # Execute the command passed to the container
    exec "$@"
}

# Run main function
main "$@"
