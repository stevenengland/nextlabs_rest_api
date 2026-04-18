# Use the official Python 3.12 image
FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

# Pre-seed so Docker initializes the volume with correct ownership
RUN mkdir -p /home/vscode/.vscode-server /home/vscode/.claude /home/vscode/.copilot \
    && chown -R vscode:vscode /home/vscode/.vscode-server /home/vscode/.claude /home/vscode/.copilot

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Proxy build args — empty by default (CI-safe)
ARG http_proxy=""
ARG https_proxy=""

# Write apt proxy config if a proxy is provided; survives sudo at runtime
RUN if [ -n "$http_proxy" ]; then \
      printf 'Acquire::http::Proxy "%s/";\nAcquire::https::Proxy "%s/";\n' \
        "$http_proxy" "$https_proxy" \
        > /etc/apt/apt.conf.d/99proxy; \
    fi

# Remove Yarn repo if not needed, OR fix the GPG key
RUN rm -f /etc/apt/sources.list.d/yarn.list || true

# Install system packages (as root)
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install vhs (Charm apt repo) + ttyd (GitHub release binary).
# Used to (re)generate the README CLI demo at docs/cast/demo.svg from
# docs/cast/demo.tape. See docs/cast/README.md.
ARG TTYD_VERSION=1.7.7
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://repo.charm.sh/apt/gpg.key \
       | gpg --dearmor -o /etc/apt/keyrings/charm.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" \
       > /etc/apt/sources.list.d/charm.list \
    && apt-get update \
    && apt-get install -y vhs \
    && curl -fsSL "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.$(uname -m)" \
         -o /usr/local/bin/ttyd \
    && chmod +x /usr/local/bin/ttyd \
    && rm -rf /var/lib/apt/lists/*

# Create workspace directory
WORKDIR /workspace

# Copy the rest of the project files (excluding files in .dockerignore)
COPY . .

# Create a non-root user (if not already created by base image)
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Set up git (global configuration)
RUN git config --global init.defaultBranch main

# Switch to non-root user
USER $USERNAME
