"""Unit tests for BaseAgent."""

import sys
from unittest.mock import MagicMock


sys.modules["structlog"] = MagicMock()


from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base_agent import BaseAgent
from src.orchestration.state import WorkflowState


# Concrete implementation for testing abstract class
class MockAgentImplementation(BaseAgent):
    async def _build_prompt(self, state, **kwargs):
        return "test prompt"

    async def _parse_output(self, response, state):
        return {"parsed": "output"}


@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def mock_budget_guard():
    guard = MagicMock()
    guard.reserve_budget = MagicMock()
    guard.record_usage = MagicMock()
    return guard


@pytest.fixture
def mock_settings():
    return MagicMock()


@pytest.fixture
def agent(mock_llm_client, mock_budget_guard, mock_settings):
    # Pass 4 required arguments + optional token_budget
    return MockAgentImplementation(
        name="TestAgent",
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
        token_budget=1000,
    )


@pytest.fixture
def workflow_state():
    return WorkflowState(
        workflow_id="wf-123",
        budget_remaining_tokens=5000,
        budget_remaining_usd=1.0,
        budget_used_tokens=0,
        budget_used_usd=0.0,
    )


@pytest.mark.anyio
async def test_execute_success(
    agent, mock_llm_client, mock_budget_guard, workflow_state
):
    # Setup mocks
    mock_response = MagicMock()
    mock_response.content = "response content"
    mock_response.tokens_used = 100
    mock_response.cost_usd = 0.001
    mock_llm_client.generate.return_value = mock_response

    # Execute
    result_state = await agent.execute(workflow_state)

    # Verify budget reservation
    mock_budget_guard.reserve_budget.assert_called_once()

    # Verify LLM call
    mock_llm_client.generate.assert_called_once()

    # Verify budget recording
    mock_budget_guard.record_usage.assert_called_once_with(
        operation_name="TestAgent.execute",
        tokens_used=100,
        cost_usd=0.001,
        workflow_state=workflow_state,
    )

    # Verify state update
    assert result_state["partial_artifacts"] == {"parsed": "output"}
    assert result_state["current_agent"] == "TestAgent"


@pytest.mark.anyio
async def test_read_if_exists_success(agent):
    with patch("aiofiles.open", new_callable=MagicMock) as mock_open:
        mock_file = AsyncMock()
        mock_file.read.return_value = "content"
        mock_open.return_value.__aenter__.return_value = mock_file

        # We need to mock Path.exists too
        with patch("pathlib.Path.exists", return_value=True):
            content = await agent._read_if_exists("existent_file.txt")
            assert content == "content"


@pytest.mark.anyio
async def test_read_if_exists_not_found(agent):
    with patch("pathlib.Path.exists", return_value=False):
        content = await agent._read_if_exists("non_existent.txt")
        assert content is None


@pytest.mark.anyio
async def test_write_file(agent):
    with patch("aiofiles.open", new_callable=MagicMock) as mock_open:
        mock_file = AsyncMock()
        mock_open.return_value.__aenter__.return_value = mock_file

        await agent._write_file("output.txt", "content")

        mock_file.write.assert_called_once_with("content")
