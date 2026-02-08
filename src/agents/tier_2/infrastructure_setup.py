"""Infrastructure Setup Agent for Tier 2.

Provisions and configures runtime environment with:
- Docker Compose configuration
- Environment variable templates
- Database initialization scripts
- Service health checks
- Developer onboarding guide
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import Settings
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


class InfrastructureSetupAgent(BaseAgent):
    """Tier 2 agent for infrastructure provisioning and setup.

    Uses Gemini-2.5-Flash for infrastructure configuration.
    Generates INFRASTRUCTURE.md, docker-compose.yml, .env.example.

    Attributes:
        token_budget: 4,000 tokens for infrastructure setup
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
    ) -> None:
        """Initialize Infrastructure Setup Agent.

        Args:
            llm_client: LLM client (should use Gemini-2.5-Flash for speed)
            budget_guard: Budget guard instance
            settings: Application settings
        """
        super().__init__(
            name="InfrastructureSetupAgent",
            llm_client=llm_client,
            budget_guard=budget_guard,
            settings=settings,
            token_budget=4000,  # 4K tokens for infrastructure config
        )

    async def _build_prompt(
        self,
        state: WorkflowState,  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> str:
        """Build infrastructure setup prompt for LLM.

        Args:
            state: Current workflow state
            **kwargs: Additional context

        Returns:
            Formatted prompt for infrastructure configuration
        """
        # Read required artifacts
        architecture = await self._read_if_exists("ARCHITECTURE.md")
        dependencies = await self._read_if_exists("DEPENDENCIES.md")

        if not architecture:
            raise ValueError(
                "ARCHITECTURE.md not found - Solution Architect must run first"
            )

        prompt = f"""# Infrastructure Setup Task

## Architecture Document
{architecture}

## Dependencies Document
{dependencies or "No dependencies document available"}

## Your Task
As an Infrastructure Setup Agent, provision and configure the complete runtime
environment for this project.

### Setup Framework

1. **Service Inventory**
   - Identify all services from ARCHITECTURE.md (database, cache, storage,
     etc.)
   - Determine ports, volumes, networks
   - Define health checks for each service
   - Specify resource limits (CPU, memory)

2. **Docker Compose Configuration**
   - Create docker-compose.yml with all services
   - Configure service dependencies (depends_on)
   - Set up networks and volumes
   - Include health checks and restart policies

3. **Environment Variables**
   - Create .env.example template
   - Document all required secrets
   - Provide example values (non-sensitive)
   - Group by service/category

4. **Database Initialization**
   - Create init scripts (schema creation, seed data)
   - Define migration strategy
   - Document manual setup steps

5. **Developer Guide**
   - Create DEVELOPER_GUIDE.md
   - Include setup instructions (clone, install, run)
   - Document common commands (test, lint, migrate)
   - Troubleshooting section

## Output Format

Generate an INFRASTRUCTURE.md document with the following structure:

```markdown
# Infrastructure Setup

**Project:** [Project Name]
**Version:** 1.0
**Date:** [Current Date]
**Agent:** Infrastructure Setup Agent
**Status:** CONFIGURED

---

## Table of Contents
1. [Services](#services)
2. [Docker Compose Configuration](#docker-compose-configuration)
3. [Environment Variables](#environment-variables)
4. [Database Setup](#database-setup)
5. [Service Health Checks](#service-health-checks)
6. [Initialization Steps](#initialization-steps)
7. [Developer Guide](#developer-guide)

---

## Services

### 1. Application (FastAPI)
- **Image:** python:3.12-slim
- **Port:** 8000 (HTTPS via mkcert)
- **Dependencies:** PostgreSQL, Redis, MinIO
- **Health Check:** GET /health
- **Resource Limits:** 2GB RAM, 2 CPU cores

### 2. Database (PostgreSQL)
- **Image:** postgres:16-alpine
- **Port:** 5432
- **Volume:** postgres_data:/var/lib/postgresql/data
- **Health Check:** pg_isready
- **Resource Limits:** 1GB RAM, 1 CPU core

### 3. Cache (Redis)
- **Image:** redis:7-alpine
- **Port:** 6379
- **Volume:** redis_data:/data
- **Health Check:** redis-cli ping
- **Resource Limits:** 512MB RAM, 1 CPU core

### 4. Object Storage (MinIO)
- **Image:** minio/minio:latest
- **Ports:** 9000 (API), 9001 (Console)
- **Volume:** minio_data:/data
- **Health Check:** curl http://localhost:9000/minio/health/live
- **Resource Limits:** 1GB RAM, 1 CPU core

### 5. Metrics (Prometheus)
- **Image:** prom/prometheus:latest
- **Port:** 9090
- **Volume:** prometheus_data:/prometheus
- **Config:** prometheus.yml
- **Resource Limits:** 512MB RAM, 1 CPU core

### 6. Dashboards (Grafana)
- **Image:** grafana/grafana:latest
- **Port:** 3000
- **Volume:** grafana_data:/var/lib/grafana
- **Credentials:** admin/admin (change on first login)
- **Resource Limits:** 512MB RAM, 1 CPU core

### 7. UI (Chainlit)
- **Image:** python:3.12-slim
- **Port:** 8080
- **Dependencies:** FastAPI backend
- **Health Check:** GET /
- **Resource Limits:** 1GB RAM, 1 CPU core

---

## Docker Compose Configuration

### docker-compose.yml

```yaml
version: '3.8'

services:
  # Application Service
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: agent-api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/agent_db
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    networks:
      - agent-network
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G

  # PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    container_name: postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=agent_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sh:/docker-entrypoint-initdb.d/init_db.sh
    networks:
      - agent-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - agent-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M

  # MinIO Object Storage
  minio:
    image: minio/minio:latest
    container_name: minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    networks:
      - agent-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  # Prometheus Metrics
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'
    networks:
      - agent-network
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M

  # Grafana Dashboards
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus
    networks:
      - agent-network
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M

  # Chainlit UI
  chainlit:
    build:
      context: .
      dockerfile: Dockerfile.chainlit
    container_name: chainlit-ui
    ports:
      - "8080:8080"
    environment:
      - BACKEND_URL=http://app:8000
    depends_on:
      - app
    networks:
      - agent-network
    volumes:
      - ./src/chainlit_app:/app
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

networks:
  agent-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  minio_data:
  prometheus_data:
  grafana_data:
```

---

## Environment Variables

### .env.example

```bash
# Application
APP_NAME=multi-tier-agent-ecosystem
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/agent_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=agent-artifacts
MINIO_SECURE=false

# LLM Providers
OPENROUTER_API_KEY=your_openrouter_key_here
GOOGLE_API_KEY=your_google_key_here
LLM_TIMEOUT_SECONDS=300
LLM_MAX_RETRIES=3

# Budget Limits
MAX_TOKENS_PER_WORKFLOW=500000
MAX_MONTHLY_BUDGET_USD=20.00
BUDGET_WARNING_THRESHOLD=0.75

# Observability
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
LANGSMITH_API_KEY=your_langsmith_key_here_optional
LANGSMITH_PROJECT=agent-ecosystem

# Security
JWT_SECRET_KEY=your_secret_key_here_generate_with_openssl
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS
CORS_ORIGINS=http://localhost:8080,http://localhost:3000
CORS_ALLOW_CREDENTIALS=true

# Chainlit
CHAINLIT_URL=http://localhost:8080
CHAINLIT_AUTH_SECRET=your_chainlit_secret_here
```

### Required Secrets (DO NOT COMMIT)

1. **OPENROUTER_API_KEY:** Get from https://openrouter.ai/keys
2. **GOOGLE_API_KEY:** Get from https://makersuite.google.com/app/apikey
3. **JWT_SECRET_KEY:** Generate with `openssl rand -hex 32`
4. **CHAINLIT_AUTH_SECRET:** Generate with `openssl rand -hex 32`
5. **LANGSMITH_API_KEY:** (Optional) Get from https://smith.langchain.com

---

## Database Setup

### 1. Schema Creation (Automated)

The database schema is created automatically via Alembic migrations.

**Initial Migration:**
```bash
# Generate initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

### 2. Seed Data (Optional)

```bash
# Run seed script
python scripts/seed_data.py
```

### 3. Manual Setup (If Needed)

```sql
-- Create database
CREATE DATABASE agent_db;

-- Create user
CREATE USER agent_user WITH PASSWORD 'secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE agent_db TO agent_user;
```

---

## Service Health Checks

### Health Check Endpoints

| Service | Endpoint | Expected Response | Timeout |
|---------|----------|-------------------|---------|
| FastAPI | http://localhost:8000/health | 200 OK | 10s |
| PostgreSQL | pg_isready -U postgres | accepting connections | 5s |
| Redis | redis-cli ping | PONG | 5s |
| MinIO | http://localhost:9000/minio/health/live | 200 OK | 20s |
| Prometheus | http://localhost:9090/-/healthy | 200 OK | 10s |
| Grafana | http://localhost:3000/api/health | 200 OK | 10s |
| Chainlit | http://localhost:8080/ | 200 OK | 10s |

### Health Check Script

```bash
#!/bin/bash
# scripts/health_check.sh

echo "Checking service health..."

# FastAPI
curl -f http://localhost:8000/health || echo "❌ FastAPI unhealthy"

# PostgreSQL
pg_isready -h localhost -U postgres || echo "❌ PostgreSQL unhealthy"

# Redis
redis-cli ping || echo "❌ Redis unhealthy"

# MinIO
curl -f http://localhost:9000/minio/health/live || echo "❌ MinIO unhealthy"

echo "✅ Health check complete"
```

---

## Initialization Steps

### 1. Infrastructure Provisioning
- **Action:** Start all services with Docker Compose
- **Command:** `docker-compose up -d`
- **Verification:** Check `docker-compose ps` - all services should be "Up
  (healthy)"

### 2. Database Migration
- **Action:** Apply database schema
- **Command:** `alembic upgrade head`
- **Verification:** Check `alembic current` - should show latest revision

### 3. Seed Data (Optional)
- **Action:** Populate initial data
- **Command:** `python scripts/seed_data.py`
- **Verification:** Query database to confirm data exists

### 4. Service Connectivity
- **Action:** Verify all services are reachable
- **Command:** `bash scripts/health_check.sh`
- **Verification:** All health checks pass

---

## Developer Guide

See DEVELOPER_GUIDE.md for complete setup instructions.

### Quick Start

```bash
# 1. Clone repository
git clone <repository_url>
cd <project_name>

# 2. Copy environment template
cp .env.example .env
# Edit .env and add your API keys

# 3. Start infrastructure
docker-compose up -d

# 4. Wait for services to be healthy
docker-compose ps

# 5. Run database migrations
alembic upgrade head

# 6. Run application
python -m uvicorn src.main:app --reload

# 7. Access services
# - API: http://localhost:8000
# - UI: http://localhost:8080
# - Grafana: http://localhost:3000
# - Prometheus: http://localhost:9090
```

### Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f app

# Run tests
pytest

# Run linter
ruff check src/

# Format code
black src/

# Type check
mypy src/
```

---

## Troubleshooting

### Issue: PostgreSQL connection refused
**Solution:** Ensure PostgreSQL container is healthy
```bash
docker-compose ps postgres
docker-compose logs postgres
```

### Issue: MinIO bucket not found
**Solution:** Create bucket manually
```bash
docker exec -it minio mc mb /data/agent-artifacts
```

### Issue: Port already in use
**Solution:** Change port in docker-compose.yml or stop conflicting service
```bash
lsof -i :8000
kill -9 <PID>
```

---

## Validation Checklist

- [ ] All services defined in docker-compose.yml
- [ ] Health checks configured for each service
- [ ] Environment variables documented in .env.example
- [ ] Database initialization scripts created
- [ ] Service connectivity verified
- [ ] Resource limits set
- [ ] Networks and volumes configured
- [ ] Developer guide complete
```

## Guidelines

1. **Complete Configuration:** Include all services from ARCHITECTURE.md
2. **Health Checks:** Every service must have a health check
3. **Resource Limits:** Set CPU and memory limits for stability
4. **Security:** Never commit secrets, use .env.example template
5. **Documentation:** DEVELOPER_GUIDE.md should enable immediate onboarding
6. **Validation:** Test that docker-compose up works end-to-end

## Respond with the complete INFRASTRUCTURE.md content
"""

        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        _state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse LLM response and extract INFRASTRUCTURE.md content.

        Args:
            response: LLM response with infrastructure configuration
            state: Current workflow state

        Returns:
            Parsed infrastructure config with validation
        """
        # Extract content
        content = response.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```markdown"):
            content = content.split("```markdown")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()

        # Validate that essential sections exist
        required_sections = [
            "# Infrastructure Setup",
            "## Services",
            "## Docker Compose Configuration",
            "## Environment Variables",
        ]

        missing_sections = [
            section for section in required_sections if section not in content
        ]

        if missing_sections:
            # Log warning but don't fail
            pass

        # Write INFRASTRUCTURE.md file
        await self._write_file("INFRASTRUCTURE.md", content)

        return {
            "infrastructure": content,
            "infrastructure_generated": True,
            "infrastructure_token_count": response.tokens_used,
            "services_count": content.count("### "),  # Approximate service count
        }

    def _get_temperature(self) -> float:
        """Use low temperature for precise infrastructure configuration.

        Returns:
            Temperature value (0.3 for structured, factual output)
        """
        return 0.3
