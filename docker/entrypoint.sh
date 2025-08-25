#!/bin/bash
# Entrypoint script for sandbox-claude containers

set -e

# Function to print colored output
print_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# Welcome message
echo "════════════════════════════════════════════════════════════════"
echo "     🚀 Sandbox Claude Container Environment"
echo "════════════════════════════════════════════════════════════════"
echo ""
print_info "Running as user: $USER_NAME (UID: $(id -u))"

# Display environment info
print_info "Container Information:"
echo "  • Project: ${SANDBOX_PROJECT:-undefined}"
echo "  • Feature: ${SANDBOX_FEATURE:-undefined}"
echo "  • Workspace: /workspace"
echo "  • Python: $(python --version 2>&1)"
echo "  • Node: $(node --version)"
echo "  • Git: $(git --version)"
echo ""

# Determine user home directory
if [ "$(id -u)" = "0" ]; then
    USER_HOME="/root"
    USER_NAME="root"
else
    USER_HOME="/home/sandman"
    USER_NAME="sandman"
fi

# Check and setup Claude configuration
# Copy the host's .claude.json if it was mounted to temp location
if [ -f "/tmp/.claude.json.host" ]; then
    # Check if there's a persisted version in workspace first
    if [ -f "/workspace/.sandbox-claude/.claude.json" ]; then
        print_info "Restoring Claude configuration from previous session"
        cp /workspace/.sandbox-claude/.claude.json $USER_HOME/.claude.json
    else
        print_info "Copying Claude configuration from host (writable copy)"
        cp /tmp/.claude.json.host $USER_HOME/.claude.json
    fi
    chmod 600 $USER_HOME/.claude.json  # Secure permissions
    print_success "Claude configuration ready (editable)"
elif [ -f "/workspace/.sandbox-claude/.claude.json" ]; then
    # No host config, but we have a persisted one
    print_info "Restoring Claude configuration from previous session"
    cp /workspace/.sandbox-claude/.claude.json $USER_HOME/.claude.json
    chmod 600 $USER_HOME/.claude.json
    print_success "Claude configuration restored"
else
    # No config exists, create an empty one for Claude to populate
    print_info "Creating new Claude configuration file"
    echo '{}' > $USER_HOME/.claude.json
    chmod 600 $USER_HOME/.claude.json
    print_info "Claude will configure on first run. Remember to add your API key."
fi

# Check and setup .claude directory
if [ -d "/tmp/.claude.host" ]; then
    # Copy the host's .claude directory if it was mounted to temp location
    if [ -d "/workspace/.sandbox-claude/.claude" ]; then
        print_info "Restoring .claude directory from previous session"
        rm -rf $USER_HOME/.claude
        cp -r /workspace/.sandbox-claude/.claude/. $USER_HOME/.claude
    else
        print_info "Copying .claude directory from host (writable copy)"
        cp -r /tmp/.claude.host/. $USER_HOME/.claude
    fi
    chmod -R 700 $USER_HOME/.claude  # Secure permissions
    print_success "Claude directory ready (editable)"
    # List configuration files
    if [ "$(ls -A $USER_HOME/.claude 2>/dev/null)" ]; then
        echo "  Configuration files:"
        ls -la $USER_HOME/.claude | grep -E "^-" | awk '{print "    • " $9}'
    fi
elif [ -d "/workspace/.sandbox-claude/.claude" ]; then
    # No host config, but we have a persisted one
    print_info "Restoring .claude directory from previous session"
    cp -r /workspace/.sandbox-claude/.claude/. $USER_HOME/.claude
    chmod -R 700 $USER_HOME/.claude
    print_success "Claude directory restored"
else
    # Create empty .claude directory
    print_info "Creating new .claude directory"
    mkdir -p $USER_HOME/.claude
    chmod 700 $USER_HOME/.claude
fi

# Check and setup credentials file
if [ -f "/tmp/.claude_creds.json.host" ]; then
    # Ensure .claude directory exists
    mkdir -p $USER_HOME/.claude
    
    # Check if there's a persisted version in workspace first
    if [ -f "/workspace/.sandbox-claude/.credentials.json" ]; then
        print_info "Restoring credentials from previous session"
        cp /workspace/.sandbox-claude/.credentials.json $USER_HOME/.claude/.credentials.json
    else
        print_info "Copying credentials from host (writable copy)"
        cp /tmp/.claude_creds.json.host $USER_HOME/.claude/.credentials.json
    fi
    chmod 600 $USER_HOME/.claude/.credentials.json  # Secure permissions
    print_success "Claude credentials ready (.credentials.json)"
elif [ -f "/workspace/.sandbox-claude/.credentials.json" ]; then
    # No host creds, but we have a persisted one
    mkdir -p $USER_HOME/.claude
    print_info "Restoring credentials from previous session"
    cp /workspace/.sandbox-claude/.credentials.json $USER_HOME/.claude/.credentials.json
    chmod 600 $USER_HOME/.claude/.credentials.json
    print_success "Claude credentials restored"
fi

# Initialize git config if not set
if [ -z "$(git config --global user.email)" ]; then
    print_info "Setting up Git configuration..."
    git config --global user.email "sandbox@claude.local"
    git config --global user.name "Sandbox Claude"
    git config --global init.defaultBranch main
fi

# Check workspace
if [ -d "/workspace" ]; then
    cd /workspace
    print_success "Workspace mounted at /workspace"
    
    # Check if it's a git repository
    if [ -d ".git" ]; then
        echo "  Git repository detected:"
        echo "    • Branch: $(git branch --show-current 2>/dev/null || echo 'detached')"
        echo "    • Status: $(git status --porcelain | wc -l) modified files"
    fi
    
    # Check for project files
    if [ -f "package.json" ]; then
        echo "  Node.js project detected"
    fi
    if [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]; then
        echo "  Python project detected"
    fi
else
    print_error "Workspace directory not found"
fi

echo ""
echo "────────────────────────────────────────────────────────────────"

# Create session file
SESSION_FILE="/tmp/.sandbox_session"
cat > "$SESSION_FILE" << EOF
SESSION_ID=$(uuidgen 2>/dev/null || echo "$(date +%s)")
PROJECT=${SANDBOX_PROJECT:-unknown}
FEATURE=${SANDBOX_FEATURE:-unknown}
STARTED=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

# Setup command history
export HISTFILE=/workspace/.sandbox_history
export HISTSIZE=10000
export HISTFILESIZE=10000
export HISTCONTROL=ignoreboth:erasedups

# Custom aliases for the sandbox environment
alias sandbox-info='cat /tmp/.sandbox_session'
alias sandbox-update='apt-get update && apt-get upgrade -y'
alias sandbox-install='apt-get install -y'
alias claude='claude --dangerously-skip-permissions'

# Function to persist Claude configuration
persist_claude_config() {
    if [ -d "/workspace" ]; then
        mkdir -p /workspace/.sandbox-claude
        
        # Save .claude.json if it exists
        if [ -f "$USER_HOME/.claude.json" ]; then
            cp $USER_HOME/.claude.json /workspace/.sandbox-claude/.claude.json
            echo "[INFO] Claude configuration (.claude.json) saved for next session" >&2
        fi
        
        # Save .claude directory if it exists
        if [ -d "$USER_HOME/.claude" ]; then
            rm -rf /workspace/.sandbox-claude/.claude
            cp -r $USER_HOME/.claude/. /workspace/.sandbox-claude/.claude
            echo "[INFO] Claude directory (.claude/) saved for next session" >&2
        fi
        
        # Save credentials file if it exists
        if [ -f "$USER_HOME/.claude/.credentials.json" ]; then
            cp $USER_HOME/.claude/.credentials.json /workspace/.sandbox-claude/.credentials.json
            echo "[INFO] Claude credentials (.credentials.json) saved for next session" >&2
        fi
    fi
}

# Export function so it's available in subshells
export -f persist_claude_config

# Set up trap to persist config on exit (for interactive sessions)
trap persist_claude_config EXIT

# Also add an alias for manual save
alias save-claude-config='persist_claude_config'

# Function to check Claude Code status
check_claude() {
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

# Run Claude check
check_claude

echo ""
print_success "Container ready! Type 'exit' to leave the sandbox."
echo "════════════════════════════════════════════════════════════════"
echo ""

# Execute the command passed to the container
exec "$@"