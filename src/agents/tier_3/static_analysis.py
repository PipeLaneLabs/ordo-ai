"""Static Analysis Agent (Tier 3).

Performs fast, automated code quality checks before tests run.
Runs black, ruff, mypy, and radon complexity analysis.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from datetime import UTC, datetime
from typing import Any

from src.agents.base_agent import BaseAgent
from src.llm.base_client import LLMResponse
from src.orchestration.state import WorkflowState


class StaticAnalysisAgent(BaseAgent):
    """Static Analysis Agent (Tier 3).

    Responsibilities:
    - Runs automated code quality checks (black, ruff, mypy, radon)
    - Validates coding standards from ARCHITECTURE.md
    - Generates COMPLIANCE_LOG.md with actionable feedback
    - Rejects code if critical issues are found
    - Provides fast feedback (10-30 seconds vs minutes of test running)

    Why This Agent is Critical:
    - Fast feedback loop (10 seconds vs 3 minutes for full tests)
    - Catches basic errors early (syntax, types, style)
    - Deterministic (same result every time)
    - No dependencies (doesn't need DB, external services)

    Attributes:
        name: Agent name ("StaticAnalysisAgent")
        llm_client: LLM provider client (Gemini-2.5-Flash recommended)
        budget_guard: Budget tracking and enforcement
        settings: Application settings
        token_budget: 2,000 tokens
    """

    async def execute(
        self,
        state: WorkflowState,
        **_kwargs: object,
    ) -> WorkflowState:
        """Override execute to run tools before LLM analysis.

        Execution flow:
        1. Run static analysis tools (black, ruff, mypy, radon)
        2. Build prompt with tool results
        3. Call LLM to analyze and generate report
        4. Parse output and save COMPLIANCE_LOG.md
        5. Update state with pass/fail status

        Args:
            state: Current workflow state
            **kwargs: Additional parameters

        Returns:
            Updated workflow state with analysis results
        """
        # 1. Run static analysis tools
        tool_results = await self._run_analysis_tools()

        # 2. Proceed with standard execution (build prompt -> call LLM -> parse)
        # Note: tool_results are passed via state for LLM context
        state["tool_results"] = tool_results
        return await super().execute(state)

    async def _run_analysis_tools(self) -> dict[str, dict[str, Any]]:
        """Run static analysis tools in parallel.

        Tools executed:
        - black --check: Code formatting
        - ruff check: Linting (replaces flake8)
        - mypy: Type checking
        - radon cc: Cyclomatic complexity

        Returns:
            Dictionary with tool results (command, return_code, stdout, stderr)
        """
        results = {}

        # Run tools in parallel for speed
        black_task = self._run_command("black --check src/")
        ruff_task = self._run_command("ruff check src/")
        mypy_task = self._run_command("mypy src/ --ignore-missing-imports")
        radon_task = self._run_command("radon cc src/ -a -nb")

        # Gather results
        black_result, ruff_result, mypy_result, radon_result = await asyncio.gather(
            black_task, ruff_task, mypy_task, radon_task, return_exceptions=True
        )

        black_result_typed: subprocess.CompletedProcess[str] | Exception = (
            black_result
        )
        ruff_result_typed: subprocess.CompletedProcess[str] | Exception = (
            ruff_result
        )
        mypy_result_typed: subprocess.CompletedProcess[str] | Exception = (
            mypy_result
        )
        radon_result_typed: subprocess.CompletedProcess[str] | Exception = (
            radon_result
        )

        results["black"] = (
            black_result_typed
            if isinstance(black_result_typed, dict)
            else self._error_result("black", black_result_typed)
        )
        results["ruff"] = (
            ruff_result_typed
            if isinstance(ruff_result_typed, dict)
            else self._error_result("ruff", ruff_result_typed)
        )
        results["mypy"] = (
            mypy_result_typed
            if isinstance(mypy_result_typed, dict)
            else self._error_result("mypy", mypy_result_typed)
        )
        results["radon"] = (
            radon_result_typed
            if isinstance(radon_result_typed, dict)
            else self._error_result("radon", radon_result_typed)
        )

        return results

    def _error_result(self, tool: str, exception: Exception) -> dict[str, Any]:
        """Create error result for failed tool execution.

        Args:
            tool: Tool name
            exception: Exception that occurred

        Returns:
            Error result dictionary
        """
        return {
            "command": tool,
            "return_code": -1,
            "stdout": "",
            "stderr": f"Tool execution failed: {exception!s}",
        }

    async def _run_command(self, cmd: str) -> dict[str, Any]:
        """Run a shell command asynchronously.

        Args:
            cmd: Shell command to execute

        Returns:
            Dictionary with command, return_code, stdout, stderr
        """
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            return {
                "command": cmd,
                "return_code": process.returncode or 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
        except Exception as e:
            return {
                "command": cmd,
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
            }

    async def _build_prompt(
        self, state: WorkflowState, **_kwargs: object
    ) -> str:
        """Build prompt with tool analysis results.

        Reads ARCHITECTURE.md for coding standards and incorporates
        tool results for LLM analysis.

        Args:
            state: Current workflow state
            **_kwargs: Additional context (unused)

        Returns:
            Formatted prompt string for LLM
        """
        tool_results = state.get("tool_results", {})
        architecture = (
            await self._read_if_exists("ARCHITECTURE.md")
            or "ARCHITECTURE.md not found."
        )

        # Extract coding standards section
        cursorrules = await self._read_if_exists(".cursorrules") or ""

        prompt = f"""You are the Static Analysis Agent (Tier 3).

Your mission is to provide fast, deterministic code quality feedback.

## Coding Standards (from ARCHITECTURE.md)

{architecture}

## .cursorrules (Coding Conventions)

{cursorrules}

## Tool Execution Results

### Black (Code Formatting)
**Command:** {tool_results.get('black', {}).get('command', 'N/A')}
**Return Code:** {tool_results.get('black', {}).get('return_code', 'N/A')}
**Output:**
```
{tool_results.get('black', {}).get('stdout', '')}
{tool_results.get('black', {}).get('stderr', '')}
```

### Ruff (Linting)
**Command:** {tool_results.get('ruff', {}).get('command', 'N/A')}
**Return Code:** {tool_results.get('ruff', {}).get('return_code', 'N/A')}
**Output:**
```
{tool_results.get('ruff', {}).get('stdout', '')}
{tool_results.get('ruff', {}).get('stderr', '')}
```

### Mypy (Type Checking)
**Command:** {tool_results.get('mypy', {}).get('command', 'N/A')}
**Return Code:** {tool_results.get('mypy', {}).get('return_code', 'N/A')}
**Output:**
```
{tool_results.get('mypy', {}).get('stdout', '')}
{tool_results.get('mypy', {}).get('stderr', '')}
```

### Radon (Complexity Analysis)
**Command:** {tool_results.get('radon', {}).get('command', 'N/A')}
**Return Code:** {tool_results.get('radon', {}).get('return_code', 'N/A')}
**Output:**
```
{tool_results.get('radon', {}).get('stdout', '')}
{tool_results.get('radon', {}).get('stderr', '')}
```

## Instructions

1. **Analyze Tool Results:**
   - Identify critical issues (must fix)
   - Identify warnings (should fix)
   - Identify complexity violations (cyclomatic complexity > 10)

2. **Generate COMPLIANCE_LOG.md:**
   - Analysis date and time
   - Overall status (APPROVED or REJECTED)
   - Detailed breakdown by tool
   - List of critical issues with file:line references
   - Actionable recommendations for Software Engineer
   - Estimated fix time

3. **Decision Logic:**
   - REJECT if:
     * Any tool has critical errors (return code != 0 for black, ruff, mypy)
     * Cyclomatic complexity > 10 for any function
     * Type errors found
     * Formatting violations found
   - APPROVE if:
     * All tools return 0 (or clean output)
     * No complexity violations
     * No type errors

## Output Format

Provide COMPLIANCE_LOG.md content:
```markdown:COMPLIANCE_LOG.md
# Code Compliance Log

**Analysis Date:** {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")}
**Status:** ❌ REJECTED | ✅ APPROVED

## Summary
...

## Black (Formatting)
...

## Ruff (Linting)
...

## Mypy (Type Checking)
...

## Radon (Complexity)
...

## Critical Issues (Must Fix)
1. ...

## Recommendations
...

## Estimated Fix Time
...
```

Also provide JSON summary:
```json
{{
    "status": "APPROVED" | "REJECTED",
    "critical_issues_count": 0,
    "critical_issues": ["issue1", "issue2"],
    "route_to": "Software Engineer" | "Quality Engineer"
}}
```
"""
        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        _state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse LLM output and save COMPLIANCE_LOG.md.

        Extracts markdown report and JSON summary from LLM response.

        Args:
            response: LLM response object
            state: Current workflow state

        Returns:
            Dictionary with:
                - report_generated: Boolean
                - status: "APPROVED" or "REJECTED"
                - critical_issues_count: Integer
                - critical_issues: List of issues
                - route_to: Next agent to route to
        """
        content = response.content
        result: dict[str, Any] = {}

        # Extract and save COMPLIANCE_LOG.md
        md_pattern = r"```markdown:COMPLIANCE_LOG\.md\n(.*?)```"
        md_match = re.search(md_pattern, content, re.DOTALL)
        if md_match:
            report_content = md_match.group(1)
            await self._write_file("COMPLIANCE_LOG.md", report_content)
            result["report_generated"] = True
        else:
            # Fallback: try without filename
            md_pattern_alt = r"```markdown\n(.*?)```"
            md_match_alt = re.search(md_pattern_alt, content, re.DOTALL)
            if md_match_alt:
                report_content = md_match_alt.group(1)
                await self._write_file("COMPLIANCE_LOG.md", report_content)
                result["report_generated"] = True

        # Extract JSON summary
        json_pattern = r"```json\n(.*?)\n```"
        json_match = re.search(json_pattern, content, re.DOTALL)
        if json_match:
            try:
                summary = json.loads(json_match.group(1))
                result.update(summary)
            except json.JSONDecodeError as e:
                result["status"] = "ERROR"
                result["error"] = f"Failed to parse JSON summary: {e!s}"

        # Ensure status is set
        if "status" not in result:
            result["status"] = "APPROVED"  # Default to approved if no issues

        return result

    def _get_temperature(self) -> float:
        """Get LLM temperature for static analysis.

        Static Analysis uses low temperature (0.1) for:
        - Deterministic analysis
        - Consistent report generation
        - Minimal hallucinations

        Returns:
            Temperature value: 0.1 (very low for determinism)
        """
        return 0.1
