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
    black \
    ruff \
    mypy \
    rich \
    click \
    pyyaml

# Install common Node packages globally
RUN npm install -g \
    typescript \
    ts-node \
    nodemon \
    prettier \
    eslint \
    jest \
    yarn \
    pnpm

# Configure locale
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Setup shell environment
RUN echo 'export PS1="\[\033[1;36m\]sandbox-claude\[\033[0m\]:\[\033[1;34m\]\w\[\033[0m\]$ "' >> /root/.bashrc \
    && echo 'alias ll="ls -la"' >> /root/.bashrc \
    && echo 'alias gs="git status"' >> /root/.bashrc \
    && echo 'alias gd="git diff"' >> /root/.bashrc \
    && echo 'alias python=python3' >> /root/.bashrc

# Create directories for configuration
RUN mkdir -p /root/.claude \
    && mkdir -p /root/.config \
    && mkdir -p /workspace \
    && mkdir -p /cache/pip \
    && mkdir -p /cache/npm

# Set cache directories
ENV PIP_CACHE_DIR=/cache/pip
ENV NPM_CONFIG_CACHE=/cache/npm

# Add entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

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

# Default command
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/bin/bash"]