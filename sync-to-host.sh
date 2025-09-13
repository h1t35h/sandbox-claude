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
