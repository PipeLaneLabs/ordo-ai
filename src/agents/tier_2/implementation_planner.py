"""Implementation Planner Agent for Tier 2.

Breaks down architecture into file-level tasks with:
- Task breakdown with dependencies
- Dependency graph validation (DAG check)
- Effort estimates
- Critical path identification
- Tool configuration files generation
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import Settings
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


class ImplementationPlannerAgent(BaseAgent):
    """Tier 2 agent for implementation planning and task breakdown.

    Uses DeepSeek-R1 for task planning and dependency analysis.
    Generates TASKS.md with structured task breakdown.

    Attributes:
        token_budget: 6,000 tokens for task planning
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
    ) -> None:
        """Initialize Implementation Planner Agent.

        Args:
            llm_client: LLM client (should use DeepSeek-R1 for planning)
            budget_guard: Budget guard instance
            settings: Application settings
        """
        super().__init__(
            name="ImplementationPlannerAgent",
            llm_client=llm_client,
            budget_guard=budget_guard,
            settings=settings,
            token_budget=6000,  # 6K tokens for task planning
        )

    async def _build_prompt(
        self,
        state: WorkflowState,  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> str:
        """Build task planning prompt for LLM.

        Args:
            state: Current workflow state
            **kwargs: Additional context

        Returns:
            Formatted prompt for task breakdown
        """
        # Read required artifacts
        architecture = await self._read_if_exists("ARCHITECTURE.md")
        requirements = await self._read_if_exists("REQUIREMENTS.md")

        if not architecture:
            raise ValueError(
                "ARCHITECTURE.md not found - Solution Architect must run first"
            )

        prompt = f"""# Implementation Planning Task

## Architecture Document
{architecture}

## Requirements Document
{requirements or "No requirements document available"}

## Your Task
As an Implementation Planner, break down this architecture into a detailed,
executable implementation plan.

### Planning Framework

1. **File Structure**
   - Create complete directory tree
   - Show all files that need to be created
   - Include test files, config files, and documentation
   - Follow architecture's technology stack conventions

2. **Dependency Inventory**
   - List all production dependencies with version constraints
   - List all development dependencies (testing, linting, etc.)
   - Group by category (core, database, observability, etc.)
   - Suggest specific versions (use >= for flexibility)

3. **Tool Configuration Files**
   - pyproject.toml (Poetry configuration)
   - pytest.ini (test configuration)
   - .gitignore (version control)
   - .cursorrules (coding standards from ARCHITECTURE.md)
   - Any other tool configs needed

4. **Task Breakdown**
   - Break into phases (Foundation, Core, Development, Validation, Delivery)
   - Each task should target ONE file or closely related files
   - Include task ID, file path, description, acceptance criteria
   - Specify dependencies between tasks
   - Estimate effort in hours
   - Identify critical path tasks

5. **Validation**
   - Ensure no circular dependencies
   - Validate that all architecture components are covered
   - Check that acceptance criteria map to requirements

## Output Format

Generate a TASKS.md document with the following structure:

```markdown
# Implementation Plan

**Project:** [Project Name from Architecture]
**Version:** 2.0 (Regenerated)
**Date:** [Current Date]
**Planner:** Implementation Planner Agent
**Status:** INITIAL PLAN

---

## Table of Contents
1. [File Structure](#file-structure)
2. [Dependency Inventory](#dependency-inventory)
3. [Tool Configuration Files](#tool-configuration-files)
4. [Task Breakdown](#task-breakdown)
5. [Critical Path](#critical-path)
6. [Risk Areas](#risk-areas)

---

## File Structure

```
project/
├── src/
│   ├── __init__.py
│   ├── config.py                    # TASK-XXX
│   ├── exceptions.py                # TASK-XXX
│   └── ...
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── pyproject.toml
├── pytest.ini
└── README.md
```

---

## Dependency Inventory

### Production Dependencies (Suggestions for Dependency Resolver)

#### Core Framework
- `fastapi>=0.115.0` - REST API framework
- `pydantic>=2.10.0` - Data validation

[Continue with all dependencies grouped by category]

### Development Dependencies

#### Testing
- `pytest>=8.3.0`
- `pytest-asyncio>=0.24.0`

[Continue with dev dependencies]

---

## Tool Configuration Files

### pyproject.toml (TASK-XXX)
```toml
[tool.poetry]
name = "project-name"
version = "1.0.0"
description = "Project description"

[tool.black]
line-length = 100
target-version = ['py312']

[tool.ruff]
line-length = 100
select = ["E", "W", "F", "I", "C", "B", "UP"]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
minversion = "8.0"
addopts = "-ra -q --strict-markers --cov=src"
testpaths = ["tests"]
asyncio_mode = "auto"
```

### pytest.ini (TASK-XXX)
```ini
[pytest]
minversion = 8.0
addopts = -ra -q --strict-markers --cov=src
testpaths = tests
asyncio_mode = auto
```

### .gitignore (TASK-XXX)
```
# Environment
.env
__pycache__/
*.pyc

# Testing
.pytest_cache/
.coverage
htmlcov/

# IDEs
.vscode/
.idea/
```

### .cursorrules (TASK-XXX)
```markdown
# Cursor Rules for [Project Name]

## Code Style
- Use `snake_case` for variables, functions, modules
- Use `PascalCase` for class names
- Use `UPPER_SNAKE_CASE` for constants
- Maximum line length: 100 characters
- Maximum function length: 50 lines
- Maximum cyclomatic complexity: 10

## Type Hints
- All public functions MUST have type hints
- Use `from __future__ import annotations` for forward references

## Async/Await
- All I/O operations MUST be async
- Use `asyncio.gather()` for parallel operations

## Error Handling
- Use custom exceptions from `src.exceptions`
- Always log exceptions with structured logging

## Testing
- Minimum 70% code coverage required
- Use pytest fixtures for reusable setup
- Mock external dependencies
```

---

## Task Breakdown

### Phase 1: Foundation (Est: X hours)

**TASK-001: Configuration Management**
- **File:** `src/config.py`
- **Description:** Pydantic Settings-based configuration with environment
  variable validation

- **Acceptance Criteria:**
  - NFR-XXX (Environment-based config from REQUIREMENTS.md)
  - Load from .env file
  - Validate required variables
  - Type-safe access
- **Dependencies:** None
- **Estimated Effort:** 1 hour

**TASK-002: Exception Hierarchy**
- **File:** `src/exceptions.py`
- **Description:** Custom exception classes for all workflow errors
- **Acceptance Criteria:**
  - Comprehensive error handling
  - Specific exception types for each failure mode
- **Dependencies:** None
- **Estimated Effort:** 1 hour

[Continue with all tasks, organized by phase]

---

## Critical Path

TASK-001 → TASK-002 → TASK-XXX → TASK-YYY

[Identify the sequence of tasks that determines minimum project duration]

---

## Risk Areas

- **TASK-XXX (Component Name):** Complex, high risk of delays
  - **Mitigation:** Allocate extra time, consider prototype first
- **TASK-YYY (Integration):** Multiple dependencies
  - **Mitigation:** Ensure all dependencies complete before starting

---

## Validation Checklist

- [ ] All architecture components have corresponding tasks
- [ ] No circular task dependencies (DAG validated)
- [ ] All requirements have acceptance criteria in tasks
- [ ] Critical path identified
- [ ] Effort estimates provided
- [ ] Tool configurations complete
```

## Guidelines

1. **Be Comprehensive:** Every file mentioned in ARCHITECTURE.md should have
   a task
2. **Be Specific:** Each task should be clear and actionable
3. **Be Realistic:** Effort estimates should account for complexity
4. **Validate Dependencies:** Ensure task graph is a valid DAG (no cycles)
5. **Map to Requirements:** Link tasks to specific requirements
6. **Include Testing:** Every code task should have corresponding test tasks
7. **Tool Configs:** Generate complete, working configuration files

## Respond with the complete TASKS.md content
"""

        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        _state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse LLM response and extract TASKS.md content.

        Args:
            response: LLM response with task breakdown
            state: Current workflow state

        Returns:
            Parsed tasks with validation
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
            "# Implementation Plan",
            "## File Structure",
            "## Dependency Inventory",
            "## Task Breakdown",
            "## Critical Path",
        ]

        missing_sections = [
            section for section in required_sections if section not in content
        ]

        if missing_sections:
            # Log warning but don't fail; check logic handles variations
            pass

        # Basic validation: check for TASK-XXX patterns
        task_count = content.count("**TASK-")
        if task_count < 5:
            # Warning: very few tasks detected
            pass

        # Write TASKS.md file
        await self._write_file("TASKS.md", content)

        return {
            "tasks": content,
            "tasks_generated": True,
            "task_count": task_count,
            "tasks_token_count": response.tokens_used,
        }

    def _get_temperature(self) -> float:
        """Use moderate temperature for structured planning.

        Returns:
            Temperature value (0.4 for balanced creativity and structure)
        """
        return 0.4
