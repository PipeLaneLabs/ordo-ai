"""Commit Agent (Tier 5).

Commits generated code to Git repository with conventional commit messages.
Handles git staging, commit message generation, and optional push operations.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import Settings
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


logger = logging.getLogger(__name__)


class CommitAgent(BaseAgent):
    """Commit Agent (Tier 5).

    Responsibilities:
    - Stage all generated files using git add
    - Generate conventional commit message based on changes
    - Create git commit with generated message
    - Optional push to remote (disabled by default)
    - Handle git errors gracefully

    Primary Output: Git commit with conventional commit message

    LLM Model: Gemini-2.5-Flash (commit message generation)
    Token Budget: 2,000 per invocation
    Temperature: 0.2 (consistent commit messages)
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
    ) -> None:
        """Initialize Commit Agent.

        Args:
            llm_client: LLM client (should use Gemini-2.5-Flash for messages)
            budget_guard: Budget guard instance
            settings: Application settings
        """
        super().__init__(
            name="CommitAgent",
            llm_client=llm_client,
            budget_guard=budget_guard,
            settings=settings,
            token_budget=2000,  # 2K tokens for commit message generation
        )

    async def _build_prompt(
        self,
        state: WorkflowState,
        **_kwargs: object,
    ) -> str:
        """Build prompt for commit message generation.

        Analyzes user request and workflow state to generate appropriate
        conventional commit message.

        Args:
            state: Current workflow state
            **kwargs: Additional parameters

        Returns:
            Formatted prompt string for LLM
        """
        user_request = state.get("user_request", "Update project")
        current_phase = state.get("current_phase", "unknown")
        completed_tasks = state.get("completed_tasks", [])
        completed_tasks_str = (
            [str(task) for task in completed_tasks]
            if isinstance(completed_tasks, list) and completed_tasks
            else []
        )

        # Get git status to understand changes
        git_status = await self._get_git_status()

        prompt = f"""# Commit Message Generation Task

You are a Git expert creating a conventional commit message for code changes.

## Context

### User Request
{user_request}

### Current Phase
{current_phase}

### Completed Tasks
{', '.join(completed_tasks_str) if completed_tasks_str else 'None'}

### Git Status
{git_status}

## Your Task

Generate a conventional commit message following the format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Commit Types
- **feat:** New feature
- **fix:** Bug fix
- **docs:** Documentation changes
- **style:** Code style changes (formatting, etc.)
- **refactor:** Code refactoring
- **test:** Adding or updating tests
- **chore:** Maintenance tasks
- **perf:** Performance improvements
- **ci:** CI/CD changes
- **build:** Build system changes

### Guidelines

1. **Subject Line:**
   - Use imperative mood ("add" not "added")
   - No period at the end
   - Maximum 50 characters
   - Lowercase after colon

2. **Body:**
   - Explain WHAT and WHY (not HOW)
   - Wrap at 72 characters
   - Separate from subject with blank line
   - Can be multiple paragraphs

3. **Footer:**
   - Reference issues (e.g., "Closes #123")
   - Note breaking changes (e.g., "BREAKING CHANGE: ...")
   - Optional

4. **Scope:**
   - Component or module affected
   - Examples: api, auth, database, docs, deployment
   - Optional but recommended

## Output Format

Wrap your commit message in XML tags:

<COMMIT_MESSAGE>
[Your conventional commit message here]
</COMMIT_MESSAGE>

## Example

<COMMIT_MESSAGE>
feat(api): add user authentication endpoints

Implement JWT-based authentication with login and logout endpoints.
Add middleware for token validation and user session management.

- Add POST /api/auth/login endpoint
- Add POST /api/auth/logout endpoint
- Add JWT token generation and validation
- Add authentication middleware

Closes #42
</COMMIT_MESSAGE>

Generate the commit message now based on the provided context.
"""

        return prompt

    async def _parse_output(
        self,
        response: LLMResponse,
        _state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse LLM response and execute git commit.

        Extracts commit message from LLM response, stages changes,
        and creates git commit. Handles various git error scenarios.

        Args:
            response: LLM response containing commit message
            state: Current workflow state

        Returns:
            Dictionary with commit_message and commit_status

        Raises:
            RuntimeError: If git operations fail critically
        """
        content = response.content
        commit_message = "chore: update project"

        # Parse commit message from LLM response
        if "<COMMIT_MESSAGE>" in content:
            try:
                commit_message = (
                    content.split("<COMMIT_MESSAGE>")[1]
                    .split("</COMMIT_MESSAGE>")[0]
                    .strip()
                )
            except IndexError:
                logger.warning(
                    "Failed to parse commit message from LLM response, "
                    "using default",
                    extra={"response_content": content[:200]},
                )
        else:
            logger.warning(
                "No commit message tags found in LLM response, using default",
                extra={"response_content": content[:200]},
            )

        # Execute git commands
        commit_status = "not_committed"
        try:
            # Check if we're in a git repository
            await self._run_git_command(["git", "rev-parse", "--git-dir"])

            # Stage all changes
            await self._run_git_command(["git", "add", "."])
            logger.info("Staged all changes for commit")

            # Check if there are changes to commit
            status_result = await self._run_git_command(
                ["git", "status", "--porcelain"]
            )

            if status_result.strip():  # Only commit if there are changes
                await self._run_git_command(["git", "commit", "-m", commit_message])
                logger.info(
                    "Successfully committed changes",
                    extra={"commit_message": commit_message},
                )
                commit_status = "committed"
            else:
                logger.info("No changes to commit")
                commit_message = "No changes to commit"
                commit_status = "no_changes"

        except RuntimeError as e:
            error_msg = str(e)
            if "not a git repository" in error_msg.lower():
                logger.warning("Not in a git repository, skipping commit")
                commit_message = "Not in git repository"
                commit_status = "not_git_repo"
            elif (
                "nothing to commit" in error_msg.lower()
                or "nothing added to commit" in error_msg.lower()
            ):
                logger.info("No changes to commit")
                commit_message = "No changes to commit"
                commit_status = "no_changes"
            else:
                logger.error(
                    "Git commit failed",
                    extra={"error": error_msg},
                    exc_info=True,
                )
                raise RuntimeError(f"Git operation failed: {error_msg}") from e
        except Exception as e:
            logger.error(
                "Unexpected error during git operations",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise RuntimeError(f"Unexpected git error: {e}") from e

        return {
            "commit_message": commit_message,
            "commit_status": commit_status,
            "commit_token_count": response.tokens_used,
        }

    def _get_temperature(self) -> float:
        """Use low temperature for consistent commit messages.

        Returns:
            Temperature value (0.2 for consistency)
        """
        return 0.2

    async def _run_git_command(self, args: list[str]) -> str:
        """Run a git command and return stdout.

        Args:
            args: Git command arguments (e.g., ["git", "status"])

        Returns:
            stdout content as string

        Raises:
            RuntimeError: If git command fails
        """
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            raise RuntimeError(
                f"Git command failed: {' '.join(args)}\nError: {error_msg}"
            )

        return stdout.decode().strip()

    async def _get_git_status(self) -> str:
        """Get current git status for context.

        Returns:
            Git status output or error message
        """
        try:
            status = await self._run_git_command(["git", "status", "--short"])
            if not status:
                return "No changes detected"
            return f"Changes:\n{status}"
        except RuntimeError:
            return "Not in a git repository or git not available"
