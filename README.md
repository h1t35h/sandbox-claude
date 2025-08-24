# Sandbox Claude 🚀

A powerful CLI tool for managing sandboxed Claude Code development environments in Docker containers. Create isolated, reproducible development environments with Claude Code pre-configured and ready to use.

## Features

- 🐳 **Docker-based Isolation**: Each sandbox runs in its own Docker container
- 🚀 **Fast Startup**: Pre-built images enable 2-3 second container creation
- 📁 **Project Organization**: Containers named by project and feature for easy management
- 💾 **Session Persistence**: SQLite database tracks all your sandbox sessions
- 🔧 **Smart Configuration**: Copy-on-write for `.claude.json` - editable in container, host file protected
- 🔒 **Secure**: Read-only config mounts, isolated environments, cryptographically secure naming
- 📊 **Session Management**: List, stop, clean, and manage multiple sandboxes
- 🎯 **Smart Selection**: Find containers by project, feature, or use the latest
- ⚡ **Type-Safe**: Full type annotations for better IDE support and reliability

## Prerequisites

- Docker installed and running
- Python 3.9 or higher (3.11+ recommended for best type hint support)
- Unix-like operating system (Linux, macOS, WSL2)
- Git (for version control features)

## Installation

### Quick Install

```bash
# Clone the repository
git clone https://github.com/yourusername/sandbox_claude.git
cd sandbox_claude

# Run the setup script
chmod +x setup.sh
./setup.sh

# Or use make
make dev-setup
```

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
# 4. Mount your Claude configuration (read-only)
# 5. Drop you into an interactive shell with all tools ready
```

### Basic Commands

```bash
# List all sandboxes
sandbox-claude list

# List sandboxes for a specific project
sandbox-claude list -p myproject

# SSH into a specific sandbox
sandbox-claude ssh -p myproject -f authentication

# SSH into the most recent sandbox
sandbox-claude ssh --latest

# Stop sandboxes
sandbox-claude stop -p myproject  # Stop all for project
sandbox-claude stop --all          # Stop all sandboxes

# Clean up stopped containers
sandbox-claude clean -p myproject
sandbox-claude clean --all
```

## What's Included in Each Sandbox

Each sandbox container comes pre-configured with:

### Development Tools
- **Python 3.12** with pip, ipython, jupyter
- **Node.js 20** with npm, yarn, pnpm
- **Git** with sensible defaults
- **GitHub CLI** for PR/issue management
- **Code Quality**: black, ruff, mypy, prettier, eslint
- **Testing**: pytest, jest
- **Editors**: vim, nano
- **Shell**: bash, zsh, tmux

### Python Packages
- Web: flask, fastapi, uvicorn
- Data: numpy, pandas, requests
- Testing: pytest, pytest-cov
- Formatting: black, ruff
- Type checking: mypy
- CLI: click, rich

### Node Packages
- TypeScript, ts-node
- Build tools: nodemon
- Linting: eslint, prettier
- Testing: jest

### Environment
- Working directory: `/workspace` (your mounted project)
- Home directory: `/root` with Claude configs
- Cache directories for pip and npm
- Locale: en_US.UTF-8

## Advanced Usage

### Container Naming Convention

Containers are named using the pattern:
```
sandbox-claude-{project}-{feature}-{timestamp}-{hex-id}
```

Example: `sandbox-claude-ecommerce-payment-20240824-143022-a3f2`

The hex-id is cryptographically secure, ensuring unique container names.

### Reusing Containers

```bash
# Reuse an existing container if available
sandbox-claude new -p myproject -f feature --reuse

# Run in detached mode (background)
sandbox-claude new -p myproject -f feature --detach
```

### Execute Commands

```bash
# Run a command in a sandbox
sandbox-claude exec <container-id> python script.py
sandbox-claude exec <container-id> npm install
```

### Configuration

#### Project Configuration

Create a `.sandbox-claude.yml` in your project root:

```yaml
project: myapp
defaults:
  image: sandbox-claude-base:latest
  environment:
    - NODE_ENV=development
    - DEBUG=true
  volumes:
    - ./data:/data
  features:
    auth:
      ports: [3000, 5432]
    payment:
      ports: [3000, 8080]
```

#### Claude Configuration

The tool intelligently handles Claude configuration:
- **Automatic Copy**: Your `~/.claude.json` is copied into the container (not mounted directly)
- **Editable**: Claude can modify the configuration inside the container
- **Host Protection**: Original host file remains untouched
- **Session Persistence**: Changes are saved to `/workspace/.sandbox-claude/` for next session
- **Secure**: Configuration file has 600 permissions (owner read/write only)

Configuration behavior:
1. On container start: Copies host's `.claude.json` to container
2. During session: Claude can modify the configuration as needed
3. Between sessions: Configuration persists in workspace directory
4. Manual save: Run `save-claude-config` command in container

The `.claude/` directory is still mounted read-only for other configuration files.

To skip mounting configuration:
```bash
sandbox-claude new -p project -f feature --no-mount-config
```

## Docker Image

### Pre-built Base Image

The base image includes:
- **Python 3.12** with common packages (numpy, pandas, pytest, black, ruff, mypy, etc.)
- **Node.js 20** with npm and common packages (typescript, prettier, eslint, etc.)
- **Git** for version control
- **GitHub CLI (gh)** for repository management
- **Claude Code** (when available via npm)
- **Development tools** (vim, nano, tmux, zsh, etc.)
- **Optimized layers** for fast rebuilds and minimal size

### Building Custom Image

```bash
# Build the base image
make docker-build

# Or manually
docker build -t sandbox-claude-base:latest -f docker/Dockerfile docker/
```

### Using Custom Image

```bash
sandbox-claude new -p project -f feature --image my-custom-image:latest
```

## Session Management

### Database Location

Sessions are stored in `~/.sandbox_claude/sessions.db`

### View Statistics

```bash
# Show sandbox statistics
make stats

# View container metrics
make list-containers

# Or use SQL directly (with improved schema)
sqlite3 ~/.sandbox_claude/sessions.db "SELECT * FROM sandboxes;"
```

### Export/Import Sessions

```python
from sandbox_claude import SessionStore

store = SessionStore()

# Export sessions
store.export_sessions(Path("sessions-backup.json"))

# Import sessions
store.import_sessions(Path("sessions-backup.json"))
```

## Makefile Commands

The project includes a comprehensive Makefile with these commands:

```bash
make help           # Show all available commands
make install        # Install package in development mode
make build          # Build the Python package
make test           # Run all tests with coverage
make test-unit      # Run unit tests only
make test-integration # Run integration tests only
make lint           # Run ruff linting
make format         # Format with black
make docker-build   # Build Docker base image
make docker-clean   # Remove Docker image
make clean          # Clean build artifacts
make dev-setup      # Complete development setup
make check-docker   # Verify Docker installation
make db-reset       # Reset session database
make stats          # Show sandbox statistics
make list-containers # List all containers
make stop-all       # Stop all sandbox containers
make remove-all     # Remove all sandbox containers
```

## Development

### Project Structure

```
sandbox_claude/
├── src/sandbox_claude/
│   ├── cli.py                 # CLI interface with type annotations
│   ├── container_manager.py   # Docker operations with error handling
│   ├── session_store.py      # SQLite persistence with indexes
│   ├── config_sync.py        # Configuration management and validation
│   └── utils.py              # Utility functions with secure randomization
├── docker/
│   ├── Dockerfile            # Multi-stage optimized base image
│   └── entrypoint.sh        # Container startup with health checks
├── tests/                    # Comprehensive test suite
├── setup.sh                  # Automated setup script
├── Makefile                  # Build automation with all targets
└── pyproject.toml           # Modern Python packaging with dependencies
```

### Running Tests

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests
make test-integration
```

### Code Quality

```bash
# Run linting (using ruff)
make lint

# Format code (using black)
make format

# Type checking (using mypy)
python -m mypy src/

# Run all quality checks
make lint format
```

## Troubleshooting

### Docker Connection Issues

```bash
# Check Docker status
make check-docker

# Verify Docker is running
docker info
```

### Container Won't Start

```bash
# Check container logs
docker logs <container-id>

# Rebuild base image
make docker-build --force
```

### Configuration Not Found

```bash
# Create default configuration
sandbox-claude config --create-default

# Verify configuration
ls -la ~/.claude*
```

### Database Issues

```bash
# Reset the session database
make db-reset

# Or manually
rm ~/.sandbox_claude/sessions.db
```

## Performance

### Startup Times

- **First run**: ~30 seconds (pulling/building base image)
- **Subsequent runs**: 2-3 seconds (using cached image)
- **With --reuse flag**: <1 second (attach to existing container)
- **Container pooling**: Instant allocation when pre-started

### Optimization Tips

1. **Use --reuse**: Reuse existing containers when possible
2. **Pre-build images**: Build base image during setup
3. **Cache volumes**: Mount cache directories for pip/npm
4. **Cleanup regularly**: Remove old containers to save space

## Security Considerations

- Claude configuration is mounted **read-only**
- Containers run with user-level privileges
- Container names use **cryptographically secure** random IDs
- SQL queries use **parameterized statements** to prevent injection
- Sensitive files should have appropriate permissions (auto-validated)
- Use `.dockerignore` to exclude sensitive files from builds
- Type-safe code prevents many runtime errors

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built for the Claude Code ecosystem
- Inspired by development environment managers like devcontainers
- Thanks to the Docker and Python communities

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Consult the troubleshooting guide above

---

Happy coding in your sandboxed environments! 🎉