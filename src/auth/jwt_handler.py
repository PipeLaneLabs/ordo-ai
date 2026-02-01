"""
JWT Authentication Handler

Handles JWT token creation, validation, and refresh operations.
Implements stateless authentication with embedded user roles.
"""

import logging
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import jwt


try:
    from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
except ImportError:
    try:
        from jwt import ExpiredSignatureError, InvalidTokenError
    except ImportError:
        # Fallback for PyJWT 2.8+
        class ExpiredSignatureError(Exception):
            pass

        class InvalidTokenError(Exception):
            pass


from pydantic import BaseModel

from src.config import settings
from src.exceptions import ConfigurationError
from src.observability.logging import bind_agent_context


# Get logger for this module
logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class TokenData(BaseModel):
    """Data structure for JWT claims."""

    user_id: str
    roles: list[str]
    exp: datetime
    iat: datetime


class JWTAuthService:
    """
    Stateless JWT authentication service.

    No database lookups required for validation.
    Tokens contain all necessary user information.
    """

    def __init__(self) -> None:
        """Initialize JWT service with configuration."""
        self.secret_key = settings.jwt_secret_key
        if not self.secret_key or len(self.secret_key) < 32:
            raise ConfigurationError(
                "jwt_secret_key", "JWT secret key must be at least 32 characters"
            )
        self.algorithm = "HS256"
        logger.debug("JWT authentication service initialized")

    def create_access_token(
        self, user_id: str, roles: list[str], expires_delta: timedelta | None = None
    ) -> str:
        """
        Create JWT access token with user information.

        Args:
            user_id: Unique identifier for the user
            roles: List of roles assigned to the user
            expires_delta: Token expiration time (default: 1 hour)

        Returns:
            Encoded JWT token string

        Raises:
            ConfigurationError: If JWT configuration is invalid
        """
        # Bind context for observability
        bind_agent_context("auth", 0)

        if expires_delta is None:
            expires_delta = timedelta(hours=1)

        now = datetime.now(tz=UTC)
        payload = {
            "sub": user_id,
            "roles": roles,
            "exp": now + expires_delta,
            "iat": now,
        }

        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(
                "Access token created",
                extra={
                    "user_id": user_id,
                    "roles": roles,
                    "expires_at": (now + expires_delta).isoformat(),
                },
            )
            return token
        except Exception as e:
            logger.error(
                "Failed to create access token",
                extra={"user_id": user_id, "error": str(e)},
            )
            raise ConfigurationError(
                "jwt_handler", f"Token creation failed: {e!s}"
            ) from e

    def verify_token(self, token: str | None) -> dict[str, Any]:
        """
        Verify JWT token and extract claims.

        Args:
            token: JWT token string to verify

        Returns:
            Dictionary containing token claims

        Raises:
            jwt.ExpiredSignatureError: Token has expired
            jwt.InvalidTokenError: Token is invalid
        """
        # Bind context for observability
        bind_agent_context("auth", 0)

        if not token:
            logger.error("Token verification failed: missing token")
            raise InvalidTokenError("Missing token")

        try:
            payload: dict[str, Any] = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            logger.debug(
                "Token verified successfully", extra={"user_id": payload.get("sub")}
            )
            return payload
        except ExpiredSignatureError:
            logger.warning("Token verification failed: expired token")
            raise
        except InvalidTokenError as e:
            logger.error(
                "Token verification failed: invalid token", extra={"error": str(e)}
            )
            raise

    def create_refresh_token(
        self, user_id: str, expires_delta: timedelta | None = None
    ) -> str:
        """
        Create JWT refresh token.

        Args:
            user_id: Unique identifier for the user
            expires_delta: Token expiration time (default: 24 hours)

        Returns:
            Encoded JWT refresh token string
        """
        # Bind context for observability
        bind_agent_context("auth", 0)

        if expires_delta is None:
            expires_delta = timedelta(hours=24)

        now = datetime.now(tz=UTC)
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": now + expires_delta,
            "iat": now,
        }

        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(
                "Refresh token created",
                extra={
                    "user_id": user_id,
                    "expires_at": (now + expires_delta).isoformat(),
                },
            )
            return token
        except Exception as e:
            logger.error(
                "Failed to create refresh token",
                extra={"user_id": user_id, "error": str(e)},
            )
            raise ConfigurationError(
                "jwt_handler", f"Refresh token creation failed: {e!s}"
            ) from e

    def verify_refresh_token(self, token: str) -> dict[str, Any] | None:
        """
        Verify refresh token and extract claims.

        Args:
            token: Refresh token string to verify

        Returns:
            Dictionary containing token claims

        Raises:
            jwt.ExpiredSignatureError: Token has expired
            jwt.InvalidTokenError: Token is invalid or not a refresh token
        """
        # Bind context for observability
        bind_agent_context("auth", 0)

        try:
            payload: dict[str, Any] = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )

            # Verify this is a refresh token
            if payload.get("type") != "refresh":
                logger.warning("Invalid refresh token: wrong token type")
                raise InvalidTokenError("Not a refresh token")

            logger.debug(
                "Refresh token verified successfully",
                extra={"user_id": payload.get("sub")},
            )
            return payload
        except ExpiredSignatureError:
            logger.warning("Refresh token verification failed: expired token")
            raise
        except InvalidTokenError as e:
            logger.error(
                "Refresh token verification failed: invalid token",
                extra={"error": str(e)},
            )
            raise


# Global instance for application use
jwt_service = JWTAuthService()
