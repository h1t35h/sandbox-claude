# Sandbox Claude 🚀

A powerful CLI tool for managing sandboxed Claude Code development environments in Docker containers. Create isolated, reproducible development environments with Claude Code pre-configured and ready to use.

## Features

- 🐳 **Docker-based Isolation**: Each sandbox runs in its own Docker container
- 🚀 **Fast Startup**: Pre-built images enable 2-3 second container creation
- 📁 **Project Organization**: Containers named by project and feature for easy management
- 💾 **Session Persistence**: SQLite database tracks all your sandbox sessions
- 🔧 **Smart Configuration**: Bi-directional config sync between host and containers
- 🔒 **Secure**: Read-only config mounts, isolated environments, cryptographically secure naming
- 📊 **Session Management**: List, stop, clean, and manage multiple sandboxes
- 🎯 **Smart Selection**: Find containers by project, feature, or use the latest
- ⚡ **Type-Safe**: Full type annotations with strict mypy checking for reliability
- 🧹 **High Code Quality**: Formatted with Black, linted with Ruff, 100% type coverage
- 📝 **Comprehensive Logging**: Full observability with structured logging
- 🎨 **Global Gitignore**: Container-specific files automatically excluded from git
- 🎭 **Playwright Integration**: Browser automation with Chromium, Firefox, and WebKit pre-installed
- 🤖 **MCP Server**: Model Context Protocol server for Claude-powered browser automation

## Prerequisites

- Docker installed and running
- Python 3.9 or higher (3.12+ recommended)
- Unix-like operating system (Linux, macOS, WSL2)
- Git (for version control features)

## Installation

### Quick Install

```bash
# Clone the repository
git clone https://github.com/yourusername/sandbox_claude.git
cd sandbox_claude

# Run the complete development setup
make dev-setup
```

This will:
1. Upgrade pip, setuptools, and wheel
2. Install the package with all dependencies
3. Build the Docker base image
4. Verify everything is ready

### Manual Installation

```bash
# Install the package with development dependencies
pip install -e ".[dev]"

# Build the Docker base image
make docker-build

# Verify installation
sandbox-claude --help
```

## Quick Start

### Create Your First Sandbox

```bash
# Create a new sandbox for your project
sandbox-claude new -p myproject -f authentication

# This will:
# 1. Check/pull the pre-built Docker image
# 2. Create a new Docker container with secure naming
# 3. Mount your current directory to /workspace
# 4. Mount your Claude configuration (with smart sync)
# 5. Drop you into an interactive shell with all tools ready
```

### Basic Commands

```bash
# List all sandboxes
sandbox-claude list

# List sandboxes for a specific project
sandbox-claude list -p myproject

# List only running containers
sandbox-claude list --active

# SSH into a specific sandbox
sandbox-claude ssh -p myproject -f authentication

# SSH into the most recent sandbox
sandbox-claude ssh --latest

# Stop sandboxes
sandbox-claude stop -p myproject  # Stop all for project
sandbox-claude stop --all          # Stop all sandboxes

# Clean up stopped containers
sandbox-claude clean -p myproject --force
sandbox-claude clean --all --force
```

## What's Included in Each Sandbox

Each sandbox container comes pre-configured with:

### Development Tools
- **Python 3.12** with pip, ipython, jupyter
- **Node.js 20** with npm, yarn, pnpm
- **Git** with global gitignore pre-configured
- **GitHub CLI (gh)** for PR/issue management
- **Claude Code CLI** pre-installed and configured
- **Playwright** for browser automation (Chromium, Firefox, WebKit)
- **MCP Server** for Claude-powered browser automation
- **Code Quality**: black, ruff, mypy, prettier, eslint
- **Testing**: pytest, pytest-playwright, jest
- **Editors**: vim, nano
- **Shell**: bash, zsh, tmux

### Python Packages
- Web: flask, fastapi, uvicorn
- Data: numpy, pandas, requests
- Testing: pytest, pytest-cov, pytest-mock
- Formatting: black, ruff
- Type checking: mypy
- CLI: click, rich, pyyaml

### Node Packages
- TypeScript, ts-node, nodemon
- Linting: eslint, prettier
- Testing: jest

### Environment
- Working directory: `/workspace` (your mounted project)
- User: `sandman` (UID/GID 1000)
- Global gitignore: `/etc/gitignore` (excludes `.sandbox_history`, `.claude-config/`)
- Cache directories for pip and npm
- Locale: en_US.UTF-8

## Advanced Usage

### Container Naming Convention

Containers are named using the pattern:
```
sandbox-claude-{project}-{feature}-{timestamp}-{hex-id}
```

Example: `sandbox-claude-ecommerce-payment-20240824-143022-a3f2`

The hex-id is cryptographically secure (using `secrets.token_hex()`), ensuring unique container names.

### Reusing Containers

```bash
# Reuse an existing container if available
sandbox-claude new -p myproject -f feature --reuse

# Run in detached mode (background)
sandbox-claude new -p myproject -f feature --detach

# Use a custom Docker image
sandbox-claude new -p myproject -f feature --image my-custom:latest
```

### Execute Commands in Containers

```bash
# Run a command in a sandbox
sandbox-claude exec <container-id> python script.py
sandbox-claude exec <container-id> npm install
sandbox-claude exec <container-id> pytest tests/
```

### Configuration Management

#### Claude Configuration Sync

The tool provides bi-directional configuration sync:

**Inside Container - Push to Host (Save Updated Credentials):**
```bash
# After logging in or updating credentials
claude login  # Follow the prompts to authenticate

# Then sync the updated credentials back to host:
claude-sync   # Aliases: claude-save, sync-claude

# Or login and auto-sync in one command:
claude-login  # Automatically syncs after successful login
```

**Inside Container - Pull from Host (Refresh Credentials):**
```bash
# To refresh with latest host configs:
claude-pull   # Aliases: claude-refresh, pull-claude

# Check config status:
claude-config-status
```

**How Configuration Sync Works:**
1. **Push (claude-sync)**: Saves to `/tmp/csandbox/.claude/` on host
2. **Pull (claude-pull)**: Loads from host into current container
3. **Auto-load**: New containers automatically load from shared directory
4. **Workspace backup**: Always maintains backup in `/workspace/.claude-config/`

**Configuration Files Handled:**
- `~/.claude.json` → Container's `~/.claude.json`
- `~/.claude/.credentials.json` → Container's `~/.claude/.credentials.json`
- `~/.claude/CLAUDE.md` → Container's `~/.claude/CLAUDE.md`

**To skip mounting configuration:**
```bash
sandbox-claude new -p project -f feature --no-mount-config
```

#### Project Configuration

Create a `.sandbox-claude.yml` in your project root:

```yaml
project: myapp
defaults:
  image: sandbox-claude-base:latest
  environment:
    - NODE_ENV=development
    - DEBUG=true
```

## Playwright & MCP Integration

### Browser Automation with Playwright

Each sandbox comes with Playwright pre-installed and configured with three browsers:
- **Chromium** - Latest stable version
- **Firefox** - Latest stable version
- **WebKit** - Latest stable version

#### Running Playwright Scripts

**Python Example:**
```bash
# Inside the container
cd /workspace
python3 examples/playwright_example.py
```

**Node.js Example:**
```bash
# Inside the container
cd /workspace
node examples/playwright_example.js
```

#### Manual Playwright Usage

**Python:**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://example.com")
    page.screenshot(path="screenshot.png")
    browser.close()
```

**Node.js:**
```javascript
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('https://example.com');
  await page.screenshot({ path: 'screenshot.png' });
  await browser.close();
})();
```

### MCP Server for Claude

The sandbox includes a **Model Context Protocol (MCP)** server that enables Claude to control browser automation directly through tool calls.

#### Available MCP Tools

When using Claude inside the container, the following browser automation tools are available:

- **navigate** - Navigate to a URL
- **screenshot** - Take screenshots (full page or viewport)
- **click** - Click elements by CSS selector
- **fill** - Fill form inputs
- **get_text** - Extract text from elements
- **get_html** - Get HTML content
- **wait_for_selector** - Wait for elements to appear
- **evaluate** - Execute JavaScript in page context

#### Using MCP with Claude

Simply ask Claude to perform browser automation tasks:

```
User: "Navigate to example.com and take a screenshot"
User: "Go to hacker news and get the top 5 story titles"
User: "Fill out the login form with username 'testuser'"
```

Claude will automatically use the MCP server to perform these actions.

#### MCP Configuration

The MCP server is automatically configured on container startup:
- **Server Script**: `/mcp-servers/mcp-playwright-server.py`
- **Configuration**: `$CLAUDE_CONFIG_DIR/mcp-config.json`
- **Documentation**: `/workspace/examples/MCP_USAGE.md`

#### Testing Playwright Installation

```bash
# Check Playwright is installed
make test-playwright

# Or manually
python3 -c "import playwright; print('Playwright ready!')"
npx playwright --version
```

#### Example Use Cases

1. **Web Scraping**: Extract data from websites
2. **Visual Testing**: Take screenshots for visual regression testing
3. **Form Automation**: Fill and submit forms programmatically
4. **Integration Testing**: Test web applications end-to-end
5. **Data Collection**: Automate data gathering from multiple sources

#### Environment Variables

- `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` - Browser installation path
- `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0` - Browser downloads enabled

For detailed MCP usage instructions, see `/workspace/examples/MCP_USAGE.md`

## Docker Image

### Pre-built Base Image

The base image (`sandbox-claude-base:latest`) includes:
- **Python 3.12** with common packages
- **Node.js 20** with npm and common packages
- **Playwright** with Chromium, Firefox, and WebKit browsers
- **MCP Server** for browser automation through Claude
- **Git** with global configuration
- **GitHub CLI (gh)**
- **Claude Code CLI**
- **Development tools** (vim, nano, tmux, zsh)
- **Global gitignore** at `/etc/gitignore`
- **Optimized layers** for fast rebuilds

### Building the Image

```bash
# Build the base image
make docker-build

# Clean and rebuild
make docker-clean
make docker-build

# Or manually
docker build -t sandbox-claude-base:latest -f docker/Dockerfile docker/
```

## Session Management

### Database Location

Sessions are stored in `~/.sandbox_claude/sessions.db` (SQLite)

### View Statistics

```bash
# Show comprehensive statistics
make stats

# List all containers
make list-containers

# Or use the CLI directly
sandbox-claude list --all
```

### Database Operations

```bash
# Reset the session database
make db-reset

# Or manually
rm ~/.sandbox_claude/sessions.db
```

### Export/Import Sessions

```python
from pathlib import Path
from sandbox_claude import SessionStore

store = SessionStore()

# Export sessions to JSON
store.export_sessions(Path("sessions-backup.json"))

# Import sessions from JSON
imported_count = store.import_sessions(Path("sessions-backup.json"))
```

## Make Commands Reference

### Development & Setup
```bash
make help           # Show all available commands with descriptions
make install        # Install package in development mode
make dev-setup      # Complete development setup (recommended)
make build          # Build the Python package distribution
```

### Testing & Quality
```bash
make test           # Run full test suite with coverage
make test-unit      # Run unit tests only
make test-integration # Run integration tests only
make lint           # Run Ruff linter and mypy type checker
make format         # Format code with Black and auto-fix Ruff issues
```

### Docker Management
```bash
make docker-build   # Build the Docker base image
make docker-push    # Push Docker image to registry
make docker-clean   # Remove the Docker image
make check-docker   # Check Docker installation and daemon status
```

### Cleanup
```bash
make clean          # Clean build artifacts, __pycache__, dist folders
make db-reset       # Reset the session database
```

### Container Operations
```bash
make stats          # Show sandbox statistics (DB + Docker)
make list-containers # List all sandbox containers
make stop-all       # Stop all sandbox containers
make remove-all     # Remove all sandbox containers (force)
```

### Running & Release
```bash
make run-example    # Run an example sandbox session
make release        # Create a release build and check with twine
```

### Playwright
```bash
make test-playwright    # Test Playwright installation
make install-playwright # Install Playwright dependencies (if needed)
```

## Development

### Project Structure

```
sandbox_claude/
├── src/sandbox_claude/
│   ├── __init__.py           # Package exports
│   ├── cli.py                # Click-based CLI interface
│   ├── container_manager.py  # Docker operations with proper logging
│   ├── session_store.py      # SQLite persistence with indexes
│   ├── config_sync.py        # Bi-directional config management
│   ├── constants.py          # Centralized constants
│   ├── utils.py              # Utility functions
│   └── logging_config.py     # Logging configuration
├── docker/
│   ├── Dockerfile                 # Optimized multi-stage build with Playwright
│   ├── entrypoint.sh              # Container startup script with MCP setup
│   ├── sync-claude-config.sh      # Config push script
│   ├── pull-claude-config.sh      # Config pull script
│   ├── mcp-playwright-server.py   # MCP server for browser automation
│   └── mcp-config.json            # MCP server configuration
├── examples/
│   ├── playwright_example.py      # Python Playwright example
│   ├── playwright_example.js      # Node.js Playwright example
│   └── MCP_USAGE.md               # MCP server usage guide
├── tests/
│   ├── test_utils.py         # Utils tests
│   ├── test_config_sync.py   # Config sync tests
│   └── test_session_store.py # Database tests
├── Makefile                  # Build automation with Playwright commands
├── pyproject.toml           # Modern Python packaging with Playwright deps
├── setup.sh                  # Automated setup script
└── README.md                 # This file
```

### Code Quality Standards

This project maintains **the highest Python quality standards**:

- ✅ **Black** formatting (100-char line length)
- ✅ **Ruff** linting (E, F, W, C90, I, N, UP, B, SIM rules)
- ✅ **Mypy** strict type checking (100% coverage)
- ✅ **Pytest** with coverage reporting
- ✅ **Consistent error handling** (specific exception types)
- ✅ **Comprehensive logging** (all operations logged)
- ✅ **Centralized constants** (no magic numbers/strings)

### Running Tests

```bash
# Run all tests with coverage
make test

# Run specific test categories
make test-unit
make test-integration

# Run with verbose output
pytest tests/ -v -s
```

### Code Quality Checks

```bash
# Format code
make format

# Run linting
make lint

# Run type checking
python -m mypy src/

# Run all quality checks
make format lint test
```

### Recent Code Quality Improvements

**Version 1.0.0 includes major maintainability improvements:**

1. **Constants Module** (`constants.py`):
   - 41 constants extracted from magic numbers/strings
   - Application metadata, Docker config, paths, timeouts
   - Name validation patterns, time/size constants

2. **Enhanced Error Handling**:
   - Specific exception types instead of broad catches
   - Proper error messages with context
   - Fixed SQL type conversion bug

3. **Comprehensive Logging**:
   - Added logging to all modules
   - Debug, info, warning, error levels
   - File logging to `~/.sandbox_claude/logs/`

4. **Improved Code Organization**:
   - All imports at module top
   - No late imports in functions
   - Removed circular dependencies

5. **Global Gitignore**:
   - `/etc/gitignore` configured in containers
   - Automatically excludes `.sandbox_history`, `.claude-config/`

## Performance

### Startup Times

- **First run**: ~30 seconds (building base image)
- **Subsequent runs**: 2-3 seconds (using cached image)
- **With --reuse flag**: <1 second (attach to existing container)

### Optimization Tips

1. **Use --reuse**: Reuse existing containers when possible
2. **Pre-build images**: Run `make docker-build` during setup
3. **Cache volumes**: Pip and npm caches are persisted
4. **Cleanup regularly**: Use `make clean` and `sandbox-claude clean --all`

## Security Considerations

- ✅ Claude configuration mounted read-only from host
- ✅ Containers run as non-root user (`sandman`, UID 1000)
- ✅ Container names use cryptographically secure random IDs (`secrets.token_hex()`)
- ✅ SQL queries use parameterized statements (prevent injection)
- ✅ Sensitive files validated for proper permissions (600/700)
- ✅ Type-safe code prevents many runtime errors
- ✅ Strict mypy checking catches type-related bugs

## Troubleshooting

### Docker Connection Issues

```bash
# Check Docker status
make check-docker

# Verify Docker is running
docker info

# Check if Docker daemon is running
docker ps
```

### Container Won't Start

```bash
# Check container logs
docker logs <container-id>

# Rebuild base image
make docker-clean
make docker-build

# Check for port conflicts
docker ps -a
```

### Configuration Issues

```bash
# Check Claude config exists
ls -la ~/.claude*

# Pull latest config into container
# (inside container)
claude-pull

# Push config from container to host
# (inside container)
claude-sync
```

### Database Issues

```bash
# Reset the session database
make db-reset

# View database contents
sqlite3 ~/.sandbox_claude/sessions.db "SELECT * FROM sandboxes;"

# Check database statistics
make stats
```

### Build Failures

```bash
# Clean everything and start fresh
make clean
make docker-clean
make dev-setup

# Check Python version
python --version  # Should be 3.9+

# Check Docker version
docker --version
```

## Logging

Logs are stored in `~/.sandbox_claude/logs/sandbox-claude.log`

```bash
# View logs
tail -f ~/.sandbox_claude/logs/sandbox-claude.log

# View recent errors
grep ERROR ~/.sandbox_claude/logs/sandbox-claude.log

# View container-specific logs
docker logs <container-id>
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow code quality standards:
   - Run `make format` before committing
   - Ensure `make lint` passes
   - Add tests for new functionality
   - Maintain 80%+ test coverage
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Development Workflow

```bash
# Setup development environment
make dev-setup

# Make your changes
# ... edit code ...

# Format and lint
make format
make lint

# Run tests
make test

# Commit if all checks pass
git add .
git commit -m "Your message"
```

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built for the Claude Code ecosystem
- Inspired by development environment managers like devcontainers
- Thanks to the Docker and Python communities
- Uses industry-standard tools: Black, Ruff, Mypy, Pytest

## Support

For issues and questions:
- 🐛 [Open an issue on GitHub](https://github.com/yourusername/sandbox_claude/issues)
- 📖 Check the [Troubleshooting](#troubleshooting) section
- 💬 Review existing issues for solutions

---

**Built with ❤️ for developers who love clean, isolated environments**

Happy coding in your sandboxed environments! 🎉
