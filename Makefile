# Makefile for sandbox-claude

.PHONY: help install build test clean docker-build docker-push run-example

PYTHON := python3
PIP := $(PYTHON) -m pip
PROJECT_NAME := sandbox-claude
DOCKER_IMAGE := sandbox-claude-base
DOCKER_TAG := latest
DOCKER_FULL := $(DOCKER_IMAGE):$(DOCKER_TAG)

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)Sandbox Claude - Development Environment Manager$(NC)"
	@echo ""
	@echo "Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## Install the package in development mode
	$(PIP) install -e ".[dev]"
	@echo "$(GREEN)✓ Package installed successfully$(NC)"

build: ## Build the package
	$(PYTHON) -m build
	@echo "$(GREEN)✓ Package built successfully$(NC)"

test: ## Run tests
	pytest tests/ -v --cov=sandbox_claude --cov-report=term-missing

test-unit: ## Run unit tests only
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	pytest tests/integration/ -v

lint: ## Run linting
	ruff check src/
	mypy src/

format: ## Format code
	black src/ tests/
	ruff check --fix src/ tests/

docker-build: ## Build the Docker base image
	@echo "$(YELLOW)Building Docker image: $(DOCKER_FULL)$(NC)"
	docker build -t $(DOCKER_FULL) -f docker/Dockerfile docker/
	@echo "$(GREEN)✓ Docker image built successfully$(NC)"

docker-push: ## Push Docker image to registry
	@echo "$(YELLOW)Pushing Docker image: $(DOCKER_FULL)$(NC)"
	docker push $(DOCKER_FULL)

docker-clean: ## Remove Docker image
	docker rmi $(DOCKER_FULL) || true
	@echo "$(GREEN)✓ Docker image removed$(NC)"

run-example: ## Run an example sandbox session
	sandbox-claude new -p example -f test

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✓ Cleaned build artifacts$(NC)"

dev-setup: ## Setup development environment
	$(PIP) install --upgrade pip setuptools wheel
	$(MAKE) install
	$(MAKE) docker-build
	@echo "$(GREEN)✓ Development environment ready$(NC)"

check-docker: ## Check Docker installation and status
	@echo "Checking Docker status..."
	@docker --version || (echo "$(RED)✗ Docker not installed$(NC)" && exit 1)
	@docker info > /dev/null 2>&1 || (echo "$(RED)✗ Docker daemon not running$(NC)" && exit 1)
	@echo "$(GREEN)✓ Docker is ready$(NC)"

db-reset: ## Reset the session database
	rm -f ~/.sandbox_claude/sessions.db
	@echo "$(GREEN)✓ Session database reset$(NC)"

stats: ## Show sandbox statistics
	@echo "$(YELLOW)Sandbox Statistics:$(NC)"
	@echo ""
	@sqlite3 ~/.sandbox_claude/sessions.db "SELECT 'Total containers:', COUNT(*) FROM sandboxes;" 2>/dev/null || echo "No sessions yet"
	@sqlite3 ~/.sandbox_claude/sessions.db "SELECT 'Running:', COUNT(*) FROM sandboxes WHERE status='running';" 2>/dev/null || true
	@sqlite3 ~/.sandbox_claude/sessions.db "SELECT 'Projects:', COUNT(DISTINCT project_name) FROM sandboxes;" 2>/dev/null || true
	@echo ""
	@docker ps -a --filter "label=sandbox.claude.version" --format "table {{.Names}}\t{{.Status}}\t{{.Created}}" 2>/dev/null || true

list-containers: ## List all sandbox containers
	@docker ps -a --filter "label=sandbox.claude.version" --format "table {{.Names}}\t{{.Status}}\t{{.Created}}"

stop-all: ## Stop all sandbox containers
	@echo "$(YELLOW)Stopping all sandbox containers...$(NC)"
	@docker stop $$(docker ps -q --filter "label=sandbox.claude.version") 2>/dev/null || true
	@echo "$(GREEN)✓ All containers stopped$(NC)"

remove-all: ## Remove all sandbox containers
	@echo "$(YELLOW)Removing all sandbox containers...$(NC)"
	@docker rm -f $$(docker ps -aq --filter "label=sandbox.claude.version") 2>/dev/null || true
	@echo "$(GREEN)✓ All containers removed$(NC)"

release: ## Create a new release
	@echo "$(YELLOW)Creating release...$(NC)"
	$(PYTHON) -m build
	twine check dist/*
	@echo "$(GREEN)✓ Release ready. Run 'twine upload dist/*' to publish$(NC)"

.DEFAULT_GOAL := help