"""Product Validator Agent (Tier 4).

Validates implementation against user intent and acceptance criteria.
Ensures all functional requirements are met and identifies deviations.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.agents.base_agent import BaseAgent
from src.llm.base_client import LLMResponse
from src.orchestration.state import WorkflowState


class ProductValidatorAgent(BaseAgent):
    """Product Validator Agent (Tier 4).

    Responsibilities:
    - Verify all functional requirements (FRs) are implemented
    - Verify all acceptance criteria are met
    - Identify deviations from user intent
    - Reject if blocking deviations found

    Primary Output: ACCEPTANCE_REPORT.md

    LLM Model: DeepSeek-R1 (reasoning for acceptance validation)
    Token Budget: 6,000 per invocation
    """

    async def _build_prompt(
        self,
        state: WorkflowState,
        **_kwargs: Any,  # noqa: ANN401
    ) -> str:
        """Build prompt for product validation.

        Reads requirements, architecture, code, and tests to validate
        that implementation meets user intent.

        Args:
            state: Current workflow state
            **kwargs: Additional parameters (validation_focus, etc.)

        Returns:
            Formatted prompt string for LLM
        """
        # Read project context
        user_request = state.get("user_request", "Not available")
        requirements = await self._read_if_exists("REQUIREMENTS.md") or "Not available"
        architecture = await self._read_if_exists("ARCHITECTURE.md") or "Not available"
        tasks = await self._read_if_exists("TASKS.md") or "Not available"
        quality_report = (
            await self._read_if_exists("QUALITY_REPORT.md") or "Not available"
        )

        # Collect implementation evidence
        code_files = self._collect_code_files()
        code_summary = self._summarize_code_files(code_files)

        test_files = self._collect_test_files()
        test_summary = self._summarize_test_files(test_files)

        # Read previous acceptance report if exists (for re-validation)
        previous_report = await self._read_if_exists("ACCEPTANCE_REPORT.md")
        previous_context = ""
        if previous_report:
            previous_context = f"""
## Previous Acceptance Report

{previous_report}

**Note:** This is a re-validation. Focus on verifying that previously identified
deviations have been addressed.
"""

        prompt = f"""# Product Validation Task

You are a product manager performing acceptance testing to verify that the
implementation meets the user's original intent and all acceptance criteria.

## Original User Request

{user_request}

## Project Context

### Requirements
{requirements}

### Architecture
{architecture}

### Tasks
{tasks}

### Quality Report
{quality_report}

{previous_context}

## Implementation Evidence

### Code Files Summary
{code_summary}

### Test Files Summary
{test_summary}

## Validation Checklist

Perform the following validation checks:

### 1. Functional Requirements (FRs) Verification
- Extract all functional requirements from REQUIREMENTS.md
- For each FR, verify it is implemented in the code
- Check that implementation matches the specified behavior
- Verify edge cases are handled

**Severity:** BLOCKING - Reject if any FR is not implemented

### 2. Acceptance Criteria Verification
- Extract all acceptance criteria from REQUIREMENTS.md and TASKS.md
- For each criterion, verify it is met
- Check test coverage for acceptance criteria
- Verify success conditions are testable

**Severity:** BLOCKING - Reject if critical acceptance criteria not met

### 3. User Intent Alignment
- Compare implementation against original user request
- Identify any deviations from user intent
- Check if implementation solves the user's problem
- Verify user experience matches expectations

**Severity:** BLOCKING - Reject if major deviations found

### 4. Non-Functional Requirements (NFRs) Verification
- Check performance requirements (if specified)
- Verify scalability considerations
- Check security requirements (defer to Security Validator)
- Verify observability requirements

**Severity:** WARNING - Document but don't block

### 5. Completeness Check
- Verify all planned features are implemented
- Check for missing functionality
- Verify error handling is comprehensive
- Check documentation completeness

**Severity:** WARNING - Document but don't block

## Output Format

Generate an ACCEPTANCE_REPORT.md with the following structure:

```markdown
# Product Acceptance Report

**Validation Date:** [Current date]
**Overall Status:** ✅ APPROVED | ❌ REJECTED
**Functional Requirements Met:** [X/Y]
**Acceptance Criteria Met:** [X/Y]
**User Intent Alignment:** [High | Medium | Low]

---

## Executive Summary

[Brief summary of acceptance validation results]

---

## Functional Requirements Verification

### FR-001: [Requirement Title]
- **Status:** ✅ IMPLEMENTED | ❌ NOT IMPLEMENTED | ⚠️ PARTIAL
- **Description:** [Requirement description from REQUIREMENTS.md]
- **Implementation Evidence:**
  - File: [filename]
  - Function/Class: [name]
  - Code snippet: [brief reference]
- **Test Coverage:** [test file reference]
- **Notes:** [Any deviations or concerns]

[Repeat for each FR]

---

## Acceptance Criteria Verification

### AC-001: [Acceptance Criterion]
- **Status:** ✅ MET | ❌ NOT MET | ⚠️ PARTIAL
- **Criterion:** [Full criterion text]
- **Evidence:** [How this is verified - code + tests]
- **Notes:** [Any issues]

[Repeat for each AC]

---

## User Intent Alignment

### Original User Request Analysis
[Restate user's original request]

### Implementation Alignment
- **Core Problem Solved:** ✅ YES | ❌ NO
- **User Experience:** [Description of how user will interact]
- **Deviations Identified:**
  1. [Deviation 1 - with severity]
  2. [Deviation 2 - with severity]

### User Value Delivered
[Describe the value delivered to the user]

---

## Non-Functional Requirements

### Performance
- **Status:** [Assessment]
- **Evidence:** [Performance test results if available]

### Scalability
- **Status:** [Assessment]
- **Evidence:** [Architecture decisions]

### Observability
- **Status:** [Assessment]
- **Evidence:** [Logging, metrics, tracing implementation]

---

## Completeness Assessment

### Implemented Features
✅ [List of implemented features]

### Missing Features
❌ [List of missing features - if any]

### Incomplete Features
⚠️ [List of partially implemented features - if any]

---

## Deviations from Specification

### Blocking Deviations
[List deviations that prevent approval]

### Non-Blocking Deviations
[List minor deviations that don't prevent approval]

---

## Recommendations

1. [Recommendation 1]
2. [Recommendation 2]

---

## Quality Gate Decision

**Status:** ✅ APPROVED | ❌ REJECTED

**Reason:** [If REJECTED, explain which requirements/criteria are not met]

**Route To:** [If REJECTED: "Software Engineer" to implement missing features]
```

## Critical Rules

1. **Be Objective:** Base decisions on evidence, not assumptions
2. **Trace to Requirements:** Every FR and AC must be traceable to code
3. **User-Centric:** Always consider if this solves the user's problem
4. **Be Specific:** Provide exact file/function references
5. **Distinguish Severity:** Separate blocking issues from nice-to-haves
6. **Consider Test Coverage:** Tests are evidence of functionality

## Approval Criteria

**APPROVE if:**
- All critical FRs are implemented
- All critical acceptance criteria are met
- Implementation aligns with user intent
- No blocking deviations

**REJECT if:**
- Any critical FR is missing
- Critical acceptance criteria not met
- Major deviation from user intent
- Implementation doesn't solve user's problem

Generate the complete ACCEPTANCE_REPORT.md now.
"""

        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        state: WorkflowState,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Parse LLM output and write ACCEPTANCE_REPORT.md.

        Extracts the acceptance report from LLM response and writes to file.

        Args:
            response: LLM response object containing acceptance analysis
            state: Current workflow state

        Returns:
            Dictionary with report_path and validation_status
        """
        content = response.content.strip()

        # Extract markdown content (remove code fence if present)
        if "```markdown" in content:
            match = re.search(r"```markdown\n(.*?)\n```", content, re.DOTALL)
            if match:
                content = match.group(1)
        elif "```" in content:
            # Remove any code fences
            content = re.sub(r"```[a-z]*\n", "", content)
            content = content.replace("```", "")

        # Write acceptance report
        await self._write_file("ACCEPTANCE_REPORT.md", content)

        # Determine validation status
        status = "APPROVED"
        if (
            "❌ REJECTED" in content
            or "Status:** ❌ REJECTED" in content
            or "**Overall Status:** ❌" in content
        ):
            status = "REJECTED"

        # Extract metrics
        frs_met = self._extract_fraction(content, "Functional Requirements Met")
        acs_met = self._extract_fraction(content, "Acceptance Criteria Met")

        return {
            "acceptance_report_path": "ACCEPTANCE_REPORT.md",
            "acceptance_status": status,
            "functional_requirements_met": frs_met,
            "acceptance_criteria_met": acs_met,
        }

    def _collect_code_files(self) -> list[Path]:
        """Collect all generated code files for validation.

        Returns:
            List of Path objects for code files
        """
        code_files = []
        src_dir = Path("src")

        if src_dir.exists():
            # Scan for Python files
            for py_file in src_dir.rglob("*.py"):
                # Skip test files and migrations
                if "test_" not in py_file.name and "migrations" not in str(py_file):
                    code_files.append(py_file)

        return code_files

    def _collect_test_files(self) -> list[Path]:
        """Collect all test files for validation.

        Returns:
            List of Path objects for test files
        """
        test_files = []
        tests_dir = Path("tests")

        if tests_dir.exists():
            # Scan for test files
            for test_file in tests_dir.rglob("test_*.py"):
                test_files.append(test_file)

        return test_files

    def _summarize_code_files(self, code_files: list[Path]) -> str:
        """Summarize code files for validation.

        Args:
            code_files: List of code file paths

        Returns:
            Summary of code files with key information
        """
        if not code_files:
            return "No code files found."

        summary_lines = [f"**Total Code Files:** {len(code_files)}\n"]

        # Group by directory
        by_directory: dict[str, list[Path]] = {}
        for file_path in code_files:
            dir_name = str(file_path.parent)
            if dir_name not in by_directory:
                by_directory[dir_name] = []
            by_directory[dir_name].append(file_path)

        # Summarize each directory
        for dir_name, files in sorted(by_directory.items()):
            summary_lines.append(f"\n### {dir_name}")
            for file_path in sorted(files):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    lines = len(content.splitlines())
                    # Extract classes and functions
                    classes = re.findall(r"^class\s+(\w+)", content, re.MULTILINE)
                    functions = re.findall(r"^def\s+(\w+)", content, re.MULTILINE)

                    summary_lines.append(f"- **{file_path.name}** ({lines} lines)")
                    if classes:
                        summary_lines.append(f"  - Classes: {', '.join(classes[:5])}")
                    if functions:
                        summary_lines.append(
                            f"  - Functions: {', '.join(functions[:5])}"
                        )
                except Exception:
                    summary_lines.append(f"- **{file_path.name}** (unreadable)")

        return "\n".join(summary_lines)

    def _summarize_test_files(self, test_files: list[Path]) -> str:
        """Summarize test files for validation.

        Args:
            test_files: List of test file paths

        Returns:
            Summary of test files with key information
        """
        if not test_files:
            return "No test files found."

        summary_lines = [f"**Total Test Files:** {len(test_files)}\n"]

        for test_file in sorted(test_files):
            try:
                content = test_file.read_text(encoding="utf-8")
                # Count test functions
                test_functions = re.findall(r"^def\s+(test_\w+)", content, re.MULTILINE)
                summary_lines.append(
                    f"- **{test_file.name}** ({len(test_functions)} tests)"
                )
                if test_functions:
                    summary_lines.append(
                        f"  - Tests: {', '.join(test_functions[:3])}..."
                    )
            except Exception:
                summary_lines.append(f"- **{test_file.name}** (unreadable)")

        return "\n".join(summary_lines)

    def _extract_fraction(self, content: str, metric_name: str) -> str:
        """Extract fraction metric from report.

        Args:
            content: Report content
            metric_name: Metric name to search for

        Returns:
            Fraction string (e.g., "5/5") or "Unknown"
        """
        # Look for patterns like "Functional Requirements Met:** 5/5
        pattern = rf"\*\*{re.escape(metric_name)}:\*\*\s*(\d+/\d+)"
        match = re.search(pattern, content)
        if match:
            return match.group(1)
        return "Unknown"

    def _get_temperature(self) -> float:
        """Get LLM temperature for product validation.

        Product Validator uses medium temperature (0.5) for:
        - Balanced analysis of requirements vs implementation
        - Consistent validation decisions
        - Reasonable interpretation of user intent

        Returns:
            Temperature value: 0.5 (medium for balanced analysis)
        """
        return 0.5

    def _estimate_cost(self) -> float:
        """Estimate cost for Product Validator execution.

        Uses DeepSeek-R1 (FREE via OpenRouter) with 6,000 token budget.
        Actual cost: $0 (free model)

        Returns:
            Estimated cost in USD: 0.0
        """
        return 0.0
