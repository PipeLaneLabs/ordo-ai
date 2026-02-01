"""Mock agent implementations for testing Phase 2 orchestration without Phase 3 agents.

These mocks allow us to test the orchestration infrastructure (checkpoints, controller,
base agent, deviation handler) without waiting for actual agent implementations.
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.config import Settings
from src.llm.base_client import BaseLLMClient, LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


class MockSimpleAgent(BaseAgent):
    """Simple mock agent for testing BaseAgent template method."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
        name: str = "MockAgent",
        response_content: str = "Mock response",
    ) -> None:
        """Initialize mock agent.

        Args:
            llm_client: LLM client instance
            budget_guard: Budget guard instance
            settings: Application settings
            name: Agent name
            response_content: Content to return from LLM
        """
        super().__init__(
            name=name,
            llm_client=llm_client,
            budget_guard=budget_guard,
            settings=settings,
            token_budget=1000,
        )
        self.response_content = response_content
        self.prompt_called = False
        self.parse_called = False

    async def _build_prompt(
        self,
        state: WorkflowState,
        **kwargs: Any,
    ) -> str:
        """Build simple test prompt.

        Args:
            state: Current workflow state
            **kwargs: Additional context

        Returns:
            Test prompt string
        """
        self.prompt_called = True
        return f"Test prompt for {self.name} with request: {state['user_request']}"

    async def _parse_output(
        self,
        response: LLMResponse,
        state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse mock response.

        Args:
            response: LLM response
            state: Current workflow state

        Returns:
            Parsed result
        """
        self.parse_called = True
        return {
            "agent_output": response.content,
            "tokens_used": response.tokens_used,
            "mock_agent_executed": True,
        }


class MockFailingAgent(BaseAgent):
    """Mock agent that fails for testing error handling."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        budget_guard: BudgetGuard,
        settings: Settings,
        error_message: str = "Mock agent failure",
    ) -> None:
        """Initialize failing mock agent.

        Args:
            llm_client: LLM client instance
            budget_guard: Budget guard instance
            settings: Application settings
            error_message: Error message to raise
        """
        super().__init__(
            name="MockFailingAgent",
            llm_client=llm_client,
            budget_guard=budget_guard,
            settings=settings,
            token_budget=1000,
        )
        self.error_message = error_message

    async def _build_prompt(
        self,
        state: WorkflowState,
        **kwargs: Any,
    ) -> str:
        """Build prompt (never called in failure scenario).

        Args:
            state: Current workflow state
            **kwargs: Additional context

        Returns:
            Test prompt
        """
        return "This should not be used"

    async def _parse_output(
        self,
        response: LLMResponse,
        state: WorkflowState,
    ) -> dict[str, Any]:
        """Parse output by raising error.

        Args:
            response: LLM response
            state: Current workflow state

        Returns:
            Never returns

        Raises:
            ValueError: Always raises error
        """
        raise ValueError(self.error_message)
