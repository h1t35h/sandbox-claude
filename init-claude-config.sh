#!/bin/bash
# Initialize Claude configuration directory for sandbox containers
# This script sets up /tmp/csandbox/.claude for use with Docker containers
# Containers run as 'sandman' user for enhanced security

set -e

# Configuration
CSANDBOX_DIR="/tmp/csandbox"
CLAUDE_CONFIG_DIR="$CSANDBOX_DIR/.claude"
HOST_CLAUDE_DIR="$HOME/.claude"
HOST_CLAUDE_JSON="$HOME/.claude.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "════════════════════════════════════════════════════════════════"
echo "     🚀 Initializing Claude Config for Sandbox Containers"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Create the csandbox directory if it doesn't exist
if [ ! -d "$CSANDBOX_DIR" ]; then
    echo -e "${YELLOW}Creating $CSANDBOX_DIR directory...${NC}"
    mkdir -p "$CSANDBOX_DIR"
    echo -e "${GREEN}✓ Created $CSANDBOX_DIR${NC}"
fi

# Create the Claude config directory
if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
    echo -e "${YELLOW}Creating $CLAUDE_CONFIG_DIR directory...${NC}"
    mkdir -p "$CLAUDE_CONFIG_DIR"
    chmod 700 "$CLAUDE_CONFIG_DIR"
    echo -e "${GREEN}✓ Created $CLAUDE_CONFIG_DIR${NC}"
else
    echo -e "${GREEN}✓ $CLAUDE_CONFIG_DIR already exists${NC}"
fi

# Copy existing Claude configuration from host if available
COPIED_FILES=0

# Copy .claude.json if it exists
if [ -f "$HOST_CLAUDE_JSON" ] && [ ! -f "$CLAUDE_CONFIG_DIR/.claude.json" ]; then
    echo -e "${YELLOW}Copying .claude.json from host...${NC}"
    cp "$HOST_CLAUDE_JSON" "$CLAUDE_CONFIG_DIR/.claude.json"
    chmod 600 "$CLAUDE_CONFIG_DIR/.claude.json"
    echo -e "${GREEN}✓ Copied .claude.json${NC}"
    COPIED_FILES=$((COPIED_FILES + 1))
elif [ -f "$CLAUDE_CONFIG_DIR/.claude.json" ]; then
    echo -e "${GREEN}✓ .claude.json already exists in $CLAUDE_CONFIG_DIR${NC}"
fi

# Copy .credentials.json if it exists
if [ -f "$HOST_CLAUDE_DIR/.credentials.json" ] && [ ! -f "$CLAUDE_CONFIG_DIR/.credentials.json" ]; then
    echo -e "${YELLOW}Copying .credentials.json from host...${NC}"
    cp "$HOST_CLAUDE_DIR/.credentials.json" "$CLAUDE_CONFIG_DIR/.credentials.json"
    chmod 600 "$CLAUDE_CONFIG_DIR/.credentials.json"
    echo -e "${GREEN}✓ Copied .credentials.json${NC}"
    COPIED_FILES=$((COPIED_FILES + 1))
elif [ -f "$CLAUDE_CONFIG_DIR/.credentials.json" ]; then
    echo -e "${GREEN}✓ .credentials.json already exists in $CLAUDE_CONFIG_DIR${NC}"
fi

# Copy CLAUDE.md if it exists
if [ -f "$HOST_CLAUDE_DIR/CLAUDE.md" ] && [ ! -f "$CLAUDE_CONFIG_DIR/CLAUDE.md" ]; then
    echo -e "${YELLOW}Copying CLAUDE.md from host...${NC}"
    cp "$HOST_CLAUDE_DIR/CLAUDE.md" "$CLAUDE_CONFIG_DIR/CLAUDE.md"
    chmod 644 "$CLAUDE_CONFIG_DIR/CLAUDE.md"
    echo -e "${GREEN}✓ Copied CLAUDE.md${NC}"
    COPIED_FILES=$((COPIED_FILES + 1))
elif [ -f "$CLAUDE_CONFIG_DIR/CLAUDE.md" ]; then
    echo -e "${GREEN}✓ CLAUDE.md already exists in $CLAUDE_CONFIG_DIR${NC}"
fi

echo ""
echo "────────────────────────────────────────────────────────────────"
echo "Configuration Summary:"
echo "  • Config directory: $CLAUDE_CONFIG_DIR"
echo "  • Files copied from host: $COPIED_FILES"

# List files in the config directory
if [ "$(ls -A $CLAUDE_CONFIG_DIR 2>/dev/null)" ]; then
    echo "  • Available configuration files:"
    ls -la "$CLAUDE_CONFIG_DIR" | grep -E "^-" | awk '{print "    - " $9 " (" $5 " bytes)"}'
else
    echo -e "  ${YELLOW}• No configuration files found${NC}"
    echo -e "  ${YELLOW}  Claude will create them on first run${NC}"
fi

echo ""
echo -e "${GREEN}✓ Claude configuration directory is ready!${NC}"
echo ""
echo "To use with Docker:"
echo "  docker run -u sandman -v $CLAUDE_CONFIG_DIR:/claude-config ..."
echo ""
echo "Or with docker-compose:"
echo "  volumes:"
echo "    - $CLAUDE_CONFIG_DIR:/claude-config"
echo "  user: sandman  # Non-root user for security"
echo ""
echo "════════════════════════════════════════════════════════════════"