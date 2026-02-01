"""Security Validator Agent (Tier 4).

Validates code for security vulnerabilities including hardcoded secrets,
SQL injection, XSS, and authentication/authorization implementation.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from src.agents.base_agent import BaseAgent
from src.llm.base_client import LLMResponse
from src.orchestration.state import WorkflowState


logger = logging.getLogger(__name__)


class SecurityValidatorAgent(BaseAgent):
    """Security Validator Agent (Tier 4).

    Responsibilities:
    - Scan for hardcoded secrets (API keys, passwords, tokens)
    - Scan for SQL injection vulnerabilities
    - Scan for XSS vulnerabilities
    - Validate authentication/authorization implementation
    - Reject if P0 (critical) security issues found

    Primary Output: SECURITY_REPORT.md

    LLM Model: DeepSeek-R1 (reasoning for security analysis)
    Token Budget: 6,000 per invocation
    """

    async def _build_prompt(
        self,
        state: WorkflowState,  # noqa: ARG002
        **_kwargs: Any,  # noqa: ANN401
    ) -> str:
        """Build prompt for security validation.

        Reads generated code files and performs security analysis.

        Args:
            state: Current workflow state
            **kwargs: Additional parameters (scan_type, focus_areas, etc.)

        Returns:
            Formatted prompt string for LLM
        """
        # Read project context
        requirements = await self._read_if_exists("REQUIREMENTS.md") or "Not available"
        architecture = await self._read_if_exists("ARCHITECTURE.md") or "Not available"
        tasks = await self._read_if_exists("TASKS.md") or "Not available"

        # Collect generated code files
        code_files = self._collect_code_files()
        code_content = self._format_code_files(code_files)

        # Read previous security report if exists (for re-validation)
        previous_report = await self._read_if_exists("SECURITY_REPORT.md")
        previous_context = ""
        if previous_report:
            previous_context = f"""
## Previous Security Report

{previous_report}

**Note:** This is a re-validation. Focus on verifying that previously identified
issues have been properly remediated.
"""

        prompt = f"""# Security Validation Task

You are a security expert performing a comprehensive security audit of generated code.

## Project Context

### Requirements
{requirements}

### Architecture
{architecture}

### Tasks
{tasks}

{previous_context}

## Code to Validate

{code_content}

## Security Validation Checklist

Perform the following security checks:

### 1. Hardcoded Secrets Detection
- Scan for API keys, passwords, tokens, private keys
- Check for hardcoded credentials in code
- Verify secrets are loaded from environment variables
- Check for exposed secrets in comments or docstrings

**Severity:** P0 (Critical) - MUST reject if found

### 2. SQL Injection Vulnerabilities
- Check for string concatenation in SQL queries
- Verify parameterized queries are used
- Check for ORM usage (SQLAlchemy) vs raw SQL
- Validate input sanitization for database operations

**Severity:** P0 (Critical) - MUST reject if found

### 3. XSS (Cross-Site Scripting) Vulnerabilities
- Check for unescaped user input in HTML/templates
- Verify output encoding is applied
- Check for unsafe innerHTML usage (if JavaScript)
- Validate Content-Security-Policy headers

**Severity:** P0 (Critical) - MUST reject if found

### 4. Authentication & Authorization
- Verify JWT token validation is implemented correctly
- Check for proper password hashing (bcrypt, not MD5/SHA1)
- Validate role-based access control (RBAC) implementation
- Check for session management security
- Verify secure cookie flags (HttpOnly, Secure, SameSite)

**Severity:** P1 (High) - Reject if blocking issues found

### 5. Additional Security Checks
- Check for insecure deserialization (pickle, eval)
- Verify HTTPS enforcement
- Check for CORS misconfiguration
- Validate rate limiting implementation
- Check for path traversal vulnerabilities
- Verify input validation on all endpoints

**Severity:** P2 (Medium) - Document but don't block

## Output Format

Generate a SECURITY_REPORT.md with the following structure:

```markdown
# Security Validation Report

**Validation Date:** [Current date]
**Overall Status:** ✅ APPROVED | ❌ REJECTED
**Critical Issues (P0):** [count]
**High Issues (P1):** [count]
**Medium Issues (P2):** [count]

---

## Executive Summary

[Brief summary of security posture]

---

## Critical Issues (P0) - BLOCKING

### Issue #1: [Title]
- **File:** [filename:line_number]
- **Severity:** P0 (Critical)
- **Category:** [Hardcoded Secrets | SQL Injection | XSS]
- **Description:** [Detailed description]
- **Evidence:**
```[language]
[code snippet showing the issue]
```
- **Remediation:** [Specific fix required]
- **Impact:** [Security impact if not fixed]

[Repeat for each P0 issue]

---

## High Issues (P1)

[Same format as P0]

---

## Medium Issues (P2)

[Same format as P0]

---

## Security Best Practices Verified

✅ [List of security practices that are correctly implemented]

---

## Recommendations

1. [Recommendation 1]
2. [Recommendation 2]

---

## Quality Gate Decision

**Status:** ✅ APPROVED | ❌ REJECTED

**Reason:** [If REJECTED, explain which P0/P1 issues are blocking]

**Route To:** [If REJECTED: "Software Engineer" to fix security issues]
```

## Critical Rules

1. **P0 Issues = Automatic Rejection:** Any hardcoded secrets, SQL injection,
   or XSS vulnerabilities MUST result in REJECTED status
2. **Be Specific:** Provide exact file paths and line numbers
3. **Provide Evidence:** Include code snippets showing the vulnerability
4. **Actionable Remediation:** Give specific fix instructions
5. **No False Positives:** Only flag actual security issues, not theoretical ones
6. **Consider Context:** Check if security measures are appropriate for the project type

Generate the complete SECURITY_REPORT.md now.
"""

        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        state: WorkflowState,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Parse LLM output and write SECURITY_REPORT.md.

        Extracts the security report from LLM response and writes to file.

        Args:
            response: LLM response object containing security analysis
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

        # Write security report
        await self._write_file("SECURITY_REPORT.md", content)

        # Determine validation status
        status = "APPROVED"
        if (
            "❌ REJECTED" in content
            or "Status:** ❌ REJECTED" in content
            or "**Overall Status:** ❌" in content
        ):
            status = "REJECTED"

        # Extract issue counts
        critical_count = self._extract_issue_count(content, "Critical Issues (P0)")
        high_count = self._extract_issue_count(content, "High Issues (P1)")

        return {
            "security_report_path": "SECURITY_REPORT.md",
            "security_status": status,
            "critical_issues": critical_count,
            "high_issues": high_count,
        }

    def _collect_code_files(self) -> list[Path]:
        """Collect all generated code files for security scanning.

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

    def _format_code_files(self, code_files: list[Path]) -> str:
        """Format code files for inclusion in prompt.

        Args:
            code_files: List of code file paths

        Returns:
            Formatted string with file contents
        """
        if not code_files:
            return "No code files found to validate."

        formatted = []
        for file_path in code_files[:20]:  # Limit to 20 files to avoid token overflow
            try:
                content = file_path.read_text(encoding="utf-8")
                formatted.append(
                    f"""
### File: {file_path}

```python
{content}
```
"""
                )
            except Exception as e:
                # Log usage to satisfy S112 and debugging
                logger.warning(f"Error reading file {file_path}: {e}")
                continue

        if len(code_files) > 20:
            formatted.append(
                f"\n**Note:** Showing 20 of {len(code_files)} files. "
                "Additional files not shown to conserve tokens.\n"
            )

        return "\n".join(formatted)

    def _extract_issue_count(self, content: str, section_name: str) -> int:
        """Extract issue count from report section.

        Args:
            content: Report content
            section_name: Section name to search for

        Returns:
            Number of issues found
        """
        # Look for patterns like "Critical Issues (P0):** 3
        pattern = rf"\*\*{re.escape(section_name)}:\*\*\s*(\d+)"
        match = re.search(pattern, content)
        if match:
            return int(match.group(1))

        # Alternative pattern: "## Critical Issues (P0) - BLOCKING" followed by issues
        section_pattern = rf"##\s*{re.escape(section_name)}"
        if re.search(section_pattern, content):
            # Count "### Issue #" occurrences in that section
            section_match = re.search(
                rf"{section_pattern}.*?(?=(?:^|\n)##\s|\Z)", content, re.DOTALL
            )
            if section_match:
                section_text = section_match.group(0)
                issue_count = len(re.findall(r"###\s*Issue\s*#\d+", section_text))
                return issue_count

        return 0

    def _get_temperature(self) -> float:
        """Get LLM temperature for security validation.

        Security Validator uses medium temperature (0.5) for:
        - Balanced analysis (not too creative, not too rigid)
        - Consistent vulnerability detection
        - Reasonable false positive rate

        Returns:
            Temperature value: 0.5 (medium for balanced analysis)
        """
        return 0.5

    def _estimate_cost(self) -> float:
        """Estimate cost for Security Validator execution.

        Uses DeepSeek-R1 (FREE via OpenRouter) with 6,000 token budget.
        Actual cost: $0 (free model)

        Returns:
            Estimated cost in USD: 0.0
        """
        return 0.0
