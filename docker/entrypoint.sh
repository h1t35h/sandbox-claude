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

print_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

# Welcome message
echo "════════════════════════════════════════════════════════════════"
echo "     🚀 Sandbox Claude Container Environment"
echo "════════════════════════════════════════════════════════════════"
echo ""
# Set Claude config directory (can be overridden by environment)
# Default to /claude-config which should be mounted from host's /tmp/csandbox/.claude
CLAUDE_CONFIG_DIR=${CLAUDE_CONFIG_DIR:-/claude-config}
export CLAUDE_CONFIG_DIR

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

# Check if Claude config directory is mounted and writable
if [ -d "$CLAUDE_CONFIG_DIR" ] && [ -w "$CLAUDE_CONFIG_DIR" ]; then
    print_success "Claude config directory mounted at: $CLAUDE_CONFIG_DIR"
    CONFIG_MODE="mounted"
elif [ -d "$CLAUDE_CONFIG_DIR" ]; then
    # Directory exists but might not be writable, try to fix permissions
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
            print_info "Falling back to workspace-based config"
            CLAUDE_CONFIG_DIR="/workspace/.claude-config"
            export CLAUDE_CONFIG_DIR
            CONFIG_MODE="workspace"
        fi
    fi
else
    print_info "Claude config directory not mounted, using workspace-based config"
    CLAUDE_CONFIG_DIR="/workspace/.claude-config"
    export CLAUDE_CONFIG_DIR
    CONFIG_MODE="workspace"
fi

# Ensure Claude config directory exists and has proper permissions
if [ "$CONFIG_MODE" = "workspace" ]; then
    mkdir -p "$CLAUDE_CONFIG_DIR"
    chown $(id -u):$(id -g) "$CLAUDE_CONFIG_DIR"
    chmod 755 "$CLAUDE_CONFIG_DIR"
fi

# Check and setup Claude configuration using CLAUDE_CONFIG_DIR
# The Claude CLI will look for configs in $CLAUDE_CONFIG_DIR
print_info "Claude config directory: $CLAUDE_CONFIG_DIR (mode: $CONFIG_MODE)"

# First, check if there's a shared host config directory with updated configs
if [ -d "/host-claude-config" ] && [ -r "/host-claude-config" ]; then
    print_info "Checking shared host config directory for updates..."
    
    # Copy any existing configs from the shared directory first (these are most recent)
    if [ -f "/host-claude-config/.claude.json" ]; then
        cp "/host-claude-config/.claude.json" "$CLAUDE_CONFIG_DIR/.claude.json"
        chmod 600 "$CLAUDE_CONFIG_DIR/.claude.json"
        print_success "Loaded .claude.json from shared host directory"
    fi
    
    if [ -f "/host-claude-config/.credentials.json" ]; then
        cp "/host-claude-config/.credentials.json" "$CLAUDE_CONFIG_DIR/.credentials.json"
        chmod 600 "$CLAUDE_CONFIG_DIR/.credentials.json"
        print_success "Loaded .credentials.json from shared host directory"
    fi
    
    if [ -f "/host-claude-config/CLAUDE.md" ]; then
        cp "/host-claude-config/CLAUDE.md" "$CLAUDE_CONFIG_DIR/CLAUDE.md"
        chmod 644 "$CLAUDE_CONFIG_DIR/CLAUDE.md"
        print_success "Loaded CLAUDE.md from shared host directory"
    fi
fi

# Only copy from host mounts if config directory doesn't have files already
if [ ! -f "$CLAUDE_CONFIG_DIR/.claude.json" ]; then
    # Copy the host's .claude.json if it was mounted to temp location
    if [ -f "/tmp/.claude.json.host" ]; then
        print_info "Copying Claude configuration from host to $CLAUDE_CONFIG_DIR"
        cp /tmp/.claude.json.host "$CLAUDE_CONFIG_DIR/.claude.json"
        chmod 600 "$CLAUDE_CONFIG_DIR/.claude.json"  # Secure permissions
        print_success "Claude configuration copied from host"
    else
        # No config exists, create an empty one for Claude to populate
        print_info "Creating new Claude configuration file at $CLAUDE_CONFIG_DIR"
        echo '{}' > "$CLAUDE_CONFIG_DIR/.claude.json"
        chmod 600 "$CLAUDE_CONFIG_DIR/.claude.json"
        print_info "Claude will configure on first run. Remember to add your API key."
    fi
else
    print_success "Using existing Claude configuration from $CLAUDE_CONFIG_DIR"
fi

# Check and setup .claude directory contents in CLAUDE_CONFIG_DIR
# Only copy from host if we don't have existing files
if [ ! -f "$CLAUDE_CONFIG_DIR/.credentials.json" ] && [ ! -f "$CLAUDE_CONFIG_DIR/CLAUDE.md" ]; then
    if [ -d "/tmp/.claude.host" ]; then
        print_info "Copying .claude directory contents from host to $CLAUDE_CONFIG_DIR"
        # Copy all files from host's .claude directory to CLAUDE_CONFIG_DIR
        cp -r /tmp/.claude.host/. "$CLAUDE_CONFIG_DIR/"
        chmod -R 700 "$CLAUDE_CONFIG_DIR"  # Secure permissions
        print_success "Claude directory contents copied from host"
    fi
fi

# List configuration files if any exist
if [ "$(ls -A $CLAUDE_CONFIG_DIR 2>/dev/null)" ]; then
    echo "  Configuration files:"
    ls -la "$CLAUDE_CONFIG_DIR" | grep -E "^-" | awk '{print "    • " $9}'
fi

# Check and setup credentials file in CLAUDE_CONFIG_DIR
if [ ! -f "$CLAUDE_CONFIG_DIR/.credentials.json" ]; then
    if [ -f "/tmp/.claude_creds.json.host" ]; then
        print_info "Copying credentials from host to $CLAUDE_CONFIG_DIR"
        cp /tmp/.claude_creds.json.host "$CLAUDE_CONFIG_DIR/.credentials.json"
        chmod 600 "$CLAUDE_CONFIG_DIR/.credentials.json"  # Secure permissions
        print_success "Claude credentials copied from host"
    else
        print_info "No credentials file found. Claude will prompt for authentication on first use."
    fi
else
    print_success "Using existing credentials from $CLAUDE_CONFIG_DIR"
fi

# Check workspace
if [ -d "/workspace" ]; then
    cd /workspace
    print_success "Workspace mounted at /workspace"
    
    # Check if it's a git worktree (when .git is a file)
    if [ -f ".git" ]; then
        print_info "Git worktree detected"
        
        # Save the original .git content
        ORIG_GIT_CONTENT=$(cat .git)
        
        # Check if main git directory was mounted (read-only)
        if [ -d "/workspace/.git_main" ]; then
            print_info "Creating container-local git metadata copy..."
            
            # Copy the read-only git metadata to a writable location
            cp -r /workspace/.git_main /workspace/.git_container 2>/dev/null || {
                print_error "Failed to copy git metadata"
                print_info "Converting to standalone git repository"
                rm -f .git
                git init
                git add .
                echo "  Git repository initialized (standalone)"
                # Exit this block early
                return 0 2>/dev/null || true
            }
            
            # Read the original .git file to get the worktree path
            ORIG_GITDIR=$(echo "$ORIG_GIT_CONTENT" | sed 's/gitdir: //')
            
            # Extract just the worktree directory name (last component)
            WORKTREE_NAME=$(basename "$ORIG_GITDIR")
            
            # Check if the worktree directory exists in the copied git directory
            if [ -d "/workspace/.git_container/worktrees/$WORKTREE_NAME" ]; then
                # Update the .git file to point to the container copy
                echo "gitdir: /workspace/.git_container/worktrees/$WORKTREE_NAME" > .git
                
                # Update the gitdir file in the container copy to point to container paths
                echo "/workspace/.git" > "/workspace/.git_container/worktrees/$WORKTREE_NAME/gitdir"
                
                print_success "Git worktree configuration adapted for container"
            else
                # Try to find the correct worktree directory
                print_info "Looking for worktree in copied git directory..."
                if [ -d "/workspace/.git_container/worktrees" ]; then
                    # List available worktrees
                    AVAILABLE_WORKTREES=$(ls -1 /workspace/.git_container/worktrees 2>/dev/null | head -n 1)
                    if [ -n "$AVAILABLE_WORKTREES" ]; then
                        echo "gitdir: /workspace/.git_container/worktrees/$AVAILABLE_WORKTREES" > .git
                        # Update the gitdir file in the container copy
                        echo "/workspace/.git" > "/workspace/.git_container/worktrees/$AVAILABLE_WORKTREES/gitdir"
                        print_success "Git worktree configuration adapted (using: $AVAILABLE_WORKTREES)"
                    else
                        print_warning "No worktrees found in copied git directory"
                        print_info "Converting to standalone git repository"
                        # Convert to a standalone repository
                        rm -f .git
                        rm -rf .git_container
                        git init
                        git add .
                    fi
                else
                    print_warning "Worktrees directory not found in copied git"
                    print_info "Converting to standalone git repository"
                    # Convert to a standalone repository
                    rm -f .git
                    rm -rf .git_container
                    git init
                    git add .
                fi
            fi
            
            # Try to show git status
            if git status >/dev/null 2>&1; then
                echo "  Git repository (worktree) detected:"
                echo "    • Branch: $(git branch --show-current 2>/dev/null || echo 'detached')"
                echo "    • Status: $(git status --porcelain 2>/dev/null | wc -l) modified files"
                # Add .git_container and .git_main to local git exclusions
                echo ".git_main" >> .git/info/exclude 2>/dev/null || true
                echo ".git_container" >> .git/info/exclude 2>/dev/null || true
            else
                print_warning "Git status check failed - reinitializing as standalone repository"
                rm -f .git
                rm -rf .git_container
                git init
                git add .
                echo "  Git repository initialized (standalone)"
            fi
        else
            print_warning "Main git directory not mounted for worktree"
            print_info "Converting to standalone git repository"
            # Convert to a standalone repository to avoid errors
            rm -f .git
            git init
            git add .
            echo "  Git repository initialized (standalone)"
        fi
    # Check if it's a regular git repository
    elif [ -d ".git" ]; then
        echo "  Git repository detected:"
        echo "    • Branch: $(git branch --show-current 2>/dev/null || echo 'detached')"
        echo "    • Status: $(git status --porcelain 2>/dev/null | wc -l) modified files"
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

# Initialize git config if not set (do this after workspace setup)
# Use --global flag to avoid repository-specific errors
if ! git config --global user.email >/dev/null 2>&1; then
    print_info "Setting up Git global configuration..."
    git config --global user.email "sandbox@claude.local" 2>/dev/null || true
    git config --global user.name "Sandbox Claude" 2>/dev/null || true
    git config --global init.defaultBranch main 2>/dev/null || true
    git config --global safe.directory /workspace 2>/dev/null || true
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
# Claude command will use CLAUDE_CONFIG_DIR environment variable
alias claude='CLAUDE_CONFIG_DIR=$CLAUDE_CONFIG_DIR claude --dangerously-skip-permissions'
# Sync Claude configuration back to host
alias claude-sync='/usr/local/bin/sync-claude-config.sh'
alias sync-claude='/usr/local/bin/sync-claude-config.sh'
alias claude-save='/usr/local/bin/sync-claude-config.sh'
# Pull Claude configuration from host
alias claude-pull='/usr/local/bin/pull-claude-config.sh'
alias pull-claude='/usr/local/bin/pull-claude-config.sh'
alias claude-refresh='/usr/local/bin/pull-claude-config.sh'

# Function to show Claude config status
show_claude_config() {
    echo "[INFO] Claude configuration directory: $CLAUDE_CONFIG_DIR" >&2
    echo "[INFO] Config mode: $CONFIG_MODE" >&2
    if [ -f "$CLAUDE_CONFIG_DIR/.claude.json" ]; then
        echo "  • .claude.json exists" >&2
    fi
    if [ -f "$CLAUDE_CONFIG_DIR/.credentials.json" ]; then
        echo "  • .credentials.json exists" >&2
    fi
    if [ -f "$CLAUDE_CONFIG_DIR/CLAUDE.md" ]; then
        echo "  • CLAUDE.md exists" >&2
    fi
    if [ "$CONFIG_MODE" = "mounted" ]; then
        echo "[INFO] Configuration shared across containers (mounted volume)" >&2
    else
        echo "[INFO] Configuration stored in workspace (container-specific)" >&2
    fi
}

# Export function so it's available in subshells
export -f show_claude_config

# Also add an alias for checking config
alias claude-config-status='show_claude_config'

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
echo "────────────────────────────────────────────────────────────────"
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
echo "────────────────────────────────────────────────────────────────"
echo ""
print_success "Container ready! Type 'exit' to leave the sandbox."
echo "════════════════════════════════════════════════════════════════"
echo ""

# Execute the command passed to the container
exec "$@"
