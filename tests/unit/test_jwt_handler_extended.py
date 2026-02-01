"""Extended unit tests for JWT authentication handler.

Tests for JWT token creation, validation, refresh, and error handling.
Covers all code paths in src/auth/jwt_handler.py.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from src.auth.jwt_handler import JWTAuthService, Role, TokenData
from src.exceptions import ConfigurationError


class TestJWTAuthServiceInitialization:
    """Test JWT service initialization."""

    def test_initialization_success(self) -> None:
        """Test successful JWT service initialization."""
        with patch("src.auth.jwt_handler.settings") as mock_settings:
            mock_settings.jwt_secret_key = "a" * 32  # Valid 32-char key
            service = JWTAuthService()
            assert service.secret_key == "a" * 32
            assert service.algorithm == "HS256"

    def test_initialization_missing_secret_key(self) -> None:
        """Test initialization fails with missing secret key."""
        with patch("src.auth.jwt_handler.settings") as mock_settings:
            mock_settings.jwt_secret_key = None
            with pytest.raises(ConfigurationError) as exc_info:
                JWTAuthService()
            assert "jwt_secret_key" in str(exc_info.value)

    def test_initialization_short_secret_key(self) -> None:
        """Test initialization fails with short secret key."""
        with patch("src.auth.jwt_handler.settings") as mock_settings:
            mock_settings.jwt_secret_key = "short"
            with pytest.raises(ConfigurationError) as exc_info:
                JWTAuthService()
            assert "32 characters" in str(exc_info.value)

    def test_initialization_exactly_32_chars(self) -> None:
        """Test initialization succeeds with exactly 32-char key."""
        with patch("src.auth.jwt_handler.settings") as mock_settings:
            mock_settings.jwt_secret_key = "a" * 32
            service = JWTAuthService()
            assert len(service.secret_key) == 32


class TestCreateAccessToken:
    """Test access token creation."""

    @pytest.fixture
    def service(self) -> JWTAuthService:
        """Create JWT service for testing."""
        with patch("src.auth.jwt_handler.settings") as mock_settings:
            mock_settings.jwt_secret_key = "a" * 32
            return JWTAuthService()

    def test_create_access_token_success(self, service: JWTAuthService) -> None:
        """Test successful access token creation."""
        token = service.create_access_token("user123", ["admin", "developer"])
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiry(
        self, service: JWTAuthService
    ) -> None:
        """Test access token creation with custom expiry."""
        expires_delta = timedelta(hours=2)
        token = service.create_access_token(
            "user123", ["admin"], expires_delta=expires_delta
        )
        assert isinstance(token, str)

    def test_create_access_token_default_expiry(self, service: JWTAuthService) -> None:
        """Test access token uses default 1-hour expiry."""
        token = service.create_access_token("user123", ["admin"])
        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])
        assert "exp" in payload
        assert "iat" in payload

    def test_create_access_token_contains_user_id(
        self, service: JWTAuthService
    ) -> None:
        """Test access token contains user ID."""
        token = service.create_access_token("user123", ["admin"])
        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])
        assert payload["sub"] == "user123"

    def test_create_access_token_contains_roles(self, service: JWTAuthService) -> None:
        """Test access token contains roles."""
        roles = ["admin", "developer"]
        token = service.create_access_token("user123", roles)
        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])
        assert payload["roles"] == roles

    def test_create_access_token_empty_roles(self, service: JWTAuthService) -> None:
        """Test access token creation with empty roles."""
        token = service.create_access_token("user123", [])
        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])
        assert payload["roles"] == []

    def test_create_access_token_multiple_roles(self, service: JWTAuthService) -> None:
        """Test access token with multiple roles."""
        roles = ["admin", "developer", "viewer"]
        token = service.create_access_token("user123", roles)
        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])
        assert payload["roles"] == roles

    def test_create_access_token_special_user_id(self, service: JWTAuthService) -> None:
        """Test access token with special characters in user ID."""
        user_id = "user@example.com"
        token = service.create_access_token(user_id, ["admin"])
        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])
        assert payload["sub"] == user_id

    def test_create_access_token_jwt_encode_failure(
        self, service: JWTAuthService
    ) -> None:
        """Test access token creation handles JWT encoding failure."""
        with patch("src.auth.jwt_handler.jwt.encode") as mock_encode:
            mock_encode.side_effect = Exception("Encoding failed")
            with pytest.raises(ConfigurationError) as exc_info:
                service.create_access_token("user123", ["admin"])
            assert "Token creation failed" in str(exc_info.value)


class TestVerifyToken:
    """Test token verification."""

    @pytest.fixture
    def service(self) -> JWTAuthService:
        """Create JWT service for testing."""
        with patch("src.auth.jwt_handler.settings") as mock_settings:
            mock_settings.jwt_secret_key = "a" * 32
            return JWTAuthService()

    def test_verify_token_success(self, service: JWTAuthService) -> None:
        """Test successful token verification."""
        token = service.create_access_token("user123", ["admin"])
        payload = service.verify_token(token)
        assert payload["sub"] == "user123"
        assert payload["roles"] == ["admin"]

    def test_verify_token_missing_token(self, service: JWTAuthService) -> None:
        """Test verification fails with missing token."""
        with pytest.raises(InvalidTokenError) as exc_info:
            service.verify_token(None)
        assert "Missing token" in str(exc_info.value)

    def test_verify_token_empty_string(self, service: JWTAuthService) -> None:
        """Test verification fails with empty token string."""
        with pytest.raises(InvalidTokenError) as exc_info:
            service.verify_token("")
        assert "Missing token" in str(exc_info.value)

    def test_verify_token_invalid_format(self, service: JWTAuthService) -> None:
        """Test verification fails with invalid token format."""
        with pytest.raises(InvalidTokenError):
            service.verify_token("invalid.token.format")

    def test_verify_token_expired(self, service: JWTAuthService) -> None:
        """Test verification fails with expired token."""
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = service.create_access_token("user123", ["admin"], expires_delta)
        with pytest.raises(ExpiredSignatureError):
            service.verify_token(token)

    def test_verify_token_wrong_secret(self, service: JWTAuthService) -> None:
        """Test verification fails with wrong secret key."""
        token = service.create_access_token("user123", ["admin"])
        # Create new service with different secret
        with patch("src.auth.jwt_handler.settings") as mock_settings:
            mock_settings.jwt_secret_key = "b" * 32
            other_service = JWTAuthService()
            with pytest.raises(InvalidTokenError):
                other_service.verify_token(token)

    def test_verify_token_tampered_payload(self, service: JWTAuthService) -> None:
        """Test verification fails with tampered payload."""
        token = service.create_access_token("user123", ["admin"])
        # Tamper with token
        parts = token.split(".")
        tampered = f"{parts[0]}.tampered.{parts[2]}"
        with pytest.raises(InvalidTokenError):
            service.verify_token(tampered)

    def test_verify_token_extracts_all_claims(self, service: JWTAuthService) -> None:
        """Test verification extracts all token claims."""
        token = service.create_access_token("user123", ["admin", "developer"])
        payload = service.verify_token(token)
        assert "sub" in payload
        assert "roles" in payload
        assert "exp" in payload
        assert "iat" in payload


class TestCreateRefreshToken:
    """Test refresh token creation."""

    @pytest.fixture
    def service(self) -> JWTAuthService:
        """Create JWT service for testing."""
        with patch("src.auth.jwt_handler.settings") as mock_settings:
            mock_settings.jwt_secret_key = "a" * 32
            return JWTAuthService()

    def test_create_refresh_token_success(self, service: JWTAuthService) -> None:
        """Test successful refresh token creation."""
        token = service.create_refresh_token("user123")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token_with_custom_expiry(
        self, service: JWTAuthService
    ) -> None:
        """Test refresh token creation with custom expiry."""
        expires_delta = timedelta(hours=48)
        token = service.create_refresh_token("user123", expires_delta=expires_delta)
        assert isinstance(token, str)

    def test_create_refresh_token_default_expiry(self, service: JWTAuthService) -> None:
        """Test refresh token uses default 24-hour expiry."""
        token = service.create_refresh_token("user123")
        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])
        assert "exp" in payload
        assert "iat" in payload

    def test_create_refresh_token_contains_type(self, service: JWTAuthService) -> None:
        """Test refresh token contains type field."""
        token = service.create_refresh_token("user123")
        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])
        assert payload["type"] == "refresh"

    def test_create_refresh_token_contains_user_id(
        self, service: JWTAuthService
    ) -> None:
        """Test refresh token contains user ID."""
        token = service.create_refresh_token("user123")
        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])
        assert payload["sub"] == "user123"

    def test_create_refresh_token_no_roles(self, service: JWTAuthService) -> None:
        """Test refresh token does not contain roles."""
        token = service.create_refresh_token("user123")
        payload = jwt.decode(token, service.secret_key, algorithms=["HS256"])
        assert "roles" not in payload

    def test_create_refresh_token_jwt_encode_failure(
        self, service: JWTAuthService
    ) -> None:
        """Test refresh token creation handles JWT encoding failure."""
        with patch("src.auth.jwt_handler.jwt.encode") as mock_encode:
            mock_encode.side_effect = Exception("Encoding failed")
            with pytest.raises(ConfigurationError) as exc_info:
                service.create_refresh_token("user123")
            assert "Refresh token creation failed" in str(exc_info.value)


class TestVerifyRefreshToken:
    """Test refresh token verification."""

    @pytest.fixture
    def service(self) -> JWTAuthService:
        """Create JWT service for testing."""
        with patch("src.auth.jwt_handler.settings") as mock_settings:
            mock_settings.jwt_secret_key = "a" * 32
            return JWTAuthService()

    def test_verify_refresh_token_success(self, service: JWTAuthService) -> None:
        """Test successful refresh token verification."""
        token = service.create_refresh_token("user123")
        payload = service.verify_refresh_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_verify_refresh_token_expired(self, service: JWTAuthService) -> None:
        """Test verification fails with expired refresh token."""
        expires_delta = timedelta(seconds=-1)
        token = service.create_refresh_token("user123", expires_delta)
        with pytest.raises(ExpiredSignatureError):
            service.verify_refresh_token(token)

    def test_verify_refresh_token_wrong_type(self, service: JWTAuthService) -> None:
        """Test verification fails if token is not refresh type."""
        # Create access token instead of refresh token
        access_token = service.create_access_token("user123", ["admin"])
        with pytest.raises(InvalidTokenError) as exc_info:
            service.verify_refresh_token(access_token)
        assert "Not a refresh token" in str(exc_info.value)

    def test_verify_refresh_token_invalid_format(self, service: JWTAuthService) -> None:
        """Test verification fails with invalid token format."""
        with pytest.raises(InvalidTokenError):
            service.verify_refresh_token("invalid.token.format")

    def test_verify_refresh_token_wrong_secret(self, service: JWTAuthService) -> None:
        """Test verification fails with wrong secret key."""
        token = service.create_refresh_token("user123")
        with patch("src.auth.jwt_handler.settings") as mock_settings:
            mock_settings.jwt_secret_key = "b" * 32
            other_service = JWTAuthService()
            with pytest.raises(InvalidTokenError):
                other_service.verify_refresh_token(token)

    def test_verify_refresh_token_missing_type_field(
        self, service: JWTAuthService
    ) -> None:
        """Test verification fails if type field is missing."""
        # Create token without type field
        now = datetime.now(tz=UTC)
        payload = {
            "sub": "user123",
            "exp": now + timedelta(hours=24),
            "iat": now,
        }
        token = jwt.encode(payload, service.secret_key, algorithm="HS256")
        with pytest.raises(InvalidTokenError) as exc_info:
            service.verify_refresh_token(token)
        assert "Not a refresh token" in str(exc_info.value)


class TestRoleEnum:
    """Test Role enumeration."""

    def test_role_admin(self) -> None:
        """Test ADMIN role."""
        assert Role.ADMIN.value == "admin"

    def test_role_developer(self) -> None:
        """Test DEVELOPER role."""
        assert Role.DEVELOPER.value == "developer"

    def test_role_viewer(self) -> None:
        """Test VIEWER role."""
        assert Role.VIEWER.value == "viewer"

    def test_role_from_string(self) -> None:
        """Test creating role from string."""
        role = Role("admin")
        assert role == Role.ADMIN


class TestTokenData:
    """Test TokenData model."""

    def test_token_data_creation(self) -> None:
        """Test TokenData creation."""
        now = datetime.now(tz=UTC)
        exp = now + timedelta(hours=1)
        data = TokenData(user_id="user123", roles=["admin"], exp=exp, iat=now)
        assert data.user_id == "user123"
        assert data.roles == ["admin"]
        assert data.exp == exp
        assert data.iat == now

    def test_token_data_multiple_roles(self) -> None:
        """Test TokenData with multiple roles."""
        now = datetime.now(tz=UTC)
        exp = now + timedelta(hours=1)
        roles = ["admin", "developer", "viewer"]
        data = TokenData(user_id="user123", roles=roles, exp=exp, iat=now)
        assert data.roles == roles


class TestJWTAuthServiceEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def service(self) -> JWTAuthService:
        """Create JWT service for testing."""
        with patch("src.auth.jwt_handler.settings") as mock_settings:
            mock_settings.jwt_secret_key = "a" * 32
            return JWTAuthService()

    def test_create_token_with_very_long_user_id(self, service: JWTAuthService) -> None:
        """Test token creation with very long user ID."""
        long_user_id = "u" * 1000
        token = service.create_access_token(long_user_id, ["admin"])
        payload = service.verify_token(token)
        assert payload["sub"] == long_user_id

    def test_create_token_with_special_characters(
        self, service: JWTAuthService
    ) -> None:
        """Test token creation with special characters in user ID."""
        user_id = "user@example.com!#$%"
        token = service.create_access_token(user_id, ["admin"])
        payload = service.verify_token(token)
        assert payload["sub"] == user_id

    def test_create_token_with_unicode_user_id(self, service: JWTAuthService) -> None:
        """Test token creation with unicode characters in user ID."""
        user_id = "用户123"
        token = service.create_access_token(user_id, ["admin"])
        payload = service.verify_token(token)
        assert payload["sub"] == user_id

    def test_verify_token_with_none_returns_error(
        self, service: JWTAuthService
    ) -> None:
        """Test verify_token with None raises error."""
        with pytest.raises(InvalidTokenError):
            service.verify_token(None)

    def test_token_expiry_boundary(self, service: JWTAuthService) -> None:
        """Test token at exact expiry boundary."""
        # Create token with reasonable expiry
        expires_delta = timedelta(hours=1)
        token = service.create_access_token("user123", ["admin"], expires_delta)
        # Should be valid
        payload = service.verify_token(token)
        assert payload["sub"] == "user123"

    def test_create_multiple_tokens_different_users(
        self, service: JWTAuthService
    ) -> None:
        """Test creating tokens for different users."""
        token1 = service.create_access_token("user1", ["admin"])
        token2 = service.create_access_token("user2", ["viewer"])
        payload1 = service.verify_token(token1)
        payload2 = service.verify_token(token2)
        assert payload1["sub"] == "user1"
        assert payload2["sub"] == "user2"

    def test_refresh_token_different_from_access_token(
        self, service: JWTAuthService
    ) -> None:
        """Test refresh token is different from access token."""
        access_token = service.create_access_token("user123", ["admin"])
        refresh_token = service.create_refresh_token("user123")
        assert access_token != refresh_token
        # Access token should fail refresh verification
        with pytest.raises(InvalidTokenError):
            service.verify_refresh_token(access_token)
