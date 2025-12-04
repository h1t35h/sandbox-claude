#!/bin/bash
# Script to sync Claude configuration back to host-mounted directories
# This allows persisting updated credentials after login

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Main sync function
sync_claude_config() {
    echo "════════════════════════════════════════════════════════════════"
    echo "     🔄 Syncing Claude Configuration to Host"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    # Check if we're in a container
    if [ ! -f /.dockerenv ]; then
        print_error "This script should only be run inside a Docker container"
        return 1
    fi
    
    # Determine the source directory (where Claude saves configs)
    if [ -n "$CLAUDE_CONFIG_DIR" ]; then
        SOURCE_DIR="$CLAUDE_CONFIG_DIR"
    else
        print_error "CLAUDE_CONFIG_DIR is not set"
        return 1
    fi
    
    print_info "Source directory: $SOURCE_DIR"
    
    # Check for various possible destination directories
    SYNCED=false
    
    # 1. PRIMARY: Check for mounted shared host directory at /host-claude-config
    if [ -d "/host-claude-config" ] && [ -w "/host-claude-config" ]; then
        print_info "Found writable shared host directory: /host-claude-config"
        print_info "This will persist to host at: /tmp/csandbox/.claude/"
        
        # Sync all config files to the shared directory
        if [ -f "$SOURCE_DIR/.claude.json" ]; then
            cp "$SOURCE_DIR/.claude.json" "/host-claude-config/.claude.json"
            chmod 600 "/host-claude-config/.claude.json"
            print_success "Synced .claude.json to host"
        fi
        
        if [ -f "$SOURCE_DIR/.credentials.json" ]; then
            cp "$SOURCE_DIR/.credentials.json" "/host-claude-config/.credentials.json"
            chmod 600 "/host-claude-config/.credentials.json"
            print_success "Synced .credentials.json to host"
        fi
        
        if [ -f "$SOURCE_DIR/CLAUDE.md" ]; then
            cp "$SOURCE_DIR/CLAUDE.md" "/host-claude-config/CLAUDE.md"
            chmod 644 "/host-claude-config/CLAUDE.md"
            print_success "Synced CLAUDE.md to host"
        fi
        
        # Copy entire directory structure
        if [ -d "$SOURCE_DIR" ]; then
            for file in "$SOURCE_DIR"/*; do
                if [ -f "$file" ]; then
                    filename=$(basename "$file")
                    cp "$file" "/host-claude-config/$filename"
                    print_info "Copied $filename"
                fi
            done
        fi
        
        SYNCED=true
        print_success "All configs synced to host at /tmp/csandbox/.claude/"
    fi
    
    # 2. FALLBACK: Sync to workspace for manual copying
    if [ -d "/workspace" ]; then
        WORKSPACE_BACKUP="/workspace/.sandbox-claude"
        mkdir -p "$WORKSPACE_BACKUP"
        
        print_info "Creating workspace backup: $WORKSPACE_BACKUP"
        
        # Copy all config files
        if [ -f "$SOURCE_DIR/.claude.json" ]; then
            cp "$SOURCE_DIR/.claude.json" "$WORKSPACE_BACKUP/.claude.json"
            chmod 600 "$WORKSPACE_BACKUP/.claude.json"
            [ "$SYNCED" = false ] && print_success "Backed up .claude.json to workspace"
        fi
        
        if [ -f "$SOURCE_DIR/.credentials.json" ]; then
            cp "$SOURCE_DIR/.credentials.json" "$WORKSPACE_BACKUP/.credentials.json"
            chmod 600 "$WORKSPACE_BACKUP/.credentials.json"
            [ "$SYNCED" = false ] && print_success "Backed up .credentials.json to workspace"
        fi
        
        if [ -d "$SOURCE_DIR" ]; then
            # Copy entire claude config directory
            mkdir -p "$WORKSPACE_BACKUP/.claude"
            rsync -av --exclude='.git' "$SOURCE_DIR/" "$WORKSPACE_BACKUP/.claude/" 2>/dev/null || \
            cp -r "$SOURCE_DIR/." "$WORKSPACE_BACKUP/.claude/" 2>/dev/null || true
            [ "$SYNCED" = false ] && print_success "Backed up .claude directory contents to workspace"
        fi
        
        [ "$SYNCED" = false ] && SYNCED=true
    fi
    
    # 3. Create a host-sync script for manual copying (in /tmp to avoid cluttering workspace)
    HOST_SYNC_SCRIPT="/tmp/sync-to-host.sh"
    cat > "$HOST_SYNC_SCRIPT" << 'SCRIPT_EOF'
#!/bin/bash
# Run this script on the HOST (not in container) to sync Claude configs

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Syncing Claude configuration from workspace to host...${NC}"

# Source directory (in workspace)
SOURCE_DIR=".sandbox-claude"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: $SOURCE_DIR not found. Run 'claude-sync' in the container first."
    exit 1
fi

# Destination directory (host home)
DEST_DIR="$HOME/.claude"
mkdir -p "$DEST_DIR"

# Copy configuration files
if [ -f "$SOURCE_DIR/.claude.json" ]; then
    cp "$SOURCE_DIR/.claude.json" "$HOME/.claude.json"
    chmod 600 "$HOME/.claude.json"
    echo -e "${GREEN}✓ Copied .claude.json${NC}"
fi

if [ -f "$SOURCE_DIR/.credentials.json" ]; then
    cp "$SOURCE_DIR/.credentials.json" "$DEST_DIR/.credentials.json"
    chmod 600 "$DEST_DIR/.credentials.json"
    echo -e "${GREEN}✓ Copied .credentials.json${NC}"
fi

if [ -d "$SOURCE_DIR/.claude" ]; then
    cp -r "$SOURCE_DIR/.claude/." "$DEST_DIR/"
    echo -e "${GREEN}✓ Copied .claude directory contents${NC}"
fi

# Also copy from /tmp/csandbox if it exists (for getting synced configs)
if [ -d "/tmp/csandbox/.claude" ]; then
    echo -e "${YELLOW}Also syncing from /tmp/csandbox/.claude...${NC}"
    
    # Copy any newer files from shared directory
    if [ -f "/tmp/csandbox/.claude/.claude.json" ]; then
        cp "/tmp/csandbox/.claude/.claude.json" "$HOME/.claude.json"
        echo -e "${GREEN}✓ Updated .claude.json from shared directory${NC}"
    fi
    
    if [ -f "/tmp/csandbox/.claude/.credentials.json" ]; then
        cp "/tmp/csandbox/.claude/.credentials.json" "$DEST_DIR/.credentials.json"
        echo -e "${GREEN}✓ Updated .credentials.json from shared directory${NC}"
    fi
fi

echo -e "${GREEN}Configuration sync complete!${NC}"
SCRIPT_EOF
    chmod +x "$HOST_SYNC_SCRIPT"
    print_success "Created host sync script: $HOST_SYNC_SCRIPT"
    print_info "Run 'cat /tmp/sync-to-host.sh' to see manual sync instructions"
    
    if [ "$SYNCED" = true ]; then
        echo ""
        echo "────────────────────────────────────────────────────────────────"
        print_success "Configuration synced successfully!"
        echo ""
        echo "Synced files:"
        [ -f "$SOURCE_DIR/.claude.json" ] && echo "  ✓ .claude.json"
        [ -f "$SOURCE_DIR/.credentials.json" ] && echo "  ✓ .credentials.json"
        [ -f "$SOURCE_DIR/CLAUDE.md" ] && echo "  ✓ CLAUDE.md"
        echo ""
        if [ -d "/host-claude-config" ]; then
            echo "Configs are synced to host at: /tmp/csandbox/.claude/"
            echo "These will be automatically loaded in new containers."
        else
            echo "To sync to your host system:"
            echo "  1. Run 'cat /tmp/sync-to-host.sh' for manual sync instructions"
            echo "  2. From HOST: cp -r .sandbox-claude/. ~/.claude/"
        fi
        echo "════════════════════════════════════════════════════════════════"
    else
        print_warning "No writable destination found for sync"
        print_info "Configuration saved to workspace backup only"
    fi
}

# Run the sync function
sync_claude_config