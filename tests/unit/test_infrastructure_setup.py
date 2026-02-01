"""Unit tests for InfrastructureSetupAgent."""

import sys
from unittest.mock import MagicMock


sys.modules["structlog"] = MagicMock()


from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.tier_2.infrastructure_setup import InfrastructureSetupAgent
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
    agent = InfrastructureSetupAgent(
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
    )
    agent._read_if_exists = AsyncMock()
    agent._write_file = AsyncMock()
    return agent


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
async def test_build_prompt_success(agent, workflow_state):
    agent._read_if_exists.side_effect = ["Architecture content", "Dependencies content"]

    prompt = await agent._build_prompt(workflow_state)

    assert "Architecture Document" in prompt
    assert "Dependencies Document" in prompt


@pytest.mark.anyio
async def test_build_prompt_no_architecture(agent, workflow_state):
    agent._read_if_exists.side_effect = [None, "Dependencies"]

    with pytest.raises(ValueError, match="ARCHITECTURE.md not found"):
        await agent._build_prompt(workflow_state)


@pytest.mark.anyio
async def test_parse_output_success(agent, workflow_state):
    content = """# Infrastructure Setup

## Services
### 1. App
### 2. DB

## Docker Compose Configuration
...

## Environment Variables
...
"""
    mock_response = MagicMock()
    mock_response.content = content
    mock_response.tokens_used = 100

    result = await agent._parse_output(mock_response, workflow_state)

    assert result["infrastructure_generated"] is True
    assert result["services_count"] == 2
    agent._write_file.assert_called_once_with("INFRASTRUCTURE.md", content.strip())


@pytest.mark.anyio
async def test_parse_output_malformed_blocks(agent, workflow_state):
    # Test with generic code block
    content = """```
# Infrastructure Setup
## Services
Services List
## Docker Compose Configuration
Config
## Environment Variables
Env
```"""
    mock_response = MagicMock()
    mock_response.content = content
    mock_response.tokens_used = 100

    result = await agent._parse_output(mock_response, workflow_state)

    assert result["infrastructure_generated"] is True
    agent._write_file.assert_called_once_with(
        "INFRASTRUCTURE.md",
        """# Infrastructure Setup
## Services
Services List
## Docker Compose Configuration
Config
## Environment Variables
Env""",
    )


@pytest.mark.anyio
async def test_parse_output_missing_sections(agent, workflow_state):
    # Test missing sections (should still pass but trigger the pass block)
    content = """# Infrastructure Setup
Missing other sections
"""
    mock_response = MagicMock()
    mock_response.content = content
    mock_response.tokens_used = 50

    result = await agent._parse_output(mock_response, workflow_state)

    assert result["infrastructure_generated"] is True
    # Verify it still writes the file
    agent._write_file.assert_called_once_with("INFRASTRUCTURE.md", content.strip())
