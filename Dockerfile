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
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# ============================================================================
# DEPENDENCIES STAGE - Install Python packages
# ============================================================================
FROM base AS dependencies

# Install Poetry
RUN pip install poetry==2.3.1

# Copy only dependency files first (for Docker layer caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies (without installing the project itself)
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# ============================================================================
# DEVELOPMENT STAGE - Hot reload enabled
# ============================================================================
FROM dependencies AS development

# Install development dependencies
RUN poetry install --no-root --with dev --no-interaction --no-ansi

# Copy application code
# Note: In docker-compose, this is mounted as volume for hot reload
# COPY src/ /app/src/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command (can be overridden in docker-compose)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================================================
# PRODUCTION STAGE - Optimized for deployment
# ============================================================================
FROM dependencies AS production

# Copy application code
COPY src/ /app/src/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command (no --reload)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
