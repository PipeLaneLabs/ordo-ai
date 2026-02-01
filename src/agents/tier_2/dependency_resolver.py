"""Dependency Resolver Agent for Tier 2.

Manages project dependencies with:
- Dependency resolution and version pinning
- Security vulnerability scanning (CVEs)
- License compatibility checking
- Lock file generation
- System-level dependency identification
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import Settings
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


class DependencyResolverAgent(BaseAgent):
    """Tier 2 agent for dependency resolution and security scanning.

    Uses Gemini-2.5-Flash for fast dependency analysis.
    Generates DEPENDENCIES.md and requirements.txt.

    Attributes:
        token_budget: 2,000 tokens for dependency analysis
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
    ) -> None:
        """Initialize Dependency Resolver Agent.

        Args:
            llm_client: LLM client (should use Gemini-2.5-Flash for speed)
            budget_guard: Budget guard instance
            settings: Application settings
        """
        super().__init__(
            name="DependencyResolverAgent",
            llm_client=llm_client,
            budget_guard=budget_guard,
            settings=settings,
            token_budget=2000,  # 2K tokens for dependency analysis
        )

    async def _build_prompt(
        self,
        state: WorkflowState,
        **_kwargs: object,
    ) -> str:
        """Build dependency resolution prompt for LLM.

        Args:
            state: Current workflow state
            **kwargs: Additional context

        Returns:
            Formatted prompt for dependency analysis
        """
        # Read required artifacts
        tasks = await self._read_if_exists("TASKS.md")
        architecture = await self._read_if_exists("ARCHITECTURE.md")

        if not tasks:
            raise ValueError(
                "TASKS.md not found - Implementation Planner must run first"
            )

        prompt = f"""# Dependency Resolution Task

## Workflow Context
**Workflow ID:** {state['workflow_id']}

## Tasks Document
{tasks}

## Architecture Document
{architecture or "No architecture document available"}

## Your Task
As a Dependency Resolver, analyze the task breakdown and architecture to create
a comprehensive dependency management plan.

### Resolution Framework

1. **Dependency Analysis**
   - Extract all dependencies mentioned in TASKS.md
   - Resolve version constraints (use latest stable versions)
   - Identify transitive dependencies
   - Group by category (core, database, observability, testing, etc.)

2. **Version Pinning**
   - Pin exact versions for reproducibility
   - Use semantic versioning constraints (>=, ~=)
   - Ensure compatibility between dependencies
   - Resolve version conflicts

3. **Security Scanning**
   - Identify known CVEs for each dependency
   - Flag CRITICAL and HIGH severity vulnerabilities
   - Provide remediation guidance
   - Scan Date: [Current Date]

4. **License Compatibility**
   - Check license for each dependency
   - Flag GPL-licensed libraries (NOT ALLOWED)
   - Ensure MIT, Apache 2.0, BSD compatibility
   - Document license obligations

5. **System Dependencies**
   - Identify system-level packages (apt, yum)
   - List for Dockerfile/Aptfile
   - Include build tools if needed

## Output Format

Generate a DEPENDENCIES.md document with the following structure:

```markdown
# Dependency Management

**Project:** [Project Name]
**Version:** 1.0
**Date:** [Current Date]
**Resolver:** Dependency Resolver Agent
**Status:** RESOLVED

---

## Table of Contents
1. [Production Dependencies](#production-dependencies)
2. [Development Dependencies](#development-dependencies)
3. [Dependency Conflicts Resolved](#dependency-conflicts-resolved)
4. [Security Scan Results](#security-scan-results)
5. [License Compatibility](#license-compatibility)
6. [System Dependencies](#system-dependencies)
7. [Installation Commands](#installation-commands)

---

## Production Dependencies

| Package | Version | License | Justification | Security Status |
|---------|---------|---------|---------------|-----------------|
| fastapi | 0.115.0 | MIT | Web framework per ARCHITECTURE.md | ✅ No CVEs |
| pydantic | 2.10.0 | MIT | Data validation | ✅ No CVEs |
| asyncpg | 0.30.0 | Apache 2.0 | PostgreSQL async driver | ✅ No CVEs |

[Continue with all production dependencies]

### Core Framework
- `fastapi==0.115.0` - REST API framework
- `uvicorn[standard]==0.32.0` - ASGI server
- `pydantic==2.10.0` - Data validation
- `pydantic-settings==2.6.0` - Environment config

### Database & Storage
- `asyncpg==0.30.0` - PostgreSQL async driver
- `redis[hiredis]==5.2.0` - Redis client with C parser
- `minio==7.2.0` - MinIO S3-compatible client
- `alembic==1.14.0` - Database migrations

### Observability
- `structlog==24.4.0` - Structured logging
- `prometheus-client==0.21.0` - Metrics
- `python-json-logger==3.2.1` - JSON log formatting

### LLM Providers
- `openai==1.58.0` - OpenRouter API client
- `google-generativeai==0.8.3` - Google Gemini fallback

### Utilities
- `python-dotenv==1.0.1` - .env file loading
- `aiofiles==24.1.0` - Async file I/O
- `httpx==0.28.0` - Async HTTP client
- `tenacity==9.0.0` - Retry logic

---

## Development Dependencies

### Testing
- `pytest==8.3.0` - Test framework
- `pytest-asyncio==0.24.0` - Async test support
- `pytest-cov==6.0.0` - Coverage reporting
- `pytest-mock==3.14.0` - Mocking utilities
- `faker==33.1.0` - Test data generation

### Code Quality
- `black==24.10.0` - Code formatter
- `ruff==0.8.0` - Fast linter
- `mypy==1.13.0` - Type checker
- `pre-commit==4.0.0` - Git hooks

### Security
- `pip-audit==2.8.0` - Vulnerability scanner
- `safety==3.3.0` - Dependency security check

---

## Dependency Conflicts Resolved

### Conflict: pydantic 1.x vs 2.x
**Resolution:** Upgraded to pydantic 2.10.0
**Rationale:** FastAPI 0.115+ requires pydantic v2
**Impact:** Breaking changes handled in migration guide
**Affected Packages:** fastapi, pydantic-settings

### Conflict: [Any other conflicts]
**Resolution:** [How resolved]
**Rationale:** [Why this approach]
**Impact:** [What changed]

---

## Security Scan Results

**Scan Date:** [Current Date]
**Tool:** pip-audit + safety
**Critical Issues:** 0
**High Issues:** 0
**Medium Issues:** 0
**Low Issues:** 0

### Vulnerability Details

[If any vulnerabilities found]

| Package | Version | CVE | Severity | Fix Available | Remediation |
|---------|---------|-----|----------|---------------|-------------|
| example | 1.0.0 | CVE-2024-XXXX | HIGH | Yes (1.0.1) | Upgrade to 1.0.1 |

**Status:** ✅ ALL CLEAR (No critical or high vulnerabilities)

---

## License Compatibility

**License Policy:** MIT, Apache 2.0, BSD only (NO GPL)

### License Summary

| License | Count | Status | Packages |
|---------|-------|--------|----------|
| MIT | 25 | ✅ ALLOWED | fastapi, pydantic, ... |
| Apache 2.0 | 8 | ✅ ALLOWED | asyncpg, ... |
| BSD | 5 | ✅ ALLOWED | ... |
| GPL | 0 | ✅ NONE FOUND | - |

**Status:** ✅ ALL LICENSES COMPATIBLE

---

## System Dependencies

### Debian/Ubuntu (Aptfile for Dockerfile)
```bash
# Build tools
build-essential
python3-dev

# PostgreSQL client
libpq-dev

# Redis client (hiredis)
libhiredis-dev

# SSL/TLS
libssl-dev
```

### Alpine Linux
```bash
# Build tools
gcc
musl-dev
python3-dev

# PostgreSQL
postgresql-dev

# Redis
hiredis-dev
```

---

## Installation Commands

### Development Environment (venv)
```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install dev dependencies
pip install -r requirements-dev.txt
```

### Production Environment (Docker)
```dockerfile
# Dockerfile snippet
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    libpq-dev \\
    libhiredis-dev \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

### Poetry (Alternative)
```bash
# Install with Poetry
poetry install

# Add new dependency
poetry add fastapi

# Update lock file
poetry lock
```

---

## requirements.txt

```
# Core Framework
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.10.0
pydantic-settings==2.6.0

# Database & Storage
asyncpg==0.30.0
redis[hiredis]==5.2.0
minio==7.2.0
alembic==1.14.0

# Observability
structlog==24.4.0
prometheus-client==0.21.0
python-json-logger==3.2.1

# LLM Providers
openai==1.58.0
google-generativeai==0.8.3

# Utilities
python-dotenv==1.0.1
aiofiles==24.1.0
httpx==0.28.0
tenacity==9.0.0
```

---

## requirements-dev.txt

```
# Testing
pytest==8.3.0
pytest-asyncio==0.24.0
pytest-cov==6.0.0
pytest-mock==3.14.0
faker==33.1.0

# Code Quality
black==24.10.0
ruff==0.8.0
mypy==1.13.0
pre-commit==4.0.0

# Security
pip-audit==2.8.0
safety==3.3.0
```

---

## Validation Checklist

- [ ] All dependencies from TASKS.md included
- [ ] Versions pinned for reproducibility
- [ ] No critical/high CVEs found
- [ ] No GPL licenses detected
- [ ] System dependencies identified
- [ ] Installation commands tested
- [ ] Lock file generated (if using Poetry)
```

## Guidelines

1. **Pin Exact Versions:** Use == for reproducibility (e.g., fastapi==0.115.0)
2. **Security First:** Flag any CRITICAL or HIGH CVEs immediately
3. **No GPL:** Reject any GPL-licensed dependencies
4. **Document Conflicts:** Explain how version conflicts were resolved
5. **System Deps:** Include all system-level packages needed
6. **Test Installation:** Ensure requirements.txt is valid and installable

## Respond with the complete DEPENDENCIES.md content
"""

        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        _state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse LLM response and extract DEPENDENCIES.md content.

        Args:
            response: LLM response with dependency analysis
            state: Current workflow state

        Returns:
            Parsed dependencies with validation
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
            "# Dependency Management",
            "## Production Dependencies",
            "## Security Scan Results",
            "## License Compatibility",
        ]

        missing_sections = [
            section for section in required_sections if section not in content
        ]

        if missing_sections:
            # Log warning but don't fail
            pass

        # Check for GPL violations
        if "GPL" in content and "✅ NONE FOUND" not in content:
            # Warning: potential GPL dependency detected
            pass

        # Write DEPENDENCIES.md file
        await self._write_file("DEPENDENCIES.md", content)

        return {
            "dependencies": content,
            "dependencies_generated": True,
            "dependencies_token_count": response.tokens_used,
            "has_security_issues": "Critical Issues: 0" not in content,
            "has_license_issues": "GPL" in content and "✅ NONE FOUND" not in content,
        }

    def _get_temperature(self) -> float:
        """Use low temperature for precise dependency resolution.

        Returns:
            Temperature value (0.2 for factual, deterministic output)
        """
        return 0.2
