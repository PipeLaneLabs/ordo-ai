"""
Configuration Management

Pydantic Settings-based configuration with environment variable validation.
All secrets and configuration loaded from .env or environment variables.
"""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment variables are loaded from .env file or system environment.
    All secrets must be provided via environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    environment: Literal["development", "production", "test"] = Field(
        default="development", description="Runtime environment"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )

    # Feature Flags
    enable_deviation_handler: bool = Field(
        default=True, description="Enable Deviation Handler Agent"
    )
    enable_strategy_validator: bool = Field(
        default=True, description="Enable Strategy Validator Agent"
    )
    enable_static_analysis: bool = Field(
        default=True, description="Enable Static Analysis Agent"
    )
    enable_observability_agent: bool = Field(
        default=True, description="Enable Observability Agent"
    )
    enable_documentation_agent: bool = Field(
        default=True, description="Enable Documentation Agent"
    )
    enable_commit_agent: bool = Field(default=False, description="Enable Commit Agent")

    # Human Approval Gates
    human_approval_tier_0: bool = Field(
        default=False, description="Approval gate for Tier 0 (Foundation)"
    )
    human_approval_tier_1: bool = Field(
        default=False, description="Approval gate for Tier 1 (Strategy)"
    )
    human_approval_tier_2: bool = Field(
        default=False, description="Approval gate for Tier 2 (Infrastructure)"
    )
    human_approval_tier_3: bool = Field(
        default=False, description="Approval gate for Tier 3 (Development)"
    )
    human_approval_tier_4: bool = Field(
        default=True, description="Approval gate for Tier 4 (Validation)"
    )
    human_approval_final: bool = Field(default=True, description="Final approval gate")

    # API Keys (LLM Providers)
    openrouter_api_key: str = Field(
        ...,
        description="OpenRouter API key for DeepSeek and other models",
        min_length=10,
    )
    google_api_key: str = Field(
        ..., description="Google Gemini API key (fallback provider)", min_length=10
    )

    # Security
    jwt_secret_key: str = Field(
        ..., description="JWT signing secret (min 32 characters)", min_length=32
    )
    encryption_key: str | None = Field(
        default=None,
        description="Encryption key for sensitive data (optional)",
        min_length=32,
    )
    chainlit_auth_secret: str | None = Field(
        default=None,
        description="Chainlit authentication secret",
        min_length=32,
    )

    # Database (PostgreSQL)
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="agent_ecosystem", description="Database name")
    postgres_user: str = Field(default="agent_user", description="Database user")
    postgres_password: str = Field(..., description="Database password", min_length=8)

    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")

    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # MinIO (S3-compatible storage)
    minio_endpoint: str = Field(default="localhost:9000", description="MinIO endpoint")
    minio_access_key: str = Field(default="minioadmin", description="MinIO access key")
    minio_secret_key: str = Field(..., description="MinIO secret key", min_length=8)
    minio_bucket: str = Field(
        default="agent-artifacts", description="MinIO bucket name"
    )
    minio_secure: bool = Field(default=False, description="Use HTTPS for MinIO")

    # Budget Limits
    max_tokens_per_workflow: int = Field(
        default=500000, description="Maximum tokens per workflow execution", gt=0
    )
    max_monthly_budget_usd: float = Field(
        default=20.0, description="Maximum monthly LLM budget in USD", gt=0
    )
    budget_alert_threshold_pct: float = Field(
        default=75.0, description="Budget warning threshold percentage", ge=0, le=100
    )
    total_budget_tokens: int = Field(
        default=1_000_000, description="Total token budget for workflow"
    )
    human_approval_timeout: int = Field(
        default=3600, description="Human approval timeout in seconds (default: 1 hour)"
    )

    # LLM Model Selection
    primary_llm_provider: Literal["openrouter", "google"] = Field(
        default="openrouter", description="Primary LLM provider"
    )
    fallback_llm_provider: Literal["openrouter", "google"] = Field(
        default="google", description="Fallback LLM provider"
    )

    # Observability (Optional)
    langsmith_api_key: str | None = Field(
        default=None, description="LangSmith API key for tracing (optional)"
    )
    langsmith_project: str = Field(
        default="multi-tier-agent-ecosystem", description="LangSmith project name"
    )

    # GitHub Integration (Optional)
    github_token: str | None = Field(
        default=None, description="GitHub personal access token (optional)"
    )

    # Sentry (Optional)
    sentry_dsn: str | None = Field(
        default=None, description="Sentry DSN for error tracking (optional)"
    )

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret key length."""
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters")
        return v

    @field_validator("postgres_password")
    @classmethod
    def validate_postgres_password(cls, v: str) -> str:
        """Validate PostgreSQL password strength."""
        if len(v) < 8:
            raise ValueError("PostgreSQL password must be at least 8 characters")
        return v

    # Observability Settings
    prometheus_enabled: bool = Field(
        default=True, description="Enable Prometheus metrics"
    )
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")

    # Retention Settings
    checkpoint_retention_days: int = Field(
        default=2, description="Days to retain workflow checkpoints"
    )
    max_checkpoints_per_workflow: int = Field(
        default=10, description="Maximum checkpoints per workflow"
    )
    log_retention_days: int = Field(default=30, description="Days to retain logs")
    artifact_retention_days: int = Field(
        default=90, description="Days to retain artifacts (MinIO)"
    )


# Global settings instance
# Settings are loaded from environment variables (.env file)
settings = Settings()  # type: ignore[call-arg]
