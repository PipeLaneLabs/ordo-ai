"""
Comprehensive tests for health check endpoints.

Tests cover:
- Basic liveness checks
- Readiness checks with all dependencies
- Service-specific health checks (PostgreSQL, Redis, MinIO)
- Health status determination logic
- Error handling and edge cases
- Socket connection failures
"""

from unittest.mock import MagicMock, patch

import pytest

from src import __version__
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


class TestCheckPostgresHealth:
    """Tests for PostgreSQL health check function."""

    def test_check_postgres_health_test_environment(self):
        """Test PostgreSQL health check in test environment."""
        with patch("src.api.health.settings.environment", "test"):
            result = check_postgres_health()
            assert result == HealthStatus.HEALTHY

    def test_check_postgres_health_healthy(self):
        """Test PostgreSQL health check when service is healthy."""
        with (
            patch("src.api.health.settings.environment", "production"),
            patch("src.api.health.settings.postgres_host", "localhost"),
            patch("src.api.health.settings.postgres_port", 5432),
            patch("src.api.health.socket.create_connection") as mock_socket,
        ):
            mock_socket.return_value = MagicMock()
            result = check_postgres_health()
            assert result == HealthStatus.HEALTHY

    def test_check_postgres_health_unhealthy(self):
        """Test PostgreSQL health check when service is unhealthy."""
        with (
            patch("src.api.health.settings.environment", "production"),
            patch("src.api.health.settings.postgres_host", "localhost"),
            patch("src.api.health.settings.postgres_port", 5432),
            patch("src.api.health.socket.create_connection") as mock_socket,
        ):
            mock_socket.side_effect = OSError("Connection refused")
            result = check_postgres_health()
            assert result == HealthStatus.UNHEALTHY


class TestCheckRedisHealth:
    """Tests for Redis health check function."""

    def test_check_redis_health_test_environment(self):
        """Test Redis health check in test environment."""
        with patch("src.api.health.settings.environment", "test"):
            result = check_redis_health()
            assert result == HealthStatus.HEALTHY

    def test_check_redis_health_healthy(self):
        """Test Redis health check when service is healthy."""
        with (
            patch("src.api.health.settings.environment", "production"),
            patch("src.api.health.settings.redis_host", "localhost"),
            patch("src.api.health.settings.redis_port", 6379),
            patch("src.api.health.socket.create_connection") as mock_socket,
        ):
            mock_socket.return_value = MagicMock()
            result = check_redis_health()
            assert result == HealthStatus.HEALTHY

    def test_check_redis_health_unhealthy(self):
        """Test Redis health check when service is unhealthy."""
        with (
            patch("src.api.health.settings.environment", "production"),
            patch("src.api.health.settings.redis_host", "localhost"),
            patch("src.api.health.settings.redis_port", 6379),
            patch("src.api.health.socket.create_connection") as mock_socket,
        ):
            mock_socket.side_effect = OSError("Connection refused")
            result = check_redis_health()
            assert result == HealthStatus.UNHEALTHY


class TestCheckMinioHealth:
    """Tests for MinIO health check function."""

    def test_check_minio_health_test_environment(self):
        """Test MinIO health check in test environment."""
        with patch("src.api.health.settings.environment", "test"):
            result = check_minio_health()
            assert result == HealthStatus.HEALTHY

    def test_check_minio_health_healthy_with_protocol(self):
        """Test MinIO health check when service is healthy with protocol."""
        with (
            patch("src.api.health.settings.environment", "production"),
            patch("src.api.health.settings.minio_endpoint", "http://localhost:9000"),
            patch("src.api.health.settings.minio_secure", False),
            patch("src.api.health.socket.create_connection") as mock_socket,
        ):
            mock_socket.return_value = MagicMock()
            result = check_minio_health()
            assert result == HealthStatus.HEALTHY

    def test_check_minio_health_healthy_without_protocol(self):
        """Test MinIO health check when service is healthy without protocol."""
        with (
            patch("src.api.health.settings.environment", "production"),
            patch("src.api.health.settings.minio_endpoint", "localhost:9000"),
            patch("src.api.health.settings.minio_secure", False),
            patch("src.api.health.socket.create_connection") as mock_socket,
        ):
            mock_socket.return_value = MagicMock()
            result = check_minio_health()
            assert result == HealthStatus.HEALTHY

    def test_check_minio_health_unhealthy(self):
        """Test MinIO health check when service is unhealthy."""
        with (
            patch("src.api.health.settings.environment", "production"),
            patch("src.api.health.settings.minio_endpoint", "localhost:9000"),
            patch("src.api.health.settings.minio_secure", False),
            patch("src.api.health.socket.create_connection") as mock_socket,
        ):
            mock_socket.side_effect = OSError("Connection refused")
            result = check_minio_health()
            assert result == HealthStatus.UNHEALTHY

    def test_check_minio_health_invalid_endpoint(self):
        """Test MinIO health check with invalid endpoint."""
        with (
            patch("src.api.health.settings.environment", "production"),
            patch("src.api.health.settings.minio_endpoint", ""),
            patch("src.api.health.settings.minio_secure", False),
        ):
            result = check_minio_health()
            assert result == HealthStatus.UNHEALTHY

    def test_check_minio_health_secure_default_port(self):
        """Test MinIO health check with secure connection default port."""
        with (
            patch("src.api.health.settings.environment", "production"),
            patch("src.api.health.settings.minio_endpoint", "localhost"),
            patch("src.api.health.settings.minio_secure", True),
            patch("src.api.health.socket.create_connection") as mock_socket,
        ):
            mock_socket.return_value = MagicMock()
            result = check_minio_health()
            assert result == HealthStatus.HEALTHY
            # Verify port 443 was used for secure connection
            mock_socket.assert_called_once()
            call_args = mock_socket.call_args
            assert call_args[0][0][1] == 443

    def test_check_minio_health_insecure_default_port(self):
        """Test MinIO health check with insecure connection default port."""
        with (
            patch("src.api.health.settings.environment", "production"),
            patch("src.api.health.settings.minio_endpoint", "localhost"),
            patch("src.api.health.settings.minio_secure", False),
            patch("src.api.health.socket.create_connection") as mock_socket,
        ):
            mock_socket.return_value = MagicMock()
            result = check_minio_health()
            assert result == HealthStatus.HEALTHY
            # Verify port 80 was used for insecure connection
            mock_socket.assert_called_once()
            call_args = mock_socket.call_args
            assert call_args[0][0][1] == 80


class TestHealthCheckEndpoint:
    """Tests for /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test basic health check endpoint."""
        with patch("src.api.health.bind_agent_context"):
            response = await health_check()

            assert response.status == HealthStatus.HEALTHY
            assert response.timestamp is not None
            assert "application" in response.services
            assert response.services["application"] == HealthStatus.HEALTHY
            assert "version" in response.details
            assert response.details["version"] == __version__

    @pytest.mark.asyncio
    async def test_health_check_response_structure(self):
        """Test health check response structure."""
        with patch("src.api.health.bind_agent_context"):
            response = await health_check()

            assert hasattr(response, "status")
            assert hasattr(response, "timestamp")
            assert hasattr(response, "services")
            assert hasattr(response, "details")
            assert isinstance(response.services, dict)
            assert isinstance(response.details, dict)


class TestReadinessCheckEndpoint:
    """Tests for /ready endpoint."""

    @pytest.mark.asyncio
    async def test_readiness_check_all_healthy(self):
        """Test readiness check when all dependencies are healthy."""
        with (
            patch("src.api.health.check_postgres_health") as mock_pg,
            patch("src.api.health.check_redis_health") as mock_redis,
            patch("src.api.health.check_minio_health") as mock_minio,
            patch("src.api.health.bind_agent_context"),
        ):
            mock_pg.return_value = HealthStatus.HEALTHY
            mock_redis.return_value = HealthStatus.HEALTHY
            mock_minio.return_value = HealthStatus.HEALTHY

            response = await readiness_check()

            assert response.status == HealthStatus.HEALTHY
            assert response.dependencies["postgres"] == HealthStatus.HEALTHY
            assert response.dependencies["redis"] == HealthStatus.HEALTHY
            assert response.dependencies["minio"] == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_readiness_check_one_unhealthy(self):
        """Test readiness check when one dependency is unhealthy."""
        with (
            patch("src.api.health.check_postgres_health") as mock_pg,
            patch("src.api.health.check_redis_health") as mock_redis,
            patch("src.api.health.check_minio_health") as mock_minio,
            patch("src.api.health.bind_agent_context"),
        ):
            mock_pg.return_value = HealthStatus.UNHEALTHY
            mock_redis.return_value = HealthStatus.HEALTHY
            mock_minio.return_value = HealthStatus.HEALTHY

            response = await readiness_check()

            assert response.status == HealthStatus.UNHEALTHY
            assert response.dependencies["postgres"] == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_readiness_check_one_degraded(self):
        """Test readiness check when one dependency is degraded."""
        with (
            patch("src.api.health.check_postgres_health") as mock_pg,
            patch("src.api.health.check_redis_health") as mock_redis,
            patch("src.api.health.check_minio_health") as mock_minio,
            patch("src.api.health.bind_agent_context"),
        ):
            mock_pg.return_value = HealthStatus.DEGRADED
            mock_redis.return_value = HealthStatus.HEALTHY
            mock_minio.return_value = HealthStatus.HEALTHY

            response = await readiness_check()

            assert response.status == HealthStatus.DEGRADED
            assert response.dependencies["postgres"] == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_readiness_check_response_structure(self):
        """Test readiness check response structure."""
        with (
            patch("src.api.health.check_postgres_health") as mock_pg,
            patch("src.api.health.check_redis_health") as mock_redis,
            patch("src.api.health.check_minio_health") as mock_minio,
            patch("src.api.health.bind_agent_context"),
        ):
            mock_pg.return_value = HealthStatus.HEALTHY
            mock_redis.return_value = HealthStatus.HEALTHY
            mock_minio.return_value = HealthStatus.HEALTHY

            response = await readiness_check()

            assert hasattr(response, "status")
            assert hasattr(response, "timestamp")
            assert hasattr(response, "dependencies")
            assert hasattr(response, "details")
            assert "postgres" in response.dependencies
            assert "redis" in response.dependencies
            assert "minio" in response.dependencies


class TestPostgresHealthCheckEndpoint:
    """Tests for /health/postgres endpoint."""

    @pytest.mark.asyncio
    async def test_postgres_health_check_healthy(self):
        """Test PostgreSQL health check endpoint when healthy."""
        with (
            patch("src.api.health.check_postgres_health") as mock_check,
            patch("src.api.health.bind_agent_context"),
        ):
            mock_check.return_value = HealthStatus.HEALTHY

            response = await postgres_health_check()

            assert response.status == HealthStatus.HEALTHY
            assert "postgres" in response.services
            assert response.services["postgres"] == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_postgres_health_check_unhealthy(self):
        """Test PostgreSQL health check endpoint when unhealthy."""
        with (
            patch("src.api.health.check_postgres_health") as mock_check,
            patch("src.api.health.bind_agent_context"),
        ):
            mock_check.return_value = HealthStatus.UNHEALTHY

            response = await postgres_health_check()

            assert response.status == HealthStatus.UNHEALTHY
            assert response.services["postgres"] == HealthStatus.UNHEALTHY


class TestRedisHealthCheckEndpoint:
    """Tests for /health/redis endpoint."""

    @pytest.mark.asyncio
    async def test_redis_health_check_healthy(self):
        """Test Redis health check endpoint when healthy."""
        with (
            patch("src.api.health.check_redis_health") as mock_check,
            patch("src.api.health.bind_agent_context"),
        ):
            mock_check.return_value = HealthStatus.HEALTHY

            response = await redis_health_check()

            assert response.status == HealthStatus.HEALTHY
            assert "redis" in response.services
            assert response.services["redis"] == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_redis_health_check_unhealthy(self):
        """Test Redis health check endpoint when unhealthy."""
        with (
            patch("src.api.health.check_redis_health") as mock_check,
            patch("src.api.health.bind_agent_context"),
        ):
            mock_check.return_value = HealthStatus.UNHEALTHY

            response = await redis_health_check()

            assert response.status == HealthStatus.UNHEALTHY
            assert response.services["redis"] == HealthStatus.UNHEALTHY


class TestMinioHealthCheckEndpoint:
    """Tests for /health/minio endpoint."""

    @pytest.mark.asyncio
    async def test_minio_health_check_healthy(self):
        """Test MinIO health check endpoint when healthy."""
        with (
            patch("src.api.health.check_minio_health") as mock_check,
            patch("src.api.health.bind_agent_context"),
        ):
            mock_check.return_value = HealthStatus.HEALTHY

            response = await minio_health_check()

            assert response.status == HealthStatus.HEALTHY
            assert "minio" in response.services
            assert response.services["minio"] == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_minio_health_check_unhealthy(self):
        """Test MinIO health check endpoint when unhealthy."""
        with (
            patch("src.api.health.check_minio_health") as mock_check,
            patch("src.api.health.bind_agent_context"),
        ):
            mock_check.return_value = HealthStatus.UNHEALTHY

            response = await minio_health_check()

            assert response.status == HealthStatus.UNHEALTHY
            assert response.services["minio"] == HealthStatus.UNHEALTHY


class TestHealthCheckEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_readiness_check_all_unhealthy(self):
        """Test readiness check when all dependencies are unhealthy."""
        with (
            patch("src.api.health.check_postgres_health") as mock_pg,
            patch("src.api.health.check_redis_health") as mock_redis,
            patch("src.api.health.check_minio_health") as mock_minio,
            patch("src.api.health.bind_agent_context"),
        ):
            mock_pg.return_value = HealthStatus.UNHEALTHY
            mock_redis.return_value = HealthStatus.UNHEALTHY
            mock_minio.return_value = HealthStatus.UNHEALTHY

            response = await readiness_check()

            assert response.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_readiness_check_mixed_degraded_and_unhealthy(self):
        """Test readiness check with mixed degraded and unhealthy statuses."""
        with (
            patch("src.api.health.check_postgres_health") as mock_pg,
            patch("src.api.health.check_redis_health") as mock_redis,
            patch("src.api.health.check_minio_health") as mock_minio,
            patch("src.api.health.bind_agent_context"),
        ):
            mock_pg.return_value = HealthStatus.UNHEALTHY
            mock_redis.return_value = HealthStatus.DEGRADED
            mock_minio.return_value = HealthStatus.HEALTHY

            response = await readiness_check()

            # Unhealthy takes precedence
            assert response.status == HealthStatus.UNHEALTHY

    def test_check_minio_health_with_explicit_port(self):
        """Test MinIO health check with explicit port in endpoint."""
        with (
            patch("src.api.health.settings.environment", "production"),
            patch("src.api.health.settings.minio_endpoint", "localhost:9001"),
            patch("src.api.health.settings.minio_secure", False),
            patch("src.api.health.socket.create_connection") as mock_socket,
        ):
            mock_socket.return_value = MagicMock()
            result = check_minio_health()
            assert result == HealthStatus.HEALTHY
            # Verify explicit port was used
            mock_socket.assert_called_once()
            call_args = mock_socket.call_args
            assert call_args[0][0][1] == 9001
