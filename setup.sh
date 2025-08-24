#!/bin/bash
# Setup script for sandbox-claude

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "════════════════════════════════════════════════════════════════"
echo "     🚀 Sandbox Claude Setup"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Function to print colored output
print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_info "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
else
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    print_success "Python $(python3 --version | cut -d' ' -f2) found"
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
else
    print_success "Docker $(docker --version | cut -d' ' -f3 | tr -d ',') found"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker daemon is not running"
    echo "Please start Docker and try again"
    exit 1
else
    print_success "Docker daemon is running"
fi

echo ""
print_info "Installing sandbox-claude..."

# Create virtual environment (optional)
if [ "$1" == "--venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    print_success "Virtual environment created and activated"
fi

# Install package
print_info "Installing Python package..."
pip install -e . > /dev/null 2>&1
print_success "Package installed"

# Build Docker image
print_info "Building Docker base image (this may take a few minutes)..."
echo "You can monitor progress with: docker build -t sandbox-claude-base:latest -f docker/Dockerfile docker/"

if make docker-build; then
    print_success "Docker image built successfully"
else
    print_error "Failed to build Docker image"
    echo "You can try building manually with: make docker-build"
fi

# Create configuration directory
print_info "Setting up configuration..."
mkdir -p ~/.sandbox_claude
print_success "Configuration directory created"

# Check for Claude configuration
if [ -f ~/.claude.json ] || [ -d ~/.claude ]; then
    print_success "Claude configuration found"
else
    print_info "No Claude configuration found"
    echo "  You may want to create ~/.claude.json with your API credentials"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
print_success "Setup complete!"
echo ""
echo "Quick start:"
echo "  sandbox-claude new -p myproject -f myfeature"
echo ""
echo "For more information:"
echo "  sandbox-claude --help"
echo "  cat README.md"
echo "════════════════════════════════════════════════════════════════"