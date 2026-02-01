"""
FastAPI Application Entry Point

Main application with health checks, metrics endpoint, and CORS middleware.
Integrates structured logging and Prometheus metrics collection.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from src.api.health import router as health_router
from src.api.workflows import router as workflows_router
from src.config import settings


# Configure logging (will be implemented in TASK-039)
# For now, use basic structlog configuration
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "application_starting",
        environment=settings.environment,
        log_level=settings.log_level,
        version="1.0.0",
    )

    # TODO (TASK-036): Initialize PostgreSQL connection pool
    # TODO (TASK-038): Initialize Redis connection
    # TODO (TASK-037): Initialize MinIO client
    # TODO (TASK-046): Run database migrations (Alembic)

    yield

    # Shutdown
    logger.info("application_shutting_down")

    # TODO: Close database connections
    # TODO: Close Redis connections
    # TODO: Close MinIO connections


# Create FastAPI app
app = FastAPI(
    title="Multi-Tier Agent Ecosystem",
    description="LangGraph-native multi-agent system for automated SDLC",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "https://localhost:8080",
        "http://localhost:3000",  # Grafana
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "Multi-Tier Agent Ecosystem API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }


# Include API routers
app.include_router(health_router)
app.include_router(workflows_router)
