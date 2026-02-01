import jwt
import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time

from src.api.workflows import get_current_user
from src.auth.jwt_handler import Role, jwt_service
from src.main import app


@pytest.fixture
def api_client_factory():
    def _factory(user_payload):
        async def override_get_current_user():
            return user_payload

        app.dependency_overrides[get_current_user] = override_get_current_user
        client = TestClient(app)
        return client

    return _factory


def test_jwt_creation_and_validation():
    """
    Tests that a JWT token can be created and validated successfully.
    """
    user_id = "test_user"
    roles = [Role.DEVELOPER.value]
    token = jwt_service.create_access_token(user_id, roles)

    payload = jwt_service.verify_token(token)
    assert payload["sub"] == user_id
    assert payload["roles"] == roles


def test_jwt_expired():
    """
    Tests that an expired JWT token fails validation.
    """
    user_id = "test_user"
    roles = [Role.DEVELOPER.value]
    with freeze_time("2023-01-01 12:00:00"):
        token = jwt_service.create_access_token(user_id, roles)

    with freeze_time("2023-01-01 13:00:01"):
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt_service.verify_token(token)


def test_jwt_invalid_signature():
    """
    Tests that a JWT with an invalid signature fails validation.
    """
    user_id = "test_user"
    roles = [Role.DEVELOPER.value]
    token = jwt_service.create_access_token(user_id, roles)

    # Tamper with the token
    tampered_token = token[:-5] + "asdfg"

    with pytest.raises(jwt.InvalidTokenError):
        jwt_service.verify_token(tampered_token)


def test_rbac_developer_permissions(api_client_factory):
    """
    Tests that a developer has the correct permissions.
    """
    user = {"sub": "dev_user", "roles": [Role.DEVELOPER.value]}
    client = api_client_factory(user)
    try:
        # This should succeed
        response = client.post(
            "/workflow/start", json={"user_request": "this is a valid test request"}
        )
        assert response.status_code == 200
        workflow_id = response.json()["workflow_id"]

        # This should fail
        response = client.delete(f"/workflow/{workflow_id}")
        assert response.status_code == 404  # 404 because the endpoint does not exist
    finally:
        app.dependency_overrides = {}


def test_rbac_viewer_permissions(api_client_factory):
    """
    Tests that a viewer has the correct permissions.
    """
    try:
        admin = {"sub": "admin_user", "roles": [Role.ADMIN.value]}
        admin_client = api_client_factory(admin)
        start = admin_client.post(
            "/workflow/start",
            json={"user_request": "this is a valid test request"},
        )
        assert start.status_code == 200
        workflow_id = start.json()["workflow_id"]

        viewer = {"sub": "viewer_user", "roles": [Role.VIEWER.value]}
        viewer_client = api_client_factory(viewer)

        response = viewer_client.get(f"/workflow/{workflow_id}/status")
        assert response.status_code == 200

        # This should fail
        response = viewer_client.post(
            "/workflow/start",
            json={"user_request": "this is a valid test request"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides = {}


def test_jwt_empty_roles():
    """
    Tests JWT creation with empty roles list.
    """
    user_id = "test_user"
    roles = []
    token = jwt_service.create_access_token(user_id, roles)

    payload = jwt_service.verify_token(token)
    assert payload["sub"] == user_id
    assert payload["roles"] == roles


def test_jwt_multiple_roles():
    """
    Tests JWT creation with multiple roles.
    """
    user_id = "test_user"
    roles = [Role.DEVELOPER.value, Role.VIEWER.value]
    token = jwt_service.create_access_token(user_id, roles)

    payload = jwt_service.verify_token(token)
    assert payload["sub"] == user_id
    assert payload["roles"] == roles
    assert len(payload["roles"]) == 2


def test_jwt_custom_expiration():
    """
    Tests JWT creation with custom expiration time.
    """
    user_id = "test_user"
    roles = [Role.DEVELOPER.value]

    # Create token with 30 minute expiration
    from datetime import timedelta

    token = jwt_service.create_access_token(user_id, roles, timedelta(minutes=30))

    payload = jwt_service.verify_token(token)
    assert payload["sub"] == user_id
    assert payload["roles"] == roles


def test_jwt_malformed_token():
    """
    Tests JWT verification with malformed token.
    """
    with pytest.raises(jwt.InvalidTokenError):
        jwt_service.verify_token("not.a.valid.token")


def test_jwt_none_token():
    """
    Tests JWT verification with None token.
    """
    with pytest.raises(jwt.InvalidTokenError):
        jwt_service.verify_token(None)


def test_jwt_empty_token():
    """
    Tests JWT verification with empty token.
    """
    with pytest.raises(jwt.InvalidTokenError):
        jwt_service.verify_token("")


def test_rbac_admin_permissions(api_client_factory):
    """
    Tests that an admin has full permissions.
    """
    user = {"sub": "admin_user", "roles": [Role.ADMIN.value]}
    client = api_client_factory(user)

    try:
        # All these should succeed for admin
        response = client.post("/workflow/start", json={"user_request": "test request"})
        assert response.status_code == 200

        workflow_id = response.json()["workflow_id"]

        response = client.get(f"/workflow/{workflow_id}/status")
        assert response.status_code == 200

        # Admin should have access to all endpoints
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/ready")
        assert response.status_code == 200
    finally:
        app.dependency_overrides = {}


def test_rbac_no_permissions(api_client_factory):
    """
    Tests user with no roles has minimal permissions.
    """
    user = {"sub": "no_role_user", "roles": []}
    client = api_client_factory(user)

    try:
        # Should be able to access public endpoints
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/ready")
        assert response.status_code == 200

        # Should not be able to access workflow endpoints
        response = client.post("/workflow/start", json={"user_request": "test request"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides = {}


def test_jwt_token_structure():
    """
    Tests that JWT tokens have the correct structure and claims.
    """
    user_id = "test_user"
    roles = [Role.DEVELOPER.value]
    token = jwt_service.create_access_token(user_id, roles)

    # Verify token structure (header.payload.signature)
    parts = token.split(".")
    assert len(parts) == 3

    # Verify standard claims exist
    payload = jwt_service.verify_token(token)
    assert "sub" in payload
    assert "roles" in payload
    assert "exp" in payload
    assert "iat" in payload
    assert isinstance(payload["roles"], list)


def test_jwt_token_immutability():
    """
    Tests that JWT tokens cannot be modified after creation.
    """
    user_id = "test_user"
    roles = [Role.DEVELOPER.value]
    token = jwt_service.create_access_token(user_id, roles)

    # Verify original token
    jwt_service.verify_token(token)

    # Try to modify the payload part (this should fail verification)
    parts = token.split(".")
    if len(parts) == 3:
        # This would create an invalid token
        tampered_token = parts[0] + "." + parts[1] + "modified" + "." + parts[2]
        with pytest.raises(jwt.InvalidTokenError):
            jwt_service.verify_token(tampered_token)
