from fastapi.testclient import TestClient


def test_health_check(test_client: TestClient):
    """
    Tests the /health endpoint.
    """
    response = test_client.get("/health")
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == "healthy"
    assert "timestamp" in json_response
    assert "services" in json_response
    assert "details" in json_response
    assert json_response["details"]["version"] == "1.0.0"


def test_readiness_check(test_client: TestClient):
    """
    Tests the /ready endpoint.
    """
    response = test_client.get("/ready")
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] in ["healthy", "degraded", "unhealthy"]
    assert "dependencies" in json_response


def test_health_check_structure(test_client: TestClient):
    """
    Tests the structure and content of health check response.
    """
    response = test_client.get("/health")
    assert response.status_code == 200

    data = response.json()

    # Test required fields
    assert "status" in data
    assert "timestamp" in data
    assert "services" in data
    assert "details" in data

    # Test field types
    assert isinstance(data["status"], str)
    assert isinstance(data["timestamp"], str)
    assert isinstance(data["services"], dict)
    assert isinstance(data["details"], dict)

    # Test service structure
    services = data["services"]
    assert "application" in services
    assert services["application"] in ["healthy", "unhealthy", "degraded"]


def test_readiness_check_structure(test_client: TestClient):
    """
    Tests the structure and content of readiness check response.
    """
    response = test_client.get("/ready")
    assert response.status_code == 200

    data = response.json()

    # Test required fields
    assert "status" in data
    assert "dependencies" in data
    assert "timestamp" in data
    assert "details" in data

    # Test field types
    assert isinstance(data["status"], str)
    assert isinstance(data["dependencies"], dict)
    assert isinstance(data["timestamp"], str)
    assert isinstance(data["details"], dict)

    # Test dependency structure
    dependencies = data["dependencies"]
    assert "postgres" in dependencies
    assert "redis" in dependencies
    assert "minio" in dependencies

    # Test dependency status values
    assert dependencies["postgres"] in ["healthy", "unhealthy", "degraded"]
    assert dependencies["redis"] in ["healthy", "unhealthy", "degraded"]
    assert dependencies["minio"] in ["healthy", "unhealthy", "degraded"]


def test_root_endpoint(test_client: TestClient):
    """
    Tests the root endpoint returns API information.
    """
    response = test_client.get("/")
    assert response.status_code == 200

    data = response.json()

    # Test required fields
    assert "name" in data
    assert "version" in data
    assert "docs" in data
    assert "health" in data
    assert "metrics" in data

    # Test field values
    assert data["name"] == "Multi-Tier Agent Ecosystem API"
    assert data["version"] == "1.0.0"
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"
    assert data["metrics"] == "/metrics"


def test_health_check_content_type(test_client: TestClient):
    """
    Tests that health endpoints return JSON content type.
    """
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    response = test_client.get("/ready")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_health_endpoints_availability(test_client: TestClient):
    """
    Tests that health endpoints are always available and responsive.
    """
    # Test multiple rapid requests
    for _ in range(5):
        response = test_client.get("/health")
        assert response.status_code == 200

        response = test_client.get("/ready")
        assert response.status_code == 200
