"""Requirements & Strategy Agent for Tier 1.

Translates user requests into structured requirements with:
- Functional requirements
- Non-functional requirements
- Constraints
- Measurable acceptance criteria
- Security requirements
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import Settings
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


class RequirementsStrategyAgent(BaseAgent):
    """Tier 1 agent for requirements analysis and strategy definition.

    Uses DeepSeek-R1 for deep reasoning about user requirements.
    Generates REQUIREMENTS.md with structured requirements.

    Attributes:
        token_budget: 8,000 tokens for comprehensive requirements analysis
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
    ) -> None:
        """Initialize Requirements & Strategy Agent.

        Args:
            llm_client: LLM client (should use DeepSeek-R1 for reasoning)
            budget_guard: Budget guard instance
            settings: Application settings
        """
        super().__init__(
            name="RequirementsStrategyAgent",
            llm_client=llm_client,
            budget_guard=budget_guard,
            settings=settings,
            token_budget=8000,  # 8K tokens for requirements analysis
        )

    async def _build_prompt(
        self,
        state: WorkflowState,
        **_kwargs: object,
    ) -> str:
        """Build requirements analysis prompt for LLM.

        Args:
            state: Current workflow state
            **kwargs: Additional context

        Returns:
            Formatted prompt for requirements elicitation
        """
        user_request = state["user_request"]

        prompt = f"""# Requirements Analysis Task

## User Request
{user_request}

## Your Task
As a Requirements Engineer, analyze this user request and create a comprehensive
REQUIREMENTS.md document.

### Analysis Framework

1. **Functional Requirements (FR)**
   - What must the system DO?
   - User stories or use cases
   - Core features and capabilities
   - Data processing requirements
   - Business logic rules

2. **Non-Functional Requirements (NFR)**
   - Performance (latency, throughput)
   - Scalability (concurrent users, data volume)
   - Availability (uptime, disaster recovery)
   - Security (authentication, authorization, data protection)
   -Usability (UX, accessibility)
   - Maintainability (code quality, documentation)
   - Compliance (regulations, standards)

3. **Constraints**
   - Technology stack limitations
   - Budget constraints
   - Timeline constraints
   - Third-party dependencies
   - Platform/environment constraints

4. **Acceptance Criteria**
   - Measurable, testable criteria for each requirement
   - Definition of Done
   - Success metrics

5. **Security Requirements**
   - Authentication mechanisms
   - Authorization/access control
   - Data encryption (at rest, in transit)
   - Input validation
   - Audit logging
   - Vulnerability protection (SQL injection, XSS, CSRF)

## Output Format

Generate a REQUIREMENTS.md document with the following structure:

```markdown
# Requirements Specification

**Project:** [Project Name]
**Version:** 1.0
**Date:** [Current Date]
**Author:** Requirements & Strategy Agent

---

## 1. Executive Summary

[Brief overview of the project and key objectives]

---

## 2. Functional Requirements

### FR-001: [Requirement Title]
- **Description:** [Detailed description]
- **Priority:** [Critical/High/Medium/Low]
- **Acceptance Criteria:**
  - [ ] [Testable criterion 1]
  - [ ] [Testable criterion 2]

[Continue for all functional requirements]

---

## 3. Non-Functional Requirements

### NFR-001: Performance
- **Metric:** [Specific metric]
- **Target:** [Measurable target]
- **Priority:** [Critical/High/Medium/Low]

[Continue for all NFRs]

---

## 4. Constraints

### C-001: [Constraint Title]
- **Description:** [Details]
- **Impact:** [How this affects the project]

---

## 5. Security Requirements

### SEC-001: [Security Requirement]
- **Description:** [Details]
- **Implementation:** [Approach]
- **Priority:** [Critical/High/Medium/Low]

---

## 6. Acceptance Criteria Summary

[Overall project acceptance criteria]

---

## 7. Out of Scope

[What is explicitly NOT included in this project]

---

## 8. Assumptions

[Assumptions made during requirements analysis]

---

## 9. Dependencies

[External dependencies and integrations]

---

## 10. Glossary

[Key terms and definitions]
```

## Guidelines

1. **Be Specific:** Use measurable, testable language
2. **Prioritize:** Mark Critical/High/Medium/Low priority
3. **Be Complete:** Cover all aspects of the user request
4. **Be Realistic:** Consider feasibility and constraints
5. **Think Security:** Security is not optional
6. **Use Standards:** Follow IEEE 830 best practices

## Respond with the complete REQUIREMENTS.md content
"""

        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        _state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse LLM response and extract REQUIREMENTS.md content.

        Args:
            response: LLM response with requirements document
            state: Current workflow state

        Returns:
            Parsed requirements with validation
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
            "# Requirements Specification",
            "## 2. Functional Requirements",
            "## 3. Non-Functional Requirements",
            "## 5. Security Requirements",
        ]

        missing_sections = [
            section for section in required_sections if section not in content
        ]

        if missing_sections:
            # Log warning but don't fail - LLM might use slightly different formatting
            pass

        # Write REQUIREMENTS.md file
        await self._write_file("REQUIREMENTS.md", content)

        return {
            "requirements": content,
            "requirements_generated": True,
            "requirements_token_count": response.tokens_used,
            "requirements_sections": len(
                [line for line in content.split("\n") if line.startswith("##")]
            ),
        }

    def _get_temperature(self) -> float:
        """Use moderate temperature for structured requirements.

        Returns:
            Temperature value (0.4 for balanced creativity and structure)
        """
        return 0.4
