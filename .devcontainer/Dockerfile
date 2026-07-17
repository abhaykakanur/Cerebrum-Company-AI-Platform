# ==============================================================================
# Cerebrum — Dev Container image
#
# Base development environment for local VS Code Dev Containers and
# GitHub Codespaces. NOT a production or application image — see
# infrastructure/docker/docker-compose.yml for the infrastructure
# services this container connects to, and
# docs/architecture/specification/96_Deployment_Strategy.md for
# production deployment (unrelated to this file).
# ==============================================================================

FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# --- Python 3.12 + uv ---------------------------------------------------------
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
        python3.12 \
        python3.12-venv \
        python3-pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# --- Node.js 20 + pnpm ---------------------------------------------------------
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g pnpm@9 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# docker-outside-of-Docker (docker CLI itself) is installed by the
# devcontainer feature in devcontainer.json, not here.

USER vscode
