"""Extended tests for health checks aligned with current endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.api.health import (
    check_minio_health,
    check_postgres_health,
    check_redis_health,
    health_check,
    minio_health_check,
    postgres_health_check,
    readiness_check,
    redis_health_check,
)
from src.api.schemas import HealthStatus


def test_check_postgres_health_in_test_env() -> None:
    """Test postgres health shortcut in test environment."""
    with patch("src.api.health.settings.environment", "test"):
        assert check_postgres_health() == HealthStatus.HEALTHY


def test_check_postgres_health_socket_ok() -> None:
    """Test postgres health when socket connect succeeds."""
    with (
        patch("src.api.health.settings.environment", "development"),
        patch("src.api.health.socket.create_connection"),
    ):
        assert check_postgres_health() == HealthStatus.HEALTHY


def test_check_postgres_health_socket_error() -> None:
    """Test postgres health when socket connect fails."""
    with (
        patch("src.api.health.settings.environment", "development"),
        patch("src.api.health.socket.create_connection", side_effect=OSError()),
    ):
        assert check_postgres_health() == HealthStatus.UNHEALTHY


def test_check_redis_health_in_test_env() -> None:
    """Test redis health shortcut in test environment."""
    with patch("src.api.health.settings.environment", "test"):
        assert check_redis_health() == HealthStatus.HEALTHY


def test_check_redis_health_socket_ok() -> None:
    """Test redis health when socket connect succeeds."""
    with (
        patch("src.api.health.settings.environment", "development"),
        patch("src.api.health.socket.create_connection"),
    ):
        assert check_redis_health() == HealthStatus.HEALTHY


def test_check_redis_health_socket_error() -> None:
    """Test redis health when socket connect fails."""
    with (
        patch("src.api.health.settings.environment", "development"),
        patch("src.api.health.socket.create_connection", side_effect=OSError()),
    ):
        assert check_redis_health() == HealthStatus.UNHEALTHY


def test_check_minio_health_in_test_env() -> None:
    """Test minio health shortcut in test environment."""
    with patch("src.api.health.settings.environment", "test"):
        assert check_minio_health() == HealthStatus.HEALTHY


def test_check_minio_health_missing_host() -> None:
    """Test minio health returns unhealthy for bad endpoint."""
    with (
        patch("src.api.health.settings.environment", "development"),
        patch("src.api.health.settings.minio_endpoint", "://bad"),
    ):
        assert check_minio_health() == HealthStatus.UNHEALTHY


def test_check_minio_health_uses_default_port() -> None:
    """Test minio health uses default port based on secure flag."""
    with (
        patch("src.api.health.settings.environment", "development"),
        patch("src.api.health.settings.minio_endpoint", "minio.local"),
        patch("src.api.health.settings.minio_secure", False),
        patch("src.api.health.socket.create_connection") as mock_conn,
    ):
        assert check_minio_health() == HealthStatus.HEALTHY
        mock_conn.assert_called_once_with(("minio.local", 80), timeout=0.5)


def test_check_minio_health_secure_port() -> None:
    """Test minio health uses 443 when secure flag is set."""
    with (
        patch("src.api.health.settings.environment", "development"),
        patch("src.api.health.settings.minio_endpoint", "https://minio.local"),
        patch("src.api.health.settings.minio_secure", True),
        patch("src.api.health.socket.create_connection") as mock_conn,
    ):
        assert check_minio_health() == HealthStatus.HEALTHY
        mock_conn.assert_called_once_with(("minio.local", 443), timeout=0.5)


@pytest.mark.asyncio
async def test_readiness_check_healthy() -> None:
    """Test readiness check when all dependencies are healthy."""
    with (
        patch(
            "src.api.health.check_postgres_health", return_value=HealthStatus.HEALTHY
        ),
        patch("src.api.health.check_redis_health", return_value=HealthStatus.HEALTHY),
        patch("src.api.health.check_minio_health", return_value=HealthStatus.HEALTHY),
    ):
        response = await readiness_check()

    assert response.status == HealthStatus.HEALTHY
    assert response.dependencies["postgres"] == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_readiness_check_unhealthy() -> None:
    """Test readiness check with an unhealthy dependency."""
    with (
        patch(
            "src.api.health.check_postgres_health", return_value=HealthStatus.UNHEALTHY
        ),
        patch("src.api.health.check_redis_health", return_value=HealthStatus.HEALTHY),
        patch("src.api.health.check_minio_health", return_value=HealthStatus.HEALTHY),
    ):
        response = await readiness_check()

    assert response.status == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_health_check_response() -> None:
    """Test health_check response structure."""
    response = await health_check()

    assert response.status == HealthStatus.HEALTHY
    assert response.services["application"] == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_postgres_health_check_response() -> None:
    """Test postgres health check response details."""
    with patch(
        "src.api.health.check_postgres_health", return_value=HealthStatus.HEALTHY
    ):
        response = await postgres_health_check()

    assert response.services["postgres"] == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_redis_health_check_response() -> None:
    """Test redis health check response details."""
    with patch("src.api.health.check_redis_health", return_value=HealthStatus.HEALTHY):
        response = await redis_health_check()

    assert response.services["redis"] == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_minio_health_check_response() -> None:
    """Test minio health check response details."""
    with patch("src.api.health.check_minio_health", return_value=HealthStatus.HEALTHY):
        response = await minio_health_check()

    assert response.services["minio"] == HealthStatus.HEALTHY
