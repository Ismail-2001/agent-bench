# Production-ready Dockerfile for agentbench
# Use uv for ultra-fast dependency management

FROM python:3.12-slim-bookworm AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy project configuration
COPY pyproject.toml README.md ./
COPY scenarios/ ./scenarios/
COPY src/ ./src/

# Install dependencies (frozen)
RUN uv pip install --system .[all]

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose if we ever add a web server for reports, otherwise just a CLI tool
# ENTRYPOINT ["agentbench"]

CMD ["agentbench", "--help"]
