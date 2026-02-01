"""Unit tests for FastAPI main application."""

from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_root_endpoint() -> None:
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Multi-Tier Agent Ecosystem API"
    assert "version" in data
    assert "health" in data


def test_health_check() -> None:
    """Test health check returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "services" in data
    assert "details" in data


def test_readiness_check() -> None:
    """Test readiness check endpoint."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "dependencies" in data
    assert "timestamp" in data
    assert "details" in data
