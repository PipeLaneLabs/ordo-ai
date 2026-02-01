"""Environment Variables Validation Script.

Validates all required environment variables are set correctly.
Run: poetry run python scripts/validate_env.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table


console = Console()

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    console.print(f"[yellow]⚠️  .env file not found at: {env_path}[/yellow]")
    console.print("[yellow]Copy .env.example to .env and fill in your values[/yellow]")
    sys.exit(1)


def check_env_var(
    name: str, required: bool = True, min_length: int = 0
) -> tuple[bool, str]:
    """Check if environment variable is set and valid."""
    value = os.getenv(name)

    if not value:
        if required:
            return False, "Missing (required)"
        else:
            return True, "Not set (optional)"

    if min_length > 0 and len(value) < min_length:
        return False, f"Too short (min {min_length} chars, got {len(value)})"

    # Mask sensitive values
    if "KEY" in name or "SECRET" in name or "PASSWORD" in name:
        masked = value[:10] + "..." if len(value) > 10 else value
        return True, f"Set ({masked})"
    else:
        return True, f"Set ({value})"


def validate_all() -> list[tuple[str, bool, str]]:
    """Validate all environment variables."""
    checks = []

    # Required LLM API Keys
    checks.append(
        (
            "OPENROUTER_API_KEY",
            *check_env_var("OPENROUTER_API_KEY", required=True, min_length=10),
        )
    )
    checks.append(
        (
            "GOOGLE_API_KEY",
            *check_env_var("GOOGLE_API_KEY", required=True, min_length=10),
        )
    )

    # Required Application Secrets
    checks.append(
        (
            "JWT_SECRET_KEY",
            *check_env_var("JWT_SECRET_KEY", required=True, min_length=32),
        )
    )

    # Optional but Recommended
    checks.append(
        (
            "CHAINLIT_AUTH_SECRET",
            *check_env_var("CHAINLIT_AUTH_SECRET", required=False, min_length=32),
        )
    )
    checks.append(("ENCRYPTION_KEY", *check_env_var("ENCRYPTION_KEY", required=False)))

    # Database Configuration
    checks.append(("POSTGRES_HOST", *check_env_var("POSTGRES_HOST", required=True)))
    checks.append(("POSTGRES_PORT", *check_env_var("POSTGRES_PORT", required=True)))
    checks.append(("POSTGRES_DB", *check_env_var("POSTGRES_DB", required=True)))
    checks.append(("POSTGRES_USER", *check_env_var("POSTGRES_USER", required=True)))
    checks.append(
        (
            "POSTGRES_PASSWORD",
            *check_env_var("POSTGRES_PASSWORD", required=True, min_length=8),
        )
    )

    # Redis Configuration
    checks.append(("REDIS_HOST", *check_env_var("REDIS_HOST", required=True)))
    checks.append(("REDIS_PORT", *check_env_var("REDIS_PORT", required=True)))

    # MinIO Configuration
    checks.append(("MINIO_ENDPOINT", *check_env_var("MINIO_ENDPOINT", required=True)))
    checks.append(
        ("MINIO_ACCESS_KEY", *check_env_var("MINIO_ACCESS_KEY", required=True))
    )
    checks.append(
        ("MINIO_SECRET_KEY", *check_env_var("MINIO_SECRET_KEY", required=True))
    )
    checks.append(("MINIO_BUCKET", *check_env_var("MINIO_BUCKET", required=True)))

    # Application Settings
    checks.append(("ENVIRONMENT", *check_env_var("ENVIRONMENT", required=True)))
    checks.append(("LOG_LEVEL", *check_env_var("LOG_LEVEL", required=True)))
    checks.append(
        ("MAX_MONTHLY_BUDGET", *check_env_var("MAX_MONTHLY_BUDGET", required=False))
    )

    # Optional External Services
    checks.append(("GITHUB_TOKEN", *check_env_var("GITHUB_TOKEN", required=False)))
    checks.append(("SENTRY_DSN", *check_env_var("SENTRY_DSN", required=False)))
    checks.append(
        ("LANGCHAIN_API_KEY", *check_env_var("LANGCHAIN_API_KEY", required=False))
    )

    return checks


def print_results(checks: list[tuple[str, bool, str]]) -> None:
    """Print validation results in a table."""
    table = Table(
        title="Environment Variables Validation",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Variable", style="cyan", width=30)
    table.add_column("Status", width=10)
    table.add_column("Details", style="dim")

    for var_name, is_valid, message in checks:
        status = "✅ Valid" if is_valid else "❌ Invalid"
        status_style = "green" if is_valid else "red"
        table.add_row(var_name, f"[{status_style}]{status}[/{status_style}]", message)

    console.print(table)


def main() -> int:
    """Main entry point."""
    console.print("[bold]Environment Variables Validation[/bold]")
    console.print()

    checks = validate_all()
    print_results(checks)

    # Summary
    valid_count = sum(1 for _, valid, _ in checks if valid)
    required_checks = [c for c in checks if "required" in c[2].lower()]
    required_valid = sum(1 for c in required_checks if c[1])

    console.print()
    console.print("[bold]Summary:[/bold]")
    console.print(f"  Total variables: {len(checks)}")
    console.print(f"  Valid: {valid_count}")
    console.print(f"  Invalid: {len(checks) - valid_count}")
    console.print(f"  Required valid: {required_valid}/{len(required_checks)}")

    # Exit code
    if all(c[1] for c in required_checks):
        console.print()
        console.print("[green]✅ All required environment variables are valid[/green]")
        console.print("[green]You can start the application[/green]")
        return 0
    else:
        console.print()
        console.print(
            "[red]❌ Some required environment variables are missing or invalid[/red]"
        )
        console.print(
            "[yellow]Please fix the issues above before starting the application[/yellow]"
        )
        console.print()
        console.print("[dim]Helpful commands:[/dim]")
        console.print("[dim]- Generate JWT secret: openssl rand -hex 32[/dim]")
        console.print(
            '[dim]- Generate encryption key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"[/dim]'
        )
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Validation cancelled[/yellow]")
        sys.exit(1)
