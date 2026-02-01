"""Health Check Script for Multi-Tier Agent Ecosystem.

Validates all infrastructure services are running and accessible.
Run: poetry run python scripts/health_check.py
"""

import asyncio
import sys

import asyncpg
import httpx
import redis.asyncio as redis
from minio import Minio
from rich.console import Console
from rich.table import Table


console = Console()


async def check_postgres() -> tuple[bool, str]:
    """Check PostgreSQL database connectivity."""
    try:
        conn = await asyncpg.connect(
            "postgresql://agent_user:agent_password_secure_123@localhost:5432/agent_ecosystem"
        )
        # Verify tables exist
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        table_names = [row["table_name"] for row in tables]
        await conn.close()

        if len(table_names) >= 6:
            return True, f"Connected, {len(table_names)} tables found"
        else:
            return (
                False,
                f"Connected but only {len(table_names)} tables (expected 6+)",
            )
    except Exception as e:
        return False, str(e)


async def check_redis() -> tuple[bool, str]:
    """Check Redis cache connectivity."""
    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        pong = await r.ping()
        info = await r.info("memory")
        used_memory = info.get("used_memory_human", "unknown")
        await r.close()

        if pong:
            return True, f"PONG, Memory: {used_memory}"
        else:
            return False, "No response"
    except Exception as e:
        return False, str(e)


def check_minio() -> tuple[bool, str]:
    """Check MinIO object storage."""
    try:
        client = Minio(
            "localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin123",
            secure=False,
        )

        # Check if bucket exists
        bucket_exists = client.bucket_exists("agent-artifacts")

        if bucket_exists:
            # Count objects
            objects = list(client.list_objects("agent-artifacts", recursive=True))
            return True, f"Ready, {len(objects)} objects in bucket"
        else:
            return True, "Ready, bucket 'agent-artifacts' will be auto-created"
    except Exception as e:
        return False, str(e)


async def check_http_service(url: str, service_name: str) -> tuple[bool, str]:
    """Check HTTP service health."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return True, f"HTTP {resp.status_code}"
            else:
                return False, f"HTTP {resp.status_code}"
    except httpx.ConnectError:
        return False, "Connection refused (service not running?)"
    except httpx.TimeoutException:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


async def run_all_checks() -> dict[str, tuple[bool, str]]:
    """Run all health checks concurrently."""
    results = {}

    # Database checks
    results["PostgreSQL"] = await check_postgres()
    results["Redis"] = await check_redis()
    results["MinIO"] = await asyncio.to_thread(check_minio)

    # HTTP service checks
    results["FastAPI"] = await check_http_service(
        "http://localhost:8000/health", "FastAPI"
    )
    results["Chainlit"] = await check_http_service("http://localhost:8080", "Chainlit")
    results["Prometheus"] = await check_http_service(
        "http://localhost:9090/-/healthy", "Prometheus"
    )
    results["Grafana"] = await check_http_service(
        "http://localhost:3000/api/health", "Grafana"
    )

    return results


def print_results(results: dict[str, tuple[bool, str]]) -> int:
    """Print results in a formatted table."""
    table = Table(
        title="Infrastructure Health Check",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Service", style="cyan", width=15)
    table.add_column("Status", width=10)
    table.add_column("Details", style="dim")

    for service, (healthy, message) in results.items():
        status = "✅ Healthy" if healthy else "❌ Failed"
        status_style = "green" if healthy else "red"
        table.add_row(service, f"[{status_style}]{status}[/{status_style}]", message)

    console.print(table)

    # Summary
    healthy_count = sum(1 for h, _ in results.values() if h)
    total_count = len(results)

    console.print()
    if healthy_count == total_count:
        console.print(f"[green]✅ All {total_count} services healthy[/green]")
        return 0
    else:
        console.print(
            f"[yellow]⚠️  {healthy_count}/{total_count} services healthy[/yellow]"
        )
        console.print(
            "[red]Some services failed. Check docker-compose logs for details.[/red]"
        )
        return 1


async def main() -> None:
    """Main entry point."""
    console.print("[bold]Multi-Tier Agent Ecosystem - Health Check[/bold]")
    console.print()

    with console.status("[bold green]Running health checks..."):
        results = await run_all_checks()

    exit_code = print_results(results)

    # Helpful tips
    console.print()
    console.print("[dim]Troubleshooting:[/dim]")
    console.print("[dim]- View logs: docker-compose logs -f <service>[/dim]")
    console.print("[dim]- Restart service: docker-compose restart <service>[/dim]")
    console.print(
        "[dim]- Full restart: docker-compose down && docker-compose up -d[/dim]"
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Health check cancelled[/yellow]")
        sys.exit(1)
