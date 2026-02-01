"""Strategy Validator Agent for Tier 1.

Validates requirements for:
- Feasibility and logical consistency
- Conflicting requirements
- Technical feasibility assessment
- Risk assessment
- Quality gate enforcement
"""

import re
from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import Settings
from src.exceptions import AgentRejectionError
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


class StrategyValidatorAgent(BaseAgent):
    """Tier 1 agent for requirements validation and feasibility assessment.

    Uses DeepSeek-R1 for deep reasoning about requirement conflicts and risks.
    Generates VALIDATION_REPORT.md and blocks progression if critical issues found.

    Attributes:
        token_budget: 6,000 tokens for validation analysis
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
    ) -> None:
        """Initialize Strategy Validator Agent.

        Args:
            llm_client: LLM client (should use DeepSeek-R1 for reasoning)
            budget_guard: Budget guard instance
            settings: Application settings
        """
        super().__init__(
            name="StrategyValidatorAgent",
            llm_client=llm_client,
            budget_guard=budget_guard,
            settings=settings,
            token_budget=6000,  # 6K tokens for validation analysis
        )

    async def _build_prompt(
        self,
        state: WorkflowState,
        **_kwargs: object,
    ) -> str:
        """Build validation prompt for LLM.

        Args:
            state: Current workflow state
            **kwargs: Additional context

        Returns:
            Formatted prompt for requirements validation
        """
        requirements = state.get("requirements", "")
        if not requirements:
            requirements = await self._read_if_exists("REQUIREMENTS.md") or ""

        prompt = f"""# Requirements Validation Task

## Requirements to Validate

{requirements}

## Your Task

As a Strategy Validator, perform a comprehensive validation of these requirements.

### Validation Framework

#### 1. **Conflict Detection**
Analyze for:
- Contradictory functional requirements
- Incompatible non-functional requirements
- Technology stack conflicts
- Resource constraint conflicts
- Timeline vs scope conflicts

#### 2. **Feasibility Assessment**
Evaluate:
- Technical feasibility (can it be built?)
- Resource feasibility (do we have the skills/tools?)
- Timeline feasibility (realistic estimates?)
- Budget feasibility (cost-effective?)
- Operational feasibility (can it be maintained?)

#### 3. **Risk Assessment**
Identify risks:
- Technical risks (complexity, unknowns)
- Security risks (attack vectors, vulnerabilities)
- Performance risks (scalability, bottlenecks)
- Integration risks (third-party dependencies)
- Compliance risks (regulatory requirements)

Rate each risk: **Critical/High/Medium/Low**

#### 4. **Completeness Check**
Verify:
- All functional areas covered?
- Security requirements adequate?
- Non-functional requirements measurable?
- Acceptance criteria testable?
- Dependencies identified?

#### 5. **Quality Gate Decision**
Based on your analysis:
- **APPROVED:** No blocking issues found → proceed to architecture
- **REJECTED:** Critical/blocking issues found → return to requirements

## Output Format

Generate a VALIDATION_REPORT.md with:

```markdown
# Requirements Validation Report

**Validator:** Strategy Validator Agent
**Date:** [Current Date]
**Status:** [APPROVED/REJECTED]

---

## Executive Summary

[Brief overview of validation results]

**Decision:** [APPROVED/REJECTED]
**Blocking Issues:** [Count]
**High Priority Issues:** [Count]
**Recommendations:** [Key recommendations]

---

## 1. Conflict Analysis

### Finding: [Conflict Title]
- **Severity:** [Critical/High/Medium/Low]
- **Description:** [Detailed explanation]
- **Affected Requirements:** [FR-001, NFR-002, etc.]
- **Impact:** [Consequences if not resolved]
- **Recommendation:** [How to resolve]

[List all conflicts found]

**Summary:** [X conflicts found - Y blocking]

---

## 2. Feasibility Assessment

### 2.1 Technical Feasibility: [FEASIBLE/AT RISK/INFEASIBLE]
- **Assessment:** [Detailed analysis]
- **Concerns:** [Technical challenges]
- **Mitigation:** [Recommended approaches]

### 2.2 Resource Feasibility: [FEASIBLE/AT RISK/INFEASIBLE]
- **Skills Required:** [List]
- **Tools Required:** [List]
- **Availability:** [Assessment]

### 2.3 Timeline Feasibility: [FEASIBLE/AT RISK/INFEASIBLE]
- **Estimated Effort:** [Ballpark estimate]
- **Timeline Concerns:** [Issues]
- **Recommendations:** [Adjustments needed]

### 2.4 Budget Feasibility: [FEASIBLE/AT RISK/INFEASIBLE]
- **Infrastructure Costs:** [Estimate]
- **Third-party Costs:** [Licenses, APIs, etc.]
- **Concerns:** [Budget risks]

---

## 3. Risk Assessment

### Risk Matrix

| Risk ID | Risk Description | Likelihood | Impact | Severity | Mitigation |
|---------|-----------------|------------|--------|----------|------------|
| R-001 | [Description] | [H/M/L] | [H/M/L] | [Critical/High/Medium/Low] | [Strategy] |

### Critical Risks (Immediate Attention Required)
[List and detail all critical risks]

### High Risks (Mitigation Planning Required)
[List and detail all high risks]

---

## 4. Completeness Check

- [ ] All functional requirements clear and testable
- [ ] Non-functional requirements measurable
- [ ] Security requirements comprehensive
- [ ] Acceptance criteria defined
- [ ] Dependencies identified
- [ ] Constraints documented
- [ ] Out-of-scope items clarified

**Gaps Found:** [List any missing areas]

---

## 5. Security Assessment

### Security Coverage: [ADEQUATE/INSUFFICIENT]
- **Authentication:** [Assessment]
- **Authorization:** [Assessment]
- **Data Protection:** [Assessment]
- **Input Validation:** [Assessment]
- **Audit Logging:** [Assessment]

**Security Concerns:** [Critical security gaps, if any]

---

## 6. Recommendations

### Must-Fix (Blocking Issues)
1. [Blocking issue 1]
2. [Blocking issue 2]

### Should-Fix (High Priority)
1. [High priority issue 1]
2. [High priority issue 2]

### Consider (Medium Priority)
1. [Medium priority improvement 1]

---

## 7. Quality Gate Decision

**Decision:** [APPROVED ✅ / REJECTED ❌]

**Rationale:** [Explanation of decision]

**If APPROVED:**
- Ready to proceed to Solution Architect
- [Any conditions or notes]

**If REJECTED:**
- Return to Requirements & Strategy Agent
- Focus areas: [What needs revision]
- Blocking issues must be resolved before re-validation
```

## Validation Rules

1. **REJECT if:**
   - Any Critical severity issues found
   - Conflicting requirements detected
   - Technical infeasibility identified
   - Critical security gaps exist
   - Missing essential requirements

2. **APPROVE if:**
   - No blocking issues
   - All requirements clear and feasible
   - Risks identified and acceptable
   - Security requirements adequate
   - Ready for architectural design

## Respond with the complete VALIDATION_REPORT.md content
"""

        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        _state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse validation report and enforce quality gate.

        Args:
            response: LLM response with validation report
            state: Current workflow state

        Returns:
            Validation results

        Raises:
            AgentRejectionError: If validation fails with blocking issues
        """
        # Extract content
        content = response.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```markdown"):
            content = content.split("```markdown")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()

        decision_match = re.search(
            r"\*\*Decision:\*\*\s*(APPROVED|REJECTED)",
            content,
            flags=re.IGNORECASE,
        )
        status_match = re.search(
            r"\*\*Status:\*\*\s*(APPROVED|REJECTED)",
            content,
            flags=re.IGNORECASE,
        )
        match_result = decision_match or status_match
        decision = (
            match_result.group(1).upper()
            if match_result is not None
            else ""
        )

        blocking_count_match = re.search(
            r"\*\*Blocking Issues:\*\*\s*(\d+)",
            content,
            flags=re.IGNORECASE,
        )
        blocking_issues_count = (
            int(blocking_count_match.group(1)) if blocking_count_match else 0
        )

        # Extract blocking issues
        blocking_issues: list[str] = []
        if "### Must-Fix (Blocking Issues)" in content:
            must_fix_lines = content.split("### Must-Fix (Blocking Issues)", 1)[
                1
            ].split("\n")
            for line in must_fix_lines:
                if line.startswith("## ") or line.startswith("### "):
                    break
                stripped = line.strip()
                if not stripped:
                    continue
                is_item = (
                    stripped.startswith("-")
                    or stripped.startswith("*")
                    or bool(re.match(r"^\d+\.", stripped))
                )
                if not is_item:
                    continue
                text = re.sub(r"^(?:\d+\.|[-*])\s*", "", stripped).strip()
                if text and text.lower() not in {"none", "n/a", "na"}:
                    blocking_issues.append(text)

        # Write VALIDATION_REPORT.md
        await self._write_file("VALIDATION_REPORT.md", content)

        # Determine quality gate status
        if decision == "REJECTED" or blocking_issues_count > 0 or blocking_issues:
            # Validation failed - raise rejection
            raise AgentRejectionError(
                agent="RequirementsStrategyAgent",
                validator="StrategyValidatorAgent",
                reason="Requirements validation failed - blocking issues found",
                details={
                    "blocking_issues": blocking_issues,
                    "blocking_issues_count": blocking_issues_count,
                    "validation_status": decision or "REJECTED",
                    "report_location": "VALIDATION_REPORT.md",
                },
            )

        # Validation passed
        return {
            "validation_report": content,
            "validation_status": "APPROVED",
            "validation_passed": True,
            "blocking_issues_count": blocking_issues_count,
            "validation_token_count": response.tokens_used,
        }

    def _get_temperature(self) -> float:
        """Use low temperature for deterministic validation.

        Returns:
            Temperature value (0.3 for consistent, analytical evaluation)
        """
        return 0.3
