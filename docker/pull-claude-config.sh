#!/bin/bash
# Script to pull Claude configuration from host into the container
# This allows refreshing credentials from host without restarting container

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

# Main pull function
pull_claude_config() {
    echo "════════════════════════════════════════════════════════════════"
    echo "     ⬇️  Pulling Claude Configuration from Host"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    # Check if we're in a container
    if [ ! -f /.dockerenv ]; then
        print_error "This script should only be run inside a Docker container"
        return 1
    fi
    
    # Determine the destination directory (where Claude reads configs)
    if [ -n "$CLAUDE_CONFIG_DIR" ]; then
        DEST_DIR="$CLAUDE_CONFIG_DIR"
    else
        print_error "CLAUDE_CONFIG_DIR is not set"
        return 1
    fi
    
    print_info "Destination directory: $DEST_DIR"
    
    # Track what was pulled
    PULLED=false
    PULLED_FILES=""
    
    # Priority 1: Check shared host directory (most recent synced configs)
    if [ -d "/host-claude-config" ] && [ -r "/host-claude-config" ]; then
        print_info "Checking shared host directory for configs..."
        
        if [ -f "/host-claude-config/.claude.json" ]; then
            cp "/host-claude-config/.claude.json" "$DEST_DIR/.claude.json"
            chmod 600 "$DEST_DIR/.claude.json"
            print_success "Pulled .claude.json from shared host directory"
            PULLED=true
            PULLED_FILES="$PULLED_FILES .claude.json"
        fi
        
        if [ -f "/host-claude-config/.credentials.json" ]; then
            cp "/host-claude-config/.credentials.json" "$DEST_DIR/.credentials.json"
            chmod 600 "$DEST_DIR/.credentials.json"
            print_success "Pulled .credentials.json from shared host directory"
            PULLED=true
            PULLED_FILES="$PULLED_FILES .credentials.json"
        fi
        
        if [ -f "/host-claude-config/CLAUDE.md" ]; then
            cp "/host-claude-config/CLAUDE.md" "$DEST_DIR/CLAUDE.md"
            chmod 644 "$DEST_DIR/CLAUDE.md"
            print_success "Pulled CLAUDE.md from shared host directory"
            PULLED=true
            PULLED_FILES="$PULLED_FILES CLAUDE.md"
        fi
        
        # Copy any other config files
        for file in /host-claude-config/*; do
            if [ -f "$file" ]; then
                filename=$(basename "$file")
                if [[ "$filename" != ".claude.json" && "$filename" != ".credentials.json" && "$filename" != "CLAUDE.md" ]]; then
                    cp "$file" "$DEST_DIR/$filename"
                    print_info "Pulled $filename"
                    PULLED=true
                    PULLED_FILES="$PULLED_FILES $filename"
                fi
            fi
        done
    fi
    
    # Priority 2: Check original host mount points (read-only mounts)
    if [ "$PULLED" = false ]; then
        print_info "Checking original host mount points..."
        
        if [ -f "/tmp/.claude.json.host" ]; then
            cp "/tmp/.claude.json.host" "$DEST_DIR/.claude.json"
            chmod 600 "$DEST_DIR/.claude.json"
            print_success "Pulled .claude.json from host mount"
            PULLED=true
            PULLED_FILES="$PULLED_FILES .claude.json"
        fi
        
        if [ -d "/tmp/.claude.host" ]; then
            # Copy .credentials.json if it exists
            if [ -f "/tmp/.claude.host/.credentials.json" ]; then
                cp "/tmp/.claude.host/.credentials.json" "$DEST_DIR/.credentials.json"
                chmod 600 "$DEST_DIR/.credentials.json"
                print_success "Pulled .credentials.json from host mount"
                PULLED=true
                PULLED_FILES="$PULLED_FILES .credentials.json"
            fi
            
            # Copy CLAUDE.md if it exists
            if [ -f "/tmp/.claude.host/CLAUDE.md" ]; then
                cp "/tmp/.claude.host/CLAUDE.md" "$DEST_DIR/CLAUDE.md"
                chmod 644 "$DEST_DIR/CLAUDE.md"
                print_success "Pulled CLAUDE.md from host mount"
                PULLED=true
                PULLED_FILES="$PULLED_FILES CLAUDE.md"
            fi
        fi
        
        if [ -f "/tmp/.claude_creds.json.host" ]; then
            cp "/tmp/.claude_creds.json.host" "$DEST_DIR/.credentials.json"
            chmod 600 "$DEST_DIR/.credentials.json"
            print_success "Pulled credentials from host mount"
            PULLED=true
            PULLED_FILES="$PULLED_FILES .credentials.json"
        fi
    fi
    
    # Priority 3: Check workspace backup
    if [ "$PULLED" = false ] && [ -d "/workspace/.sandbox-claude" ]; then
        print_info "Checking workspace backup..."
        
        if [ -f "/workspace/.sandbox-claude/.claude.json" ]; then
            cp "/workspace/.sandbox-claude/.claude.json" "$DEST_DIR/.claude.json"
            chmod 600 "$DEST_DIR/.claude.json"
            print_success "Pulled .claude.json from workspace backup"
            PULLED=true
            PULLED_FILES="$PULLED_FILES .claude.json"
        fi
        
        if [ -f "/workspace/.sandbox-claude/.credentials.json" ]; then
            cp "/workspace/.sandbox-claude/.credentials.json" "$DEST_DIR/.credentials.json"
            chmod 600 "$DEST_DIR/.credentials.json"
            print_success "Pulled .credentials.json from workspace backup"
            PULLED=true
            PULLED_FILES="$PULLED_FILES .credentials.json"
        fi
        
        if [ -d "/workspace/.sandbox-claude/.claude" ]; then
            cp -r "/workspace/.sandbox-claude/.claude/." "$DEST_DIR/" 2>/dev/null || true
            print_success "Pulled .claude directory from workspace backup"
            PULLED=true
        fi
    fi
    
    echo ""
    echo "────────────────────────────────────────────────────────────────"
    
    if [ "$PULLED" = true ]; then
        print_success "Configuration pulled successfully!"
        echo ""
        echo "Pulled files:$PULLED_FILES"
        echo ""
        print_info "Claude configuration has been refreshed"
        print_info "You may need to restart Claude or re-login if issues persist"
    else
        print_warning "No configuration files found to pull"
        print_info "Make sure configs exist in one of:"
        echo "  1. /tmp/csandbox/.claude/ (shared host directory)"
        echo "  2. Original host mount points"
        echo "  3. Workspace backup directory"
    fi
    
    echo "════════════════════════════════════════════════════════════════"
}

# Run the pull function
pull_claude_config