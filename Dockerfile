# Multi-stage Dockerfile for Multi-Tier Agent Ecosystem
# Supports both development (hot reload) and production builds

# ============================================================================
# BASE STAGE - Common dependencies
# ============================================================================
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Poetry Configuration
    POETRY_VERSION=2.3.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_HOME="/opt/poetry"

# Add Poetry and APPs bin to PATH
ENV PATH="$POETRY_HOME/bin:/usr/local/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry (System-wide)
RUN curl -sSL https://install.python-poetry.org | python3 -

# Create app directory
WORKDIR /app

# ============================================================================
# DEPENDENCIES STAGE - Install Python packages via Poetry
# ============================================================================
FROM base AS dependencies

# Copy Poetry configuration files
# We copy ONLY these first to leverage Docker layer caching
COPY pyproject.toml poetry.lock ./

# Install dependencies
# --no-root: Do not install the project itself yet (just libs)
# --without dev: Keep production image small
RUN poetry install --no-root --without dev

# ============================================================================
# DEVELOPMENT STAGE - Hot reload enabled
# ============================================================================
FROM dependencies AS development

# Install dev dependencies (testing tools, linters)
RUN poetry install --no-root --with dev

# Copy application code
COPY src/ /app/src/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with reload
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================================================
# PRODUCTION STAGE - Optimized for deployment
# ============================================================================
FROM dependencies AS production

# Copy application code
COPY src/ /app/src/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run without reload
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]