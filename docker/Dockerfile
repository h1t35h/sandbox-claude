# Multi-stage build for optimized sandbox-claude base image
FROM ubuntu:22.04 AS base

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV NODE_VERSION=20
ENV CLAUDE_CODE_VERSION=latest

# Set working directory
WORKDIR /workspace

# Install system dependencies and development tools
RUN apt-get update && apt-get install -y \
    # Essential tools
    curl \
    wget \
    git \
    vim \
    nano \
    less \
    htop \
    # Build tools
    build-essential \
    pkg-config \
    cmake \
    # Python 3.12
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    # Network tools
    net-tools \
    iputils-ping \
    dnsutils \
    # Archive tools
    zip \
    unzip \
    tar \
    # Process management
    supervisor \
    # Shell enhancements
    zsh \
    tmux \
    # Locale
    locales \
    # Playwright browser dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 \
    fonts-liberation \
    fonts-noto-color-emoji \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code \
    && rm -f /root/.claude.json

# Install pip for Python 3.12 and common Python packages
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12 \
    && python3.12 -m pip install --upgrade pip setuptools wheel \
    && python3.12 -m pip install --ignore-installed \
    ipython \
    jupyter \
    numpy \
    pandas \
    requests \
    flask \
    fastapi \
    uvicorn \
    pytest \
    pytest-playwright \
    black \
    ruff \
    mypy \
    rich \
    click \
    pyyaml \
    playwright \
    mcp

# Install Python Playwright browsers
RUN python3.12 -m playwright install

# Install common Node packages globally
RUN npm install -g \
    typescript \
    ts-node \
    nodemon \
    prettier \
    eslint \
    jest \
    yarn \
    pnpm \
    playwright \
    @playwright/test

# Install Playwright browsers (Chromium, Firefox, WebKit)
# Install with --with-deps to ensure all system dependencies are met
RUN npx playwright install --with-deps chromium firefox webkit

# Configure locale
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Playwright environment variables
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# Create sandman user with UID/GID 1000
RUN groupadd -g 1000 sandman \
    && useradd -m -u 1000 -g sandman -s /bin/bash sandman \
    && usermod -aG sudo sandman \
    && echo "sandman ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Setup global gitignore for container-specific directories
RUN echo "# Sandbox-specific files" > /etc/gitignore && \
    echo ".sandbox_history" >> /etc/gitignore && \
    echo ".claude-config/" >> /etc/gitignore

# Configure global git settings for both users
RUN for user_home in /root /home/sandman; do \
        git config --file $user_home/.gitconfig core.excludesfile /etc/gitignore && \
        git config --file $user_home/.gitconfig init.defaultBranch main && \
        git config --file $user_home/.gitconfig safe.directory '*'; \
    done

# Setup shell environment for both users
RUN for user_home in /root /home/sandman; do \
        echo 'export PS1="\[\033[1;36m\]sandbox-claude\[\033[0m\]:\[\033[1;34m\]\w\[\033[0m\]$ "' >> $user_home/.bashrc && \
        echo 'export CLAUDE_CONFIG_DIR=/claude-config' >> $user_home/.bashrc && \
        echo 'alias ll="ls -la"' >> $user_home/.bashrc && \
        echo 'alias gs="git status"' >> $user_home/.bashrc && \
        echo 'alias gd="git diff"' >> $user_home/.bashrc && \
        echo 'alias python=python3' >> $user_home/.bashrc && \
        echo 'alias claude="claude --dangerously-skip-permissions"' >> $user_home/.bashrc && \
        echo 'alias claude-sync="/usr/local/bin/sync-claude-config.sh"' >> $user_home/.bashrc && \
        echo 'alias sync-claude="/usr/local/bin/sync-claude-config.sh"' >> $user_home/.bashrc && \
        echo 'alias claude-save="/usr/local/bin/sync-claude-config.sh"' >> $user_home/.bashrc && \
        echo 'alias claude-pull="/usr/local/bin/pull-claude-config.sh"' >> $user_home/.bashrc && \
        echo 'alias pull-claude="/usr/local/bin/pull-claude-config.sh"' >> $user_home/.bashrc && \
        echo 'alias claude-refresh="/usr/local/bin/pull-claude-config.sh"' >> $user_home/.bashrc && \
        echo 'alias claude-login="claude login && /usr/local/bin/sync-claude-config.sh"' >> $user_home/.bashrc; \
    done

# Create directories for configuration for both users
RUN mkdir -p /root/.claude \
    && mkdir -p /root/.config \
    && mkdir -p /home/sandman/.claude \
    && mkdir -p /home/sandman/.config \
    && chown -R sandman:sandman /home/sandman/.claude \
    && chown -R sandman:sandman /home/sandman/.config \
    && mkdir -p /workspace \
    && chown sandman:sandman /workspace \
    && mkdir -p /cache/pip \
    && mkdir -p /cache/npm \
    && chown -R sandman:sandman /cache \
    && mkdir -p /claude-config \
    && chown sandman:sandman /claude-config \
    && chmod 755 /claude-config \
    && mkdir -p /mcp-servers \
    && chown sandman:sandman /mcp-servers \
    && chmod 755 /mcp-servers

# Set cache directories
ENV PIP_CACHE_DIR=/cache/pip
ENV NPM_CONFIG_CACHE=/cache/npm

# Set Claude config directory to a mounted location (separate from workspace)
# This allows sharing config across different workspace containers
ENV CLAUDE_CONFIG_DIR=/claude-config

# Add entrypoint and utility scripts
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY sync-claude-config.sh /usr/local/bin/sync-claude-config.sh
COPY pull-claude-config.sh /usr/local/bin/pull-claude-config.sh
RUN chmod +x /usr/local/bin/entrypoint.sh \
    && chmod +x /usr/local/bin/sync-claude-config.sh \
    && chmod +x /usr/local/bin/pull-claude-config.sh

# Add MCP server and configuration
COPY mcp-playwright-server.py /mcp-servers/mcp-playwright-server.py
COPY mcp-config.json /mcp-servers/mcp-config.json
RUN chmod +x /mcp-servers/mcp-playwright-server.py \
    && chown -R sandman:sandman /mcp-servers

# Create a healthcheck script
RUN echo '#!/bin/bash\npython --version && node --version && git --version' > /usr/local/bin/healthcheck.sh \
    && chmod +x /usr/local/bin/healthcheck.sh

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh || exit 1

# Labels for metadata
LABEL maintainer="Sandbox Claude Team"
LABEL version="1.0.0"
LABEL description="Sandbox environment for Claude Code development"

# Switch to sandman user by default
USER sandman
WORKDIR /workspace

# Default command
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/bin/bash"]