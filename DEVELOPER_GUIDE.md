# Developer Guide

**Project:** Multi-Tier Agent Ecosystem  
**Version:** 1.0  
**Last Updated:** 2026-01-30

## Table of Contents

1. [Quick Start](#quick-start)
2. [Development Environment Setup](#development-environment-setup)
3. [Running the Application](#running-the-application)
4. [Testing](#testing)
5. [Code Standards](#code-standards)
6. [Database Migrations](#database-migrations)
7. [Debugging](#debugging)
8. [Common Issues](#common-issues)

---

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git
- PostgreSQL client tools (psql)
- Redis CLI (optional)

### 5-Minute Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd my-agent-team

# 2. Copy environment file
cp .env.example .env

# 3. Start services with Docker Compose
docker-compose up -d

# 4. Initialize database
docker-compose exec agent-api bash scripts/init_db.sh

# 5. Run migrations
docker-compose exec agent-api bash scripts/run_migrations.sh

# 6. Verify health
docker-compose exec agent-api bash scripts/health_check.sh

# 7. Access the application
# FastAPI: http://localhost:8000
# Chainlit UI: http://localhost:8080
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000
```

---

## Development Environment Setup

### Local Development (Without Docker)

```bash
# 1. Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
pip install -e .

# 3. Set up environment variables
cp .env.example .env
# Edit .env with your local settings

# 4. Start PostgreSQL and Redis locally
# Option A: Using Docker for just the databases
docker-compose up -d postgres redis

# Option B: Using local installations
# Ensure PostgreSQL and Redis are running on default ports

# 5. Initialize database
bash scripts/init_db.sh

# 6. Run migrations
bash scripts/run_migrations.sh
```

### Docker Development

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f agent-api

# Stop services
docker-compose down

# Remove volumes (reset database)
docker-compose down -v
```

---

## Running the Application

### FastAPI Backend

```bash
# Development mode (with hot reload)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Chainlit UI

```bash
# Development mode
chainlit run src/chainlit_app/app.py -w

# Production mode
chainlit run src/chainlit_app/app.py
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View specific service logs
docker-compose logs -f agent-api
docker-compose logs -f agent-ui
docker-compose logs -f postgres

# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart agent-api
```

---

## Testing

### Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_config.py -v

# Run with coverage
pytest tests/unit/ --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_config.py::test_config_loading -v
```

### Integration Tests

```bash
# Run integration tests
pytest tests/integration/ -v

# Run optional integration suites (git/langgraph)
RUN_INTEGRATION=1 RUN_GIT=1 pytest tests/integration/ -v

# Run with specific markers
pytest -m integration -v
```

### E2E Tests

```bash
# Run end-to-end tests
pytest tests/e2e/ -v

# Run optional e2e suites (if enabled)
RUN_E2E=1 pytest tests/e2e/ -v

# Run with specific markers
pytest -m e2e -v
```

### All Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run with specific Python version
tox -e py312

# Run with linting
pytest tests/ -v --flake8 --mypy
```

### Test Configuration

Tests use `pytest` with the following configuration:
- **Config file:** `pytest.ini`
- **Fixtures:** `tests/conftest.py`
- **Markers:** `unit`, `integration`, `e2e`

### Optional Test Suites (CI)

Some integration suites require a configured git repo and full LangGraph setup.
They are gated behind environment flags and run in a dedicated CI job.

- `RUN_INTEGRATION=1` enables extended integration suites.
- `RUN_GIT=1` enables git-dependent integration suites.
- `RUN_E2E=1` enables e2e suites when present.
- `RUN_CHAINLIT_REAL=1` runs Chainlit tests against the real Chainlit package
    (unit tests otherwise use a local stub).

---

## Code Standards

### Style Guide

This project follows PEP 8 with the following tools:

#### Black (Code Formatter)

```bash
# Format code
black src/ tests/

# Check formatting
black --check src/ tests/
```

#### Ruff (Linter)

```bash
# Check code
ruff check src/ tests/

# Fix issues automatically
ruff check --fix src/ tests/
```

#### MyPy (Type Checker)

```bash
# Check types
mypy src/ --ignore-missing-imports

# Generate report
mypy src/ --html mypy_report
```

### Type Hints

All public functions and classes must have type hints:

```python
from typing import Optional, List
from src.models import User

def get_user(user_id: str) -> Optional[User]:
    """Get user by ID.
    
    Args:
        user_id: The user ID
        
    Returns:
        User object or None if not found
    """
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def process_workflow(workflow_id: str, config: dict) -> dict:
    """Process a workflow with the given configuration.
    
    Args:
        workflow_id: Unique workflow identifier
        config: Configuration dictionary with keys:
            - timeout: Maximum execution time in seconds
            - retries: Number of retry attempts
            
    Returns:
        Result dictionary with keys:
            - status: 'success' or 'failed'
            - output: Workflow output
            - duration: Execution time in seconds
            
    Raises:
        ValueError: If workflow_id is empty
        TimeoutError: If execution exceeds timeout
    """
    pass
```

### Complexity Limits

- **Cyclomatic Complexity:** Max 10 per function
- **Line Length:** Max 100 characters
- **Function Length:** Max 50 lines (excluding docstrings)

---

## Database Migrations

### Creating a Migration

```bash
# Generate a new migration
alembic revision --autogenerate -m "Add new_column to users table"

# Edit the generated file in migrations/versions/
# Then apply it
alembic upgrade head
```

### Running Migrations

```bash
# Upgrade to latest version
alembic upgrade head

# Upgrade to specific version
alembic upgrade 001

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade 001

# View migration history
alembic history --verbose

# View current version
alembic current
```

### Using Migration Scripts

```bash
# Initialize database
bash scripts/init_db.sh

# Run migrations
bash scripts/run_migrations.sh upgrade

# Check migration status
bash scripts/run_migrations.sh status

# Rollback to previous version
bash scripts/run_migrations.sh downgrade 001
```

---

## Debugging

### Enable Debug Logging

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or in .env
LOG_LEVEL=DEBUG
```

### View Application Logs

```bash
# Docker Compose
docker-compose logs -f agent-api

# Local development
# Logs are printed to console with DEBUG level
```

### Debug with Python Debugger

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use Python 3.7+ syntax
breakpoint()
```

### Database Debugging

```bash
# Connect to PostgreSQL
psql -h localhost -U agent_user -d agent_ecosystem

# View tables
\dt

# View table structure
\d checkpoints

# Run SQL query
SELECT * FROM workflows LIMIT 10;
```

### Redis Debugging

```bash
# Connect to Redis
redis-cli

# View keys
KEYS *

# Get value
GET key_name

# Monitor commands
MONITOR
```

---

## Common Issues

### Issue: Database Connection Failed

**Symptoms:** `psycopg2.OperationalError: could not connect to server`

**Solutions:**
1. Check PostgreSQL is running: `docker-compose ps postgres`
2. Verify credentials in `.env` file
3. Check network connectivity: `docker-compose exec postgres pg_isready`
4. Restart PostgreSQL: `docker-compose restart postgres`

### Issue: Port Already in Use

**Symptoms:** `Address already in use` error

**Solutions:**
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
docker-compose -f docker-compose.yml up -d -p 8001:8000
```

### Issue: Migration Fails

**Symptoms:** `alembic.util.exc.CommandError: Can't locate revision identified by`

**Solutions:**
1. Check migration files exist: `ls migrations/versions/`
2. Verify database is accessible
3. Check migration history: `alembic history --verbose`
4. Reset database: `docker-compose down -v && docker-compose up -d`

### Issue: Tests Fail with Import Errors

**Symptoms:** `ModuleNotFoundError: No module named 'src'`

**Solutions:**
```bash
# Install in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run tests from project root
cd /path/to/my-agent-team
pytest tests/
```

### Issue: Hot Reload Not Working

**Symptoms:** Code changes not reflected in running application

**Solutions:**
1. Ensure `--reload` flag is used: `uvicorn src.main:app --reload`
2. Check file permissions: `chmod 644 src/**/*.py`
3. Restart container: `docker-compose restart agent-api`
4. Check volume mounts in docker-compose.yml

### Issue: Out of Memory

**Symptoms:** `MemoryError` or container killed

**Solutions:**
1. Increase Docker memory limit in docker-compose.yml
2. Check for memory leaks: `docker stats`
3. Reduce worker count in production
4. Enable garbage collection: `gc.collect()`

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Chainlit Documentation](https://docs.chainlit.io/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [pytest Documentation](https://docs.pytest.org/)

---

## Getting Help

- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- Review [API_REFERENCE.md](API_REFERENCE.md) for API documentation
- Open an issue on GitHub
- Contact the development team
