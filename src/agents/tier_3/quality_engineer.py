"""Quality Engineer Agent (Tier 3).

Ensures code correctness through comprehensive testing.
Generates unit, integration, and e2e tests with coverage analysis.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from venv import logger

from src.agents.base_agent import BaseAgent
from src.llm.base_client import LLMResponse
from src.orchestration.state import WorkflowState


class QualityEngineerAgent(BaseAgent):
    """Quality Engineer Agent (Tier 3).

    Responsibilities:
    - Generates unit, integration, and e2e tests (phase-wise)
    - Executes tests with pytest and coverage analysis
    - Generates QUALITY_REPORT.md with detailed results
    - Ensures code coverage meets 70% threshold
    - Identifies bugs and code quality issues
    - Provisions and tears down test databases/environments
    - Tests edge cases and failure scenarios
    - Phase Isolation: Generates mocks for future dependencies

    Testing Standards:
    - Minimum coverage: 70%
    - Unit tests for all public functions
    - Integration tests for API endpoints
    - E2E tests for critical user flows
    - Security tests for auth/authorization
    - Mocking Policy: Mandatory mocking for unavailable dependencies

    Attributes:
        name: Agent name ("QualityEngineerAgent")
        llm_client: LLM provider client (DeepSeek-V3.2 recommended)
        budget_guard: Budget tracking and enforcement
        settings: Application settings
        token_budget: 12,000 tokens
    """

    _last_pytest_run_at: float | None = None

    async def _build_prompt(self, state: WorkflowState, **_kwargs: object) -> str:
        """Build prompt with code context and requirements.

        Reads source code, REQUIREMENTS.md, ARCHITECTURE.md, and TASKS.md
        to generate comprehensive test suites.

        Args:
            state: Current workflow state
            **kwargs: Additional parameters

        Returns:
            Formatted prompt string for LLM
        """
        # Read project context
        src_context = await self._read_src_files()
        requirements = (
            await self._read_if_exists("REQUIREMENTS.md")
            or "REQUIREMENTS.md not found."
        )
        architecture = (
            await self._read_if_exists("ARCHITECTURE.md")
            or "ARCHITECTURE.md not found."
        )
        tasks = await self._read_if_exists("TASKS.md") or "TASKS.md not found."

        # Read existing test files to avoid duplication
        existing_tests = await self._read_existing_tests()

        # Extract state information
        current_phase = state.get("current_phase", "unknown")
        rejection_count = state.get("rejection_count", 0)

        prompt = f"""You are the Quality Engineer Agent (Tier 3).

Your mission is to ensure code correctness through comprehensive testing.

## Project Context

### REQUIREMENTS.md (Acceptance Criteria)
{requirements}

### ARCHITECTURE.md (System Design)
{architecture}

### TASKS.md (Implementation Plan)
{tasks}

### Source Code to Test
{src_context}

### Existing Tests (Avoid Duplication)
{existing_tests if existing_tests else "No existing tests found."}

## Current Phase
Phase: {current_phase}
Rejection Count: {rejection_count}

## Testing Requirements

### 1. Unit Tests (tests/unit/)
- Test all public functions and methods
- Test edge cases and boundary conditions
- Test error handling and exceptions
- Use `pytest.mark.asyncio` for async functions
- Mock external dependencies (DB, LLM, Redis, MinIO)
- Follow Arrange-Act-Assert pattern
- Target: 70%+ code coverage

### 2. Integration Tests (tests/integration/)
- Test tier transitions and agent interactions
- Test API endpoints with FastAPI TestClient
- Test database operations with test database
- Test checkpoint persistence and recovery
- Mock LLM calls to avoid API costs

### 3. End-to-End Tests (tests/e2e/)
- Test critical user flows (happy path)
- Test complete workflow execution
- Use mocks for external services
- Verify all primary files created

### 4. Mocking Strategy (Phase Isolation)
- If code depends on future phase artifacts, generate mocks immediately
- Mock unavailable dependencies (e.g., MockAgent for Controller testing)
- Do NOT defer testing - verify logic now with mocks

## Coding Standards for Tests

1. **Type Hints:** All test functions MUST have type hints
2. **Docstrings:** Clear test descriptions
3. **Fixtures:** Use pytest fixtures for reusable setup (conftest.py)
4. **Assertions:** Use descriptive assertion messages
5. **Coverage:** Aim for 70%+ coverage
6. **Performance:** Mark slow tests with `@pytest.mark.slow`
7. **Isolation:** Each test should be independent

## Test File Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_config.py       # Unit tests for config
│   ├── test_budget_guard.py # Unit tests for budget guard
│   └── ...
├── integration/
│   ├── test_checkpoint_manager.py
│   ├── test_llm_clients.py
│   └── ...
└── e2e/
    └── test_full_workflow.py
```

## Example Test (Unit Test)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.config import Settings

@pytest.mark.asyncio
async def test_budget_guard_reserve_budget() -> None:
    \"\"\"Test budget reservation within limits.\"\"\"
    # Arrange
    settings = Settings(max_tokens_per_workflow=100000)
    budget_guard = BudgetGuard(settings)
    state = {{"workflow_id": "test-001", "tokens_used": 0}}
    # Act
    budget_guard.reserve_budget(
        operation_name="test_operation",
        estimated_tokens=5000,
        estimated_cost_usd=0.005,
        workflow_state=state
    )
    # Assert
    assert state["tokens_reserved"] == 5000
    assert state["cost_reserved_usd"] == 0.005
```

## Example Test (Integration Test)

```python
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.mark.integration
def test_workflow_start_endpoint() -> None:
    \"\"\"Test POST /workflow/start endpoint.\"\"\"
    # Arrange
    client = TestClient(app)
    request_data = {{
        "user_request": "Create a simple FastAPI hello world endpoint"
    }}

    # Act
    response = client.post("/workflow/start", json=request_data)

    # Assert
    assert response.status_code == 200
    assert "workflow_id" in response.json()
```

## Output Format

Provide test files in markdown code blocks:

```python:tests/unit/test_filename.py
# Test file content
```

```python:tests/integration/test_filename.py
# Test file content
```

```python:tests/e2e/test_filename.py
# Test file content
```

```python:tests/conftest.py
# Shared fixtures
```

## Important Notes

- Generate tests for ALL public functions in the source code
- Include both positive and negative test cases
- Mock external dependencies to avoid API costs
- Ensure tests are deterministic (no random failures)
- Follow pytest best practices
- Target 70%+ code coverage

Begin test generation now.
"""
        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        _state: WorkflowState,
    ) -> dict[str, Any]:
        """Save tests, run execution, and generate report.

        Extracts test files from LLM response, saves them, executes pytest,
        and generates QUALITY_REPORT.md.

        Args:
            response: LLM response object containing generated tests
            state: Current workflow state

        Returns:
            Dictionary with:
                - files_created: List of test files created
                - test_results: Pytest execution results
                - coverage_percent: Code coverage percentage
                - report_generated: Boolean
                - status: "APPROVED" or "REJECTED"
        """
        content = response.content
        files_created: list[str] = []

        # 1. Save Test Files
        pattern = r"```(?:(\w+):)?([^\n]+)\n(.*?)```"
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            filename = match.group(2).strip()
            code_content = match.group(3)

            # Only save test files
            if filename.startswith("tests/") and filename.endswith(".py"):
                await self._write_file(filename, code_content)
                files_created.append(filename)

        # 2. Run Pytest with Coverage
        test_results = await self._run_pytest()

        # 3. Extract Coverage Percentage
        coverage_percent = self._extract_coverage(test_results)

        # 4. Generate Quality Report
        report = self._generate_quality_report(
            test_results, files_created, coverage_percent
        )
        await self._write_file("QUALITY_REPORT.md", report)

        # 5. Determine Status
        status = (
            "APPROVED"
            if self._is_approved(test_results, coverage_percent)
            else "REJECTED"
        )

        return {
            "files_created": files_created,
            "test_results": test_results,
            "coverage_percent": coverage_percent,
            "report_generated": True,
            "status": status,
        }

    async def _read_src_files(self) -> str:
        """Read all relevant source files for test generation.

        Recursively reads Python files from src/ directory.
        Limits context to avoid token overflow.

        Returns:
            Concatenated source code context
        """
        context = ""
        file_count = 0
        max_files = 50  # Limit to avoid token overflow

        for root, _, files in os.walk("src"):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    if file_count >= max_files:
                        context += "\n... (truncated, too many files)\n"
                        return context

                    from pathlib import Path

                    path = Path(root) / file
                    try:
                        async with self._open_file_async(str(path)) as f:
                            content = await f.read()
                            context += (
                                f"\n### File: {path}\n```python\n{content}\n```\n"
                            )
                            file_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to process file: {e}")

        return context

    async def _read_existing_tests(self) -> str:
        """Read existing test files to avoid duplication.

        Returns:
            Concatenated existing test files
        """
        context = ""
        tests_dir = Path("tests")

        if not tests_dir.exists():
            return ""

        for test_file in tests_dir.rglob("test_*.py"):
            try:
                async with self._open_file_async(str(test_file)) as f:
                    content = await f.read()
                    context += (
                        f"\n### Existing Test: {test_file}\n```python\n{content}\n```\n"
                    )
            except Exception as e:
                logger.warning(f"Failed to process file: {e}")

        return context

    def _open_file_async(self, path: str) -> Any:
        """Open file asynchronously for reading.

        Args:
            path: File path

        Returns:
            Async file handle
        """
        import aiofiles

        return aiofiles.open(path, encoding="utf-8")

    async def _run_pytest(self) -> dict[str, Any]:
        """Run pytest with coverage and capture output.

        Returns:
            Dictionary with return_code, stdout, stderr
        """
        cmd = "pytest tests/ --cov=src --cov-report=term-missing --cov-report=json -v"
        self._last_pytest_run_at = time.monotonic()
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            return {
                "return_code": process.returncode or 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
        except Exception as e:
            return {
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
            }

    def _extract_coverage(self, results: dict[str, Any]) -> float:
        """Extract coverage percentage from pytest output.

        Args:
            results: Pytest execution results

        Returns:
            Coverage percentage (0-100)
        """
        stdout = results.get("stdout", "")

        # Try to parse from coverage report
        # Format: "TOTAL    1234    567    54%"
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", stdout)
        if match:
            return float(match.group(1))

        if self._last_pytest_run_at is None:
            return 0.0

        # Try JSON coverage report
        try:
            import json

            with Path("coverage.json").open() as f:
                coverage_data = json.load(f)
                return float(
                    coverage_data.get("totals", {}).get("percent_covered", 0.0)
                )
        except Exception as e:
            logger.warning(f"Failed to read coverage.json: {e}")

        return 0.0

    def _is_approved(self, results: dict[str, Any], coverage: float) -> bool:
        """Determine if tests pass quality gate.

        Args:
            results: Pytest execution results
            coverage: Code coverage percentage

        Returns:
            True if approved, False if rejected
        """
        # Approve if:
        # 1. All tests pass (return code 0)
        # 2. Coverage >= 70%
        return results["return_code"] == 0 and coverage >= 70.0

    def _generate_quality_report(
        self,
        results: dict[str, Any],
        new_tests: list[str],
        coverage: float,
    ) -> str:
        """Generate markdown quality report.

        Args:
            results: Pytest execution results
            new_tests: List of new test files created
            coverage: Code coverage percentage

        Returns:
            Markdown report content
        """
        status = "✅ PASSED" if results["return_code"] == 0 else "❌ FAILED"
        coverage_status = "✅ PASSED" if coverage >= 70.0 else "❌ FAILED"

        return f"""# Quality Report

**Generated:** {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")}
**Status:** {status}

## Test Execution Summary

- **Return Code:** {results['return_code']}
- **New Tests Created:** {len(new_tests)}
- **Coverage:** {coverage:.1f}% {coverage_status} (threshold: 70%)

## Test Output

### Stdout
```
{results['stdout']}
```

### Stderr
```
{results['stderr']}
```

## Generated Test Files

{chr(10).join(f'- {f}' for f in new_tests)}

## Quality Gate Status

- {'✅' if results['return_code'] == 0 else '❌'} Test pass rate: {
    '100%' if results['return_code'] == 0 else 'FAILED'}
- {'✅' if coverage >= 70.0 else '❌'} Coverage threshold: {
    coverage:.1f}% (target: 70%)

**Overall:** {'✅ APPROVED' if self._is_approved(results, coverage) else '❌ REJECTED'}

{
    '**Reason:** Tests failed or coverage below threshold'
    if not self._is_approved(results, coverage)
    else ''
}
{
    '**Route to:** Software Engineer (fix bugs) or Quality Engineer (fix tests)'
    if not self._is_approved(results, coverage)
    else ''
}
"""

    def _get_temperature(self) -> float:
        """Get LLM temperature for test generation.

        Quality Engineer uses moderate temperature (0.3) for:
        - Creative test case generation
        - Edge case discovery
        - Balanced determinism and creativity

        Returns:
            Temperature value: 0.3
        """
        return 0.3
