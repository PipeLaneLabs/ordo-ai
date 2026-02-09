"""Base agent abstract class for all 16 workflow agents.

Provides template method pattern for agent execution with:
- Budget reservation and tracking
- LLM interaction
- State management
- File I/O helpers
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import aiofiles
# Space needed for readability between standard library and third-party imports
from src.config import Settings
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


class BaseAgent(ABC):
    """Abstract base class for all workflow agents.

    Implements template method pattern:
    1. Reserve budget
    2. Build prompt (agent-specific)
    3. Call LLM
    4. Parse output (agent-specific)
    5. Record usage
    6. Update state

    Attributes:
        name: Agent name (e.g., "RequirementsStrategyAgent")
        llm_client: LLM provider client
        budget_guard: Budget tracking and enforcement
        settings: Application settings
        token_budget: Maximum tokens per execution
    """

    def __init__(
        self,
        name: str,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
        token_budget: int = 4000,
    ) -> None:
        """Initialize base agent.

        Args:
            name: Agent identifier
            llm_client: LLM client instance
            budget_guard: Budget guard instance
            settings: Application settings
            token_budget: Maximum tokens per execution
        """
        self.name = name
        self.llm_client = llm_client
        self.budget_guard = budget_guard
        self.settings = settings
        self.token_budget = token_budget

    async def execute(
        self,
        state: WorkflowState,
        **kwargs: object,
    ) -> WorkflowState:
        """Execute agent workflow (template method).

        1. Reserve budget for estimated token usage
        2. Build agent-specific prompt
        3. Call LLM provider
        4. Parse LLM output
        5. Record actual token usage
        6. Update workflow state

        Args:
            state: Current workflow state
            **kwargs: Additional agent-specific parameters

        Returns:
            Updated workflow state

        Raises:
            BudgetExhaustedError: If budget limits exceeded
            AgentRejectionError: If agent rejects task
        """
        # Step 1: Reserve budget
        estimated_cost = self._estimate_cost()
        self.budget_guard.reserve_budget(
            operation_name=f"{self.name}.execute",
            estimated_tokens=self.token_budget,
            estimated_cost_usd=estimated_cost,
            workflow_state=state,
        )

        # Step 2: Build prompt (agent-specific)
        prompt = await self._build_prompt(state, **kwargs)

        # Step 3: Call LLM
        response = await self.llm_client.generate(
            prompt=prompt,
            max_tokens=self.token_budget,
            temperature=self._get_temperature(),
            **self._get_llm_kwargs(),
        )

        # Step 4: Parse output (agent-specific)
        result = await self._parse_output(response, state)

        # Step 5: Record actual usage
        self.budget_guard.record_usage(
            operation_name=f"{self.name}.execute",
            tokens_used=response.tokens_used,
            cost_usd=response.cost_usd,
            workflow_state=state,
        )

        # Step 6: Update state
        updated_state = self._update_state(state, result)
        updated_state["current_agent"] = self.name
        updated_state["state_version"] = state.get("state_version", 1) + 1

        return updated_state

    @abstractmethod
    async def _build_prompt(
        self,
        state: WorkflowState,
        **kwargs: object,
    ) -> str:
        """Build agent-specific prompt from state and context.

        Args:
            state: Current workflow state
            **kwargs: Additional parameters

        Returns:
            Formatted prompt string
        """

    @abstractmethod
    async def _parse_output(
        self,
        response: LLMResponse,
        state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse LLM response into structured output.

        Args:
            response: LLM response object
            state: Current workflow state

        Returns:
            Parsed result dictionary

        Raises:
            AgentRejectionError: If output indicates rejection
        """

    def _update_state(
        self,
        state: WorkflowState,
        result: dict[str, Any],
    ) -> WorkflowState:
        """Update workflow state with agent results.

        Default implementation updates partial_artifacts.
        Agents can override for custom state updates.

        Args:
            state: Current workflow state
            result: Parsed agent results

        Returns:
            Updated workflow state
        """
        updated = state.copy()
        partial = updated.get("partial_artifacts", {})
        partial.update(result)
        updated["partial_artifacts"] = partial
        return updated

    def _get_temperature(self) -> float:
        """Get LLM temperature for this agent.

        Default: 0.7 (balanced)
        Override for agent-specific temperatures.

        Returns:
            Temperature value (0.0-1.0)
        """
        return 0.7

    def _get_llm_kwargs(self) -> dict[str, Any]:
        """Get additional LLM parameters for this agent.

        Override for agent-specific parameters (stop sequences, etc.)

        Returns:
            Additional LLM parameters
        """
        return {}

    def _estimate_cost(self) -> float:
        """Estimate cost for this agent execution.

        Default uses token_budget with average cost.
        Override for better estimation.

        Returns:
            Estimated cost in USD
        """
        # Rough estimate: $1 per 1M tokens average
        return (self.token_budget / 1_000_000) * 1.0

    async def _read_if_exists(self, filename: str) -> str | None:
        """Read file content if it exists.

        Helper for reading optional workflow artifacts.

        Args:
            filename: File name (relative to workspace)

        Returns:
            File content or None if not found
        """
        file_path = Path(filename)
        if not file_path.exists():
            return None

        try:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                return await f.read()
        except OSError:
            return None

    async def _write_file(self, filename: str, content: str) -> None:
        """Write content to file.

        Creates parent directories if needed.

        Args:
            filename: File name (relative to workspace)
            content: Content to write

        Raises:
            OSError: On write failures
        """
        file_path = Path(filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(content)

    async def _append_to_file(self, filename: str, content: str) -> None:
        """Append content to file.

        Creates file and parent directories if needed.

        Args:
            filename: File name (relative to workspace)
            content: Content to append

        Raises:
            OSError: On write failures
        """
        file_path = Path(filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(file_path, "a", encoding="utf-8") as f:
            await f.write(content)

    def _check_file_exists(self, filename: str) -> bool:
        """Check if file exists.

        Args:
            filename: File name (relative to workspace)

        Returns:
            True if file exists, False otherwise
        """
        return Path(filename).exists()
