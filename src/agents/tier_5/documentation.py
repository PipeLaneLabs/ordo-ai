"""Documentation Agent (Tier 5).

Generates end-user and developer documentation including README.md,
API_REFERENCE.md, and TROUBLESHOOTING.md based on project artifacts.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import Settings
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


class DocumentationAgent(BaseAgent):
    """Documentation Agent (Tier 5).

    Responsibilities:
    - Generate README.md with project overview and quickstart guide
    - Generate API_REFERENCE.md with endpoint documentation
    - Generate TROUBLESHOOTING.md with common issues and solutions
    - Extract information from ARCHITECTURE.md, TASKS.md, and code files

    Primary Outputs:
    - README.md
    - docs/API_REFERENCE.md
    - docs/TROUBLESHOOTING.md

    LLM Model: DeepSeek-R1 (documentation reasoning)
    Token Budget: 8,000 per invocation
    Temperature: 0.3 (balanced creativity for documentation)
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
    ) -> None:
        """Initialize Documentation Agent.

        Args:
            llm_client: LLM client (should use DeepSeek-R1 for documentation)
            budget_guard: Budget guard instance
            settings: Application settings
        """
        super().__init__(
            name="DocumentationAgent",
            llm_client=llm_client,
            budget_guard=budget_guard,
            settings=settings,
            token_budget=8000,  # 8K tokens for comprehensive documentation
        )

    async def _build_prompt(
        self,
        state: WorkflowState,  # noqa: ARG002
        **_kwargs: object,
    ) -> str:
        """Build prompt for documentation generation.

        Reads project context from REQUIREMENTS.md, ARCHITECTURE.md, TASKS.md,
        and analyzes code structure to generate comprehensive documentation.

        Args:
            state: Current workflow state
            **kwargs: Additional parameters

        Returns:
            Formatted prompt string for LLM
        """
        # Read project context files
        requirements = await self._read_if_exists("REQUIREMENTS.md") or "Not available"
        architecture = await self._read_if_exists("ARCHITECTURE.md") or "Not available"
        tasks = await self._read_if_exists("TASKS.md") or "Not available"
        dependencies = await self._read_if_exists("DEPENDENCIES.md") or "Not available"
        infrastructure = (
            await self._read_if_exists("INFRASTRUCTURE.md") or "Not available"
        )

        # Collect code structure information
        code_structure = self._analyze_code_structure()

        prompt = f"""# Documentation Generation Task

You are a technical writer creating comprehensive documentation for a software project.

## Project Context

### Requirements
{requirements}

### Architecture
{architecture}

### Tasks
{tasks}

### Dependencies
{dependencies}

### Infrastructure
{infrastructure}

### Code Structure
{code_structure}

## Your Task

Generate three documentation files with the following specifications:

### 1. README.md
Create a project README with:
- Project title and brief description
- Key features list
- Technology stack overview
- Quick start guide (installation, setup, running)
- Project structure overview
- Development workflow
- Testing instructions
- Deployment overview
- Contributing guidelines
- License information

**Target Audience:** Developers new to the project
**Tone:** Professional, clear, concise
**Length:** 200-400 lines

### 2. docs/API_REFERENCE.md
Create API documentation with:
- API overview and base URL
- Authentication methods
- Endpoint documentation (method, path, parameters, responses)
- Request/response examples
- Error codes and handling
- Rate limiting information
- Versioning strategy

**Target Audience:** API consumers and integrators
**Tone:** Technical, precise, example-driven
**Length:** 150-300 lines

### 3. docs/TROUBLESHOOTING.md
Create troubleshooting guide with:
- Common issues and solutions
- Environment setup problems
- Database connection issues
- Authentication/authorization errors
- Performance optimization tips
- Debugging techniques
- FAQ section
- Support contact information

**Target Audience:** Developers and operators
**Tone:** Helpful, solution-oriented
**Length:** 100-200 lines

## Output Format

Use XML-like tags to separate the files:

<FILE name="README.md">
[Complete README content in markdown format]
</FILE>

<FILE name="docs/API_REFERENCE.md">
[Complete API reference content in markdown format]
</FILE>

<FILE name="docs/TROUBLESHOOTING.md">
[Complete troubleshooting guide content in markdown format]
</FILE>

## Guidelines

1. **Be Accurate:** Base documentation on actual project artifacts
2. **Be Complete:** Cover all major features and components
3. **Be Clear:** Use simple language and provide examples
4. **Be Consistent:** Maintain consistent formatting and terminology
5. **Be Practical:** Include real-world usage examples
6. **Be Current:** Reflect the actual state of the codebase

## Important Notes

- Extract actual endpoint paths from ARCHITECTURE.md or code
- Use real technology stack from DEPENDENCIES.md
- Reference actual file paths from project structure
- Include realistic examples based on project context
- Ensure all code examples are syntactically correct

Generate the three documentation files now.
"""

        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        _state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse LLM response and save documentation files.

        Extracts documentation content from XML-like tags and writes files.
        Falls back to markdown header detection if no XML tags found.

        Args:
            response: LLM response containing documentation content
            state: Current workflow state

        Returns:
            Dictionary with documentation_files list

        Raises:
            ValueError: If no valid documentation files could be parsed
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

        # Fallback: if no XML matches found, try to extract markdown content
        if not files_created and "# " in content and content.startswith("# "):
            # Look for markdown headers and try to save as README.md
            await self._write_file("README.md", content)
            files_created.append("README.md")

        if not files_created:
            raise ValueError(
                "No valid documentation files could be parsed from LLM response. "
                "Expected <FILE name='...'>...</FILE> tags or markdown content."
            )

        return {
            "documentation_files": files_created,
            "documentation_generated": True,
            "documentation_token_count": response.tokens_used,
        }

    def _get_temperature(self) -> float:
        """Use moderate temperature for documentation generation.

        Returns:
            Temperature value (0.3 for balanced creativity and accuracy)
        """
        return 0.3

    def _analyze_code_structure(self) -> str:
        """Analyze project code structure for documentation.

        Returns:
            Formatted string describing project structure
        """
        src_path = Path("src")
        if not src_path.exists():
            return "Code structure not available"

        structure_lines = ["Project Structure:", "```"]

        # Collect directories and key files
        for item in sorted(src_path.rglob("*")):
            if item.is_file() and item.suffix == ".py":
                relative_path = item.relative_to(Path.cwd())
                structure_lines.append(f"  {relative_path}")

        structure_lines.append("```")
        return "\n".join(structure_lines)
