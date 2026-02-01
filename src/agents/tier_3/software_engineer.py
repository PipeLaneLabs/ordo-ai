"""Software Engineer Agent (Tier 3).

Implements production-quality code based on TASKS.md specifications.
Handles code generation, bug fixes, and migration management.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.agents.base_agent import BaseAgent
from src.llm.base_client import LLMResponse
from src.orchestration.state import WorkflowState


class SoftwareEngineerAgent(BaseAgent):
    """Software Engineer Agent (Tier 3).

    Responsibilities:
    - Implements production-quality code based on TASKS.md
    - Follows ARCHITECTURE.md coding standards
    - Incorporates OBSERVABILITY.md instrumentation
    - Handles rejection feedback from Static Analysis, Quality Engineer,
      Security Validator
    - Generates database migrations (alembic) when models change
    - Updates seed/test data scripts to match schema changes
    - Verifies migration reversibility

    Strict Output Constraints:
    - ✅ ONLY creates source code files (.py, .js, .java, etc.)
    - ✅ Inline code comments (docstrings, // comments)
    - ✅ Configuration files (.env.example, config.yaml)
    - ❌ NEVER creates README.md, ARCHITECTURE.md, deployment guides, API docs

    Attributes:
        name: Agent name ("SoftwareEngineerAgent")
        llm_client: LLM provider client (DeepSeek-V3.2 recommended)
        budget_guard: Budget tracking and enforcement
        settings: Application settings
        token_budget: 16,000 tokens (highest allocation)
    """

    async def _build_prompt(self, state: WorkflowState, **_kwargs: object) -> str:
        """Build prompt for code generation.

        Reads project context from TASKS.md, ARCHITECTURE.md, DEPENDENCIES.md,
        and OBSERVABILITY.md. Incorporates feedback from previous rejections.

        Args:
            state: Current workflow state
            **kwargs: Additional parameters (current_task_id, feedback_type, etc.)

        Returns:
            Formatted prompt string for LLM
        """
        # Read project context files
        tasks = await self._read_if_exists("TASKS.md") or "TASKS.md not found."
        architecture = (
            await self._read_if_exists("ARCHITECTURE.md")
            or "ARCHITECTURE.md not found."
        )
        dependencies = (
            await self._read_if_exists("DEPENDENCIES.md")
            or "DEPENDENCIES.md not found."
        )
        observability = (
            await self._read_if_exists("OBSERVABILITY.md")
            or "OBSERVABILITY.md not found."
        )

        # Read rejection feedback if available
        compliance_log = await self._read_if_exists("COMPLIANCE_LOG.md") or ""
        quality_report = await self._read_if_exists("QUALITY_REPORT.md") or ""
        security_report = await self._read_if_exists("SECURITY_REPORT.md") or ""
        deviation_log = await self._read_if_exists("DEVIATION_LOG.md") or ""

        # Extract state information
        current_task_id = state.get("current_task_id")
        feedback = state.get("feedback", "")
        rejection_count = state.get("rejection_count", 0)
        rejected_by = state.get("rejected_by", "")

        # Build context-aware prompt
        prompt = f"""You are the Software Engineer Agent (Tier 3).

Your mission is to implement production-quality code that passes all quality gates.

## Project Context

### TASKS.md
{tasks}

### ARCHITECTURE.md (Coding Standards)
{architecture}

### DEPENDENCIES.md
{dependencies}

### OBSERVABILITY.md (Instrumentation Requirements)
{observability}

## Current Task
Task ID: {current_task_id if current_task_id else "Identify next pending task"}
Rejection Count: {rejection_count}
{f"Rejected By: {rejected_by}" if rejected_by else ""}

## Rejection Feedback (if any)

### Static Analysis Feedback
{compliance_log if compliance_log else "No static analysis feedback yet."}

### Quality Engineer Feedback
{quality_report if quality_report else "No quality feedback yet."}

### Security Validator Feedback
{security_report if security_report else "No security feedback yet."}

### Deviation Handler Feedback
{deviation_log if deviation_log else "No deviation feedback yet."}

### General Feedback
{feedback if feedback else "No general feedback."}

## Coding Standards (MANDATORY)

1. **Type Hints:** All functions MUST have type hints for arguments and return values
2. **Docstrings:** Google-style docstrings for all classes and public functions
3. **Error Handling:** Comprehensive try/except with custom exceptions
4. **Async/Await:** All I/O operations MUST be async (database, LLM, file
   I/O, HTTP)
5. **No Placeholders:** Implement full logic, no TODO comments or pass
   statements
6. **Observability:** Include structured logging per OBSERVABILITY.md
7. **Max Line Length:** 100 characters
8. **Max Function Length:** 50 lines
9. **Max Cyclomatic Complexity:** 10

## Observability Instrumentation (REQUIRED)

Every function that performs I/O or business logic MUST include:
- Structured logging with trace_id and workflow_id
- Prometheus metrics (counters, histograms, gauges)
- OpenTelemetry spans for distributed tracing
- Error logging with full context

Example:
```python
import structlog
from prometheus_client import Counter, Histogram
from opentelemetry import trace

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)

requests_total = Counter(
    "http_requests_total", "Total requests", ["method", "endpoint"]
)
request_duration = Histogram(
    "http_request_duration_seconds", "Request duration"
)

async def create_user(user_data: UserCreate) -> User:
    with tracer.start_as_current_span("user.create"):
        logger.info("user.create.started", email=user_data.email)
        requests_total.labels(method="POST", endpoint="/users").inc()

        try:
            # Implementation
            user = await db.create_user(user_data)
            logger.info("user.create.success", user_id=user.id)
            return user
        except Exception as e:
            logger.error("user.create.failed", error=str(e), exc_info=True)
            raise
```

## Database Migrations (if models change)

If you modify SQLAlchemy models:
1. Generate migration: `alembic revision --autogenerate -m "description"`
2. Review and edit the generated migration file
3. Test upgrade: `alembic upgrade head`
4. Test downgrade: `alembic downgrade -1`
5. Update seed data scripts to match new schema

## Output Format

Provide code in markdown code blocks with filenames:

```python:src/module/file.py
# File content here
```

```python:migrations/versions/001_initial_schema.py
# Migration file if needed
```

## Rejection Handling Strategy

If this is a fix iteration:
- **Static Analysis Rejection:** Fix linting, type errors, complexity
  violations (targeted fixes only)
- **Quality Engineer Rejection:** Fix bugs identified by failing tests
- **Security Validator Rejection:** Remediate vulnerabilities
- **Deviation Handler Rejection:** Address root cause analysis findings

IMPORTANT: Make targeted fixes to specific lines/functions. Do NOT
regenerate entire files.

## Escalation Conditions

Escalate to Solution Architect (via Deviation Handler) if:
- Technical constraint cannot be solved
- Requirement is impossible to implement
- Dependency conflict blocks implementation
- Architectural flaw discovered

Begin implementation now.
"""
        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        _state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse LLM output and write code files.

        Extracts code blocks from LLM response, validates file paths,
        and writes files to disk.

        Args:
            response: LLM response object containing generated code
            state: Current workflow state

        Returns:
            Dictionary with:
                - files_created: List of file paths created
                - status: "completed" or "no_files_generated"
                - error: Error message if validation failed

        Raises:
            ValueError: If file path validation fails
        """
        content = response.content
        files_created: list[str] = []
        errors: list[str] = []

        # Regex to find code blocks with filenames
        # Matches ```language:filename OR ```filename
        pattern = r"```(?:(\w+):)?([^\n]+)\n(.*?)```"
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            filename = match.group(2).strip()
            code_content = match.group(3)

            # Validate filename
            if not self._is_valid_code_file(filename):
                errors.append(
                    f"Invalid filename: {filename} (path traversal or "
                    "forbidden file type)"
                )
                continue

            try:
                await self._write_file(filename, code_content)
                files_created.append(filename)
            except OSError as e:
                errors.append(f"Failed to write {filename}: {e!s}")

        return {
            "files_created": files_created,
            "status": "completed" if files_created else "no_files_generated",
            "errors": errors if errors else None,
        }

    def _is_valid_code_file(self, filename: str) -> bool:
        """Validate that filename is a safe code file path.

        Checks for:
        - No path traversal (..)
        - No absolute paths
        - Allowed file extensions only
        - No forbidden file types (README.md, ARCHITECTURE.md, etc.)

        Args:
            filename: File path to validate

        Returns:
            True if valid code file, False otherwise
        """
        # Forbidden file types (per Software Engineer constraints)
        forbidden_files = {
            "README.md",
            "ARCHITECTURE.md",
            "DEPLOYMENT.md",
            "API_REFERENCE.md",
            "TROUBLESHOOTING.md",
            "CONTRIBUTING.md",
        }

        # Check for path traversal
        if ".." in filename or filename.startswith("/"):
            return False

        # Check for forbidden files
        file_path = Path(filename)
        if file_path.name in forbidden_files:
            return False

        # Allow only code files and configuration files
        allowed_extensions = {
            # Code files
            ".py",
            ".js",
            ".ts",
            ".java",
            ".go",
            ".rs",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            # Configuration files
            ".yaml",
            ".yml",
            ".json",
            ".toml",
            ".ini",
            ".env",
            ".example",
            # Database migrations
            ".sql",
            # Shell scripts
            ".sh",
            ".bash",
            # Package files
            ".txt",  # requirements.txt, etc.
        }

        # Check if file has allowed extension
        return not (
            file_path.suffix
            and file_path.suffix not in allowed_extensions
            and not filename.endswith(".env.example")
        )

    def _get_temperature(self) -> float:
        """Get LLM temperature for code generation.

        Software Engineer uses low temperature (0.2) for:
        - Precise, deterministic code generation
        - Consistent coding style
        - Reduced hallucinations

        Returns:
            Temperature value: 0.2 (low for precision)
        """
        return 0.2

    def _estimate_cost(self) -> float:
        """Estimate cost for Software Engineer execution.

        Uses DeepSeek-V3.2 (PAID model) with highest token budget.
        Rough estimate: $1 per 1M tokens.

        Returns:
            Estimated cost in USD
        """
        # Software Engineer has 16,000 token budget (highest allocation)
        # DeepSeek-V3.2: ~$1 per 1M tokens
        return (self.token_budget / 1_000_000) * 1.0
