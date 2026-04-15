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
    # Add system deps here, e.g.:
    # libpq-dev \
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
