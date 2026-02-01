"""Unit tests for ImplementationPlannerAgent."""

import sys
from unittest.mock import MagicMock


sys.modules["structlog"] = MagicMock()


from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.tier_2.implementation_planner import ImplementationPlannerAgent
from src.orchestration.state import WorkflowState


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
    agent = ImplementationPlannerAgent(
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
    )
    # Mock file operations to avoid disk I/O
    agent._read_if_exists = AsyncMock()
    agent._write_file = AsyncMock()
    return agent


@pytest.fixture
def workflow_state():
    return WorkflowState(
        workflow_id="wf-123",
        budget_remaining_tokens=10000,
        budget_remaining_usd=1.0,
        budget_used_tokens=0,
        budget_used_usd=0.0,
    )


@pytest.mark.anyio
async def test_build_prompt_success(agent, workflow_state):
    # Setup mocks
    agent._read_if_exists.side_effect = [
        "Architecture content",  # ARCHITECTURE.md
        "Requirements content",  # REQUIREMENTS.md
    ]

    # Execute
    prompt = await agent._build_prompt(workflow_state)

    # Verify
    assert "Architecture Document" in prompt
    assert "Architecture content" in prompt
    assert "Requirements Document" in prompt


@pytest.mark.anyio
async def test_build_prompt_missing_architecture(agent, workflow_state):
    # Setup mocks
    agent._read_if_exists.side_effect = [None, "Requirements"]

    # Execute & Verify
    with pytest.raises(ValueError, match="ARCHITECTURE.md not found"):
        await agent._build_prompt(workflow_state)


@pytest.mark.anyio
async def test_parse_output_success(agent, workflow_state):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.content = "```markdown\n# Implementation Plan\n\n## File Structure\n\n## Dependency Inventory\n\n## Task Breakdown\n**TASK-001**\n**TASK-002**\n**TASK-003**\n**TASK-004**\n**TASK-005**\n\n## Critical Path\n```"
    mock_response.tokens_used = 100

    # Execute
    result = await agent._parse_output(mock_response, workflow_state)

    # Verify
    assert result["tasks_generated"] is True
    assert result["task_count"] >= 5
    agent._write_file.assert_called_once()
    assert agent._write_file.call_args[0][0] == "TASKS.md"


@pytest.mark.anyio
async def test_execute_integration(agent, mock_llm_client, workflow_state):
    # Determine cost
    agent._estimate_cost = MagicMock(return_value=0.01)

    # Setup mocks
    agent._read_if_exists.side_effect = ["Arch", "Reqs"]
    mock_response = MagicMock()
    mock_response.content = "# Implementation Plan\n\n## File Structure\n\n## Dependency Inventory\n\n## Task Breakdown\n**TASK-001**\n**TASK-002**\n**TASK-003**\n**TASK-004**\n**TASK-005**\n\n## Critical Path"
    mock_response.tokens_used = 100
    mock_response.cost_usd = 0.001
    mock_llm_client.generate.return_value = mock_response

    # Execute
    result = await agent.execute(workflow_state)

    # Verify
    assert result["partial_artifacts"]["tasks_generated"] is True
