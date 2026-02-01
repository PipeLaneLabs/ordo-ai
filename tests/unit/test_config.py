"""
Unit Tests for Configuration Management

Tests Settings class validation, environment variable loading,
and configuration constraints.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.config import Settings


class TestSettingsValidation:
    """Test Settings validation rules."""

    def test_valid_settings(self, monkeypatch):
        """Test Settings with all valid values."""
        # Set all required environment variables
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_1234567890")
        monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_1234567890")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_jwt_secret_key_1234567890_very_long")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test_password_123")
        monkeypatch.setenv("MINIO_SECRET_KEY", "test_minio_secret_123")

        settings = Settings()

        assert settings.openrouter_api_key == "test_key_1234567890"
        assert settings.google_api_key == "test_google_key_1234567890"
        assert len(settings.jwt_secret_key) >= 32
        assert settings.postgres_password == "test_password_123"
        assert settings.minio_secret_key == "test_minio_secret_123"

    def test_api_key_too_short(self, monkeypatch):
        """Test that API keys must be at least 10 characters."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "short")  # Too short
        monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_1234567890")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_jwt_secret_key_1234567890_very_long")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test_password_123")
        monkeypatch.setenv("MINIO_SECRET_KEY", "test_minio_secret_123")

        with pytest.raises(PydanticValidationError) as exc_info:
            Settings()

        assert "at least 10 characters" in str(exc_info.value).lower()

    def test_jwt_secret_too_short(self, monkeypatch):
        """Test that JWT secret must be at least 32 characters."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_1234567890")
        monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_1234567890")
        monkeypatch.setenv("JWT_SECRET_KEY", "short_jwt_key")  # Too short
        monkeypatch.setenv("POSTGRES_PASSWORD", "test_password_123")
        monkeypatch.setenv("MINIO_SECRET_KEY", "test_minio_secret_123")

        with pytest.raises(PydanticValidationError) as exc_info:
            Settings()

        assert "at least 32 characters" in str(exc_info.value).lower()

    def test_password_too_short(self, monkeypatch):
        """Test that passwords must be at least 8 characters."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_1234567890")
        monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_1234567890")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_jwt_secret_key_1234567890_very_long")
        monkeypatch.setenv("POSTGRES_PASSWORD", "short")  # Too short
        monkeypatch.setenv("MINIO_SECRET_KEY", "test_minio_secret_123")

        with pytest.raises(PydanticValidationError) as exc_info:
            Settings()

        assert "at least 8 characters" in str(exc_info.value).lower()

    def test_default_values(self, monkeypatch):
        """Test that optional settings have correct defaults."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_1234567890")
        monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_1234567890")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_jwt_secret_key_1234567890_very_long")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test_password_123")
        monkeypatch.setenv("MINIO_SECRET_KEY", "test_minio_secret_123")
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        monkeypatch.delenv("POSTGRES_HOST", raising=False)
        monkeypatch.delenv("POSTGRES_PORT", raising=False)
        monkeypatch.delenv("POSTGRES_DB", raising=False)
        monkeypatch.delenv("POSTGRES_USER", raising=False)
        monkeypatch.delenv("REDIS_HOST", raising=False)
        monkeypatch.delenv("REDIS_PORT", raising=False)
        monkeypatch.delenv("REDIS_DB", raising=False)
        monkeypatch.delenv("MAX_TOKENS_PER_WORKFLOW", raising=False)
        monkeypatch.delenv("MAX_MONTHLY_BUDGET_USD", raising=False)
        monkeypatch.delenv("BUDGET_ALERT_THRESHOLD_PCT", raising=False)

        settings = Settings(_env_file=None)

        # Check default values
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.postgres_host == "localhost"
        assert settings.postgres_port == 5432
        assert settings.postgres_db == "agent_ecosystem"
        assert settings.postgres_user == "agent_user"
        assert settings.redis_host == "localhost"
        assert settings.redis_port == 6379
        assert settings.redis_db == 0
        assert settings.minio_endpoint == "localhost:9000"
        assert settings.minio_access_key == "minioadmin"
        assert settings.minio_bucket == "agent-artifacts"
        assert settings.minio_secure is False
        assert settings.max_tokens_per_workflow == 500000
        assert settings.max_monthly_budget_usd == 20.0
        assert settings.budget_alert_threshold_pct == 75.0

    def test_custom_values(self, monkeypatch):
        """Test that custom environment variables override defaults."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_1234567890")
        monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_1234567890")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_jwt_secret_key_1234567890_very_long")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test_password_123")
        monkeypatch.setenv("MINIO_SECRET_KEY", "test_minio_secret_123")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("POSTGRES_HOST", "db.example.com")
        monkeypatch.setenv("POSTGRES_PORT", "5433")
        monkeypatch.setenv("MAX_TOKENS_PER_WORKFLOW", "1000000")
        monkeypatch.setenv("MAX_MONTHLY_BUDGET_USD", "50.0")

        settings = Settings()

        assert settings.environment == "production"
        assert settings.log_level == "DEBUG"
        assert settings.postgres_host == "db.example.com"
        assert settings.postgres_port == 5433
        assert settings.max_tokens_per_workflow == 1000000
        assert settings.max_monthly_budget_usd == 50.0

    def test_postgres_url_property(self, monkeypatch):
        """Test PostgreSQL URL construction."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_1234567890")
        monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_1234567890")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_jwt_secret_key_1234567890_very_long")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test_password_123")
        monkeypatch.setenv("MINIO_SECRET_KEY", "test_minio_secret_123")

        settings = Settings()

        expected_url = (
            f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        assert settings.postgres_url == expected_url

    def test_redis_url_property(self, monkeypatch):
        """Test Redis URL construction."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_1234567890")
        monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_1234567890")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_jwt_secret_key_1234567890_very_long")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test_password_123")
        monkeypatch.setenv("MINIO_SECRET_KEY", "test_minio_secret_123")

        settings = Settings()

        expected_url = (
            f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
        )
        assert settings.redis_url == expected_url

    def test_budget_validation_positive_values(self, monkeypatch):
        """Test that budget values must be positive."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_1234567890")
        monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_1234567890")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_jwt_secret_key_1234567890_very_long")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test_password_123")
        monkeypatch.setenv("MINIO_SECRET_KEY", "test_minio_secret_123")
        monkeypatch.setenv("MAX_TOKENS_PER_WORKFLOW", "-1000")  # Invalid

        with pytest.raises(PydanticValidationError):
            Settings()

    def test_alert_threshold_range(self, monkeypatch):
        """Test that alert threshold is between 0 and 100."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_1234567890")
        monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_1234567890")
        monkeypatch.setenv("JWT_SECRET_KEY", "test_jwt_secret_key_1234567890_very_long")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test_password_123")
        monkeypatch.setenv("MINIO_SECRET_KEY", "test_minio_secret_123")
        monkeypatch.setenv("BUDGET_ALERT_THRESHOLD_PCT", "150")  # Invalid

        with pytest.raises(PydanticValidationError):
            Settings()
