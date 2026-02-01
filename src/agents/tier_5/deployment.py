"""Deployment Agent (Tier 5).

Finalizes deployment configuration including production Dockerfile,
docker-compose.yml, and CI/CD pipeline configurations.
"""

from __future__ import annotations

import re
from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import Settings
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


class DeploymentAgent(BaseAgent):
    """Deployment Agent (Tier 5).

    Responsibilities:
    - Generate production-ready Dockerfile with multi-stage builds
    - Finalize docker-compose.yml with all services
    - Generate GitHub Actions workflows for CI/CD
    - Create deployment scripts and configurations

    Primary Outputs:
    - docker/Dockerfile
    - docker/docker-compose.yml
    - .github/workflows/lint-and-test.yml
    - .github/workflows/dependency-scan.yml

    LLM Model: Gemini-2.5-Flash (deployment configuration)
    Token Budget: 4,000 per invocation
    Temperature: 0.1 (deterministic for infrastructure config)
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
    ) -> None:
        """Initialize Deployment Agent.

        Args:
            llm_client: LLM client (should use Gemini-2.5-Flash for config)
            budget_guard: Budget guard instance
            settings: Application settings
        """
        super().__init__(
            name="DeploymentAgent",
            llm_client=llm_client,
            budget_guard=budget_guard,
            settings=settings,
            token_budget=4000,  # 4K tokens for deployment configuration
        )

    async def _build_prompt(
        self,
        state: WorkflowState,  # noqa: ARG002
        **_kwargs: object,
    ) -> str:
        """Build prompt for deployment configuration generation.

        Reads project context from INFRASTRUCTURE.md, ARCHITECTURE.md,
        and DEPENDENCIES.md to generate production-ready deployment configs.

        Args:
            state: Current workflow state
            **kwargs: Additional parameters

        Returns:
            Formatted prompt string for LLM
        """
        # Read project context files
        infrastructure = (
            await self._read_if_exists("INFRASTRUCTURE.md") or "Not available"
        )
        architecture = await self._read_if_exists("ARCHITECTURE.md") or "Not available"
        dependencies = await self._read_if_exists("DEPENDENCIES.md") or "Not available"
        requirements = await self._read_if_exists("REQUIREMENTS.md") or "Not available"

        prompt = f"""# Deployment Configuration Task

You are a DevOps engineer creating production-ready deployment configurations.

## Project Context

### Infrastructure Requirements
{infrastructure}

### Architecture
{architecture}

### Dependencies
{dependencies}

### Requirements
{requirements}

## Your Task

Generate four deployment configuration files with production-grade quality:

### 1. docker/Dockerfile
Create a production-ready multi-stage Dockerfile with:
- Multi-stage build (builder stage + runtime stage)
- Python 3.12 base image
- Dependency installation from requirements.txt
- Non-root user for security
- Health check configuration
- Proper layer caching optimization
- Security best practices (no secrets, minimal attack surface)
- Appropriate EXPOSE directives
- ENTRYPOINT and CMD configuration

**Requirements:**
- Use official Python 3.12 slim image
- Install dependencies in builder stage
- Copy only necessary files to runtime stage
- Set working directory to /app
- Create non-root user (appuser)
- Include HEALTHCHECK instruction

### 2. docker/docker-compose.yml
Create a complete docker-compose.yml with all services:
- FastAPI application service
- Chainlit UI service
- PostgreSQL database
- Redis cache
- MinIO object storage
- Prometheus metrics
- Grafana dashboards

**Requirements:**
- Use version "3.8" or higher
- Define networks for service isolation
- Define volumes for data persistence
- Set environment variables from .env file
- Configure health checks for all services
- Set resource limits (memory, CPU)
- Configure service dependencies
- Expose appropriate ports

### 3. .github/workflows/lint-and-test.yml
Create GitHub Actions workflow for linting and testing:
- Trigger on push and pull_request
- Run on ubuntu-latest
- Python 3.12 setup
- Install dependencies
- Run black (formatting check)
- Run ruff (linting)
- Run mypy (type checking)
- Run pytest with coverage
- Upload coverage reports

**Requirements:**
- Use actions/checkout@v4
- Use actions/setup-python@v5
- Cache pip dependencies
- Fail on any check failure
- Generate coverage report

### 4. .github/workflows/dependency-scan.yml
Create GitHub Actions workflow for security scanning:
- Trigger on schedule (daily) and pull_request
- Run on ubuntu-latest
- Python 3.12 setup
- Install dependencies
- Run pip-audit for vulnerability scanning
- Run safety check
- Report security issues

**Requirements:**
- Use actions/checkout@v4
- Use actions/setup-python@v5
- Fail on high/critical vulnerabilities
- Generate security report

## Output Format

Use XML-like tags to separate the files:

<FILE name="docker/Dockerfile">
[Complete Dockerfile content]
</FILE>

<FILE name="docker/docker-compose.yml">
[Complete docker-compose.yml content]
</FILE>

<FILE name=".github/workflows/lint-and-test.yml">
[Complete GitHub Actions workflow content]
</FILE>

<FILE name=".github/workflows/dependency-scan.yml">
[Complete GitHub Actions workflow content]
</FILE>

## Guidelines

1. **Production-Ready:** All configurations must be production-grade
2. **Security-First:** Follow security best practices
3. **Optimized:** Minimize image size and build time
4. **Documented:** Include comments explaining key decisions
5. **Tested:** Configurations should be immediately usable
6. **Standards-Compliant:** Follow Docker and GitHub Actions best practices

## Important Notes

- Extract actual service names and ports from INFRASTRUCTURE.md
- Use real dependency versions from DEPENDENCIES.md
- Ensure all environment variables are documented
- Include health checks for all services
- Set appropriate resource limits
- Use secrets management for sensitive data

Generate the four deployment configuration files now.
"""

        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        _state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse LLM response and save deployment files.

        Extracts deployment configuration content from XML-like tags
        and writes files to appropriate locations.

        Args:
            response: LLM response containing deployment configuration
            state: Current workflow state

        Returns:
            Dictionary with deployment_files list

        Raises:
            ValueError: If no valid deployment files could be parsed
        """
        content = response.content
        files_created = []

        # XML-like parsing with case-insensitive matching
        pattern = r'<FILE\s+name="(.*?)"\s*>\s*(.*?)\s*</FILE>'
        matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)

        for match in matches:
            filename = match.group(1).strip()
            file_content = match.group(2).strip()
            if file_content:  # Only write non-empty content
                await self._write_file(filename, file_content)
                files_created.append(filename)

        if not files_created:
            raise ValueError(
                "No valid deployment files could be parsed from LLM response. "
                "Expected <FILE name='...'>...</FILE> tags."
            )

        return {
            "deployment_files": files_created,
            "deployment_configured": True,
            "deployment_token_count": response.tokens_used,
        }

    def _get_temperature(self) -> float:
        """Use very low temperature for deterministic deployment config.

        Returns:
            Temperature value (0.1 for maximum consistency)
        """
        return 0.1
