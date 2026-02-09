"""
Enhanced Health Checks

Comprehensive health and readiness checks for all system dependencies.
Includes liveness, readiness, and service-specific health endpoints.
"""

import logging
import socket
from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import APIRouter

from src import __version__
from src.api.schemas import HealthCheckResponse, HealthStatus, ReadinessCheckResponse
from src.config import settings
from src.observability.logging import bind_agent_context


# Get logger for this module
logger = logging.getLogger(__name__)

# Create router for health endpoints
router = APIRouter(tags=["health"])


def check_postgres_health() -> HealthStatus:
    """
    Check PostgreSQL database health.

    Returns:
        Health status of PostgreSQL service
    """
    if settings.environment == "test":
        return HealthStatus.HEALTHY

    try:
        with socket.create_connection(
            (settings.postgres_host, settings.postgres_port),
            timeout=0.5,
        ):
            return HealthStatus.HEALTHY
    except OSError:
        return HealthStatus.UNHEALTHY


def check_redis_health() -> HealthStatus:
    """
    Check Redis cache health.

    Returns:
        Health status of Redis service
    """
    if settings.environment == "test":
        return HealthStatus.HEALTHY

    try:
        with socket.create_connection(
            (settings.redis_host, settings.redis_port),
            timeout=0.5,
        ):
            return HealthStatus.HEALTHY
    except OSError:
        return HealthStatus.UNHEALTHY


def check_minio_health() -> HealthStatus:
    """
    Check MinIO storage health.

    Returns:
        Health status of MinIO service
    """
    if settings.environment == "test":
        return HealthStatus.HEALTHY

    endpoint = settings.minio_endpoint
    if "://" not in endpoint:
        endpoint = f"http://{endpoint}"

    parsed = urlparse(endpoint)
    host = parsed.hostname
    port = parsed.port
    if not host:
        return HealthStatus.UNHEALTHY

    if port is None:
        port = 443 if settings.minio_secure else 80

    try:
        with socket.create_connection((host, port), timeout=0.5):
            return HealthStatus.HEALTHY
    except OSError:
        return HealthStatus.UNHEALTHY


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Basic liveness health check.

    Returns:
        Overall system health status
    """
    # Bind context for observability
    bind_agent_context("api", 0)

    logger.debug("Performing basic health check")

    # For liveness check, we just need to confirm the application is running
    response = HealthCheckResponse(
        status=HealthStatus.HEALTHY,
        timestamp=datetime.now(tz=UTC),
        services={"application": HealthStatus.HEALTHY},
        details={"version": __version__, "environment": settings.environment},
    )

    logger.debug("Basic health check completed", extra={"status": response.status})
    return response


@router.get("/ready", response_model=ReadinessCheckResponse)
async def readiness_check() -> ReadinessCheckResponse:
    """
    Comprehensive readiness check.

    Verifies all dependencies are ready to handle traffic.

    Returns:
        Readiness status of all system dependencies
    """
    # Bind context for observability
    bind_agent_context("api", 0)

    logger.info("Performing readiness check")

    # Check all dependencies
    postgres_status = check_postgres_health()
    redis_status = check_redis_health()
    minio_status = check_minio_health()

    dependencies = {
        "postgres": postgres_status,
        "redis": redis_status,
        "minio": minio_status,
    }

    # Determine overall status
    # If any service is UNHEALTHY, overall status is UNHEALTHY
    # If any service is DEGRADED, overall status is DEGRADED
    # Otherwise, overall status is HEALTHY
    overall_status = HealthStatus.HEALTHY
    for dependency_status in dependencies.values():
        if dependency_status == HealthStatus.UNHEALTHY:
            overall_status = HealthStatus.UNHEALTHY
            break
        elif dependency_status == HealthStatus.DEGRADED:
            overall_status = HealthStatus.DEGRADED

    response = ReadinessCheckResponse(
        status=overall_status,
        timestamp=datetime.now(tz=UTC),
        dependencies=dependencies,
        details={
            "environment": settings.environment,
            "checked_at": datetime.now(tz=UTC).isoformat(),
        },
    )

    # Log based on overall status
    if overall_status == HealthStatus.HEALTHY:
        logger.info("Readiness check passed", extra={"status": overall_status})
    elif overall_status == HealthStatus.DEGRADED:
        logger.warning("Readiness check degraded", extra={"status": overall_status})
    else:
        logger.error("Readiness check failed", extra={"status": overall_status})

    return response


@router.get("/health/postgres", response_model=HealthCheckResponse)
async def postgres_health_check() -> HealthCheckResponse:
    """
    PostgreSQL-specific health check.

    Returns:
        Health status of PostgreSQL service
    """
    # Bind context for observability
    bind_agent_context("api", 0)

    logger.debug("Performing PostgreSQL health check")

    postgres_status = check_postgres_health()

    response = HealthCheckResponse(
        status=postgres_status,
        timestamp=datetime.now(tz=UTC),
        services={"postgres": postgres_status},
        details={
            "host": settings.postgres_host,
            "port": settings.postgres_port,
            "database": settings.postgres_db,
        },
    )

    logger.debug("PostgreSQL health check completed", extra={"status": postgres_status})
    return response


@router.get("/health/redis", response_model=HealthCheckResponse)
async def redis_health_check() -> HealthCheckResponse:
    """
    Redis-specific health check.

    Returns:
        Health status of Redis service
    """
    # Bind context for observability
    bind_agent_context("api", 0)

    logger.debug("Performing Redis health check")

    redis_status = check_redis_health()

    response = HealthCheckResponse(
        status=redis_status,
        timestamp=datetime.now(tz=UTC),
        services={"redis": redis_status},
        details={
            "host": settings.redis_host,
            "port": settings.redis_port,
            "database": settings.redis_db,
        },
    )

    logger.debug("Redis health check completed", extra={"status": redis_status})
    return response


@router.get("/health/minio", response_model=HealthCheckResponse)
async def minio_health_check() -> HealthCheckResponse:
    """
    MinIO-specific health check.

    Returns:
        Health status of MinIO service
    """
    # Bind context for observability
    bind_agent_context("api", 0)

    logger.debug("Performing MinIO health check")

    minio_status = check_minio_health()

    response = HealthCheckResponse(
        status=minio_status,
        timestamp=datetime.now(tz=UTC),
        services={"minio": minio_status},
        details={
            "endpoint": settings.minio_endpoint,
            "bucket": settings.minio_bucket,
            "secure": settings.minio_secure,
        },
    )

    logger.debug("MinIO health check completed", extra={"status": minio_status})
    return response
