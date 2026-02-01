"""Unit tests for DependencyResolverAgent."""

import sys
from unittest.mock import MagicMock


sys.modules["structlog"] = MagicMock()


from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.tier_2.dependency_resolver import DependencyResolverAgent
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
    agent = DependencyResolverAgent(
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
    agent._read_if_exists.side_effect = ["Tasks content", "Architecture content"]

    prompt = await agent._build_prompt(workflow_state)

    assert "Tasks Document" in prompt
    assert "Architecture Document" in prompt


@pytest.mark.anyio
async def test_build_prompt_missing_tasks(agent, workflow_state):
    agent._read_if_exists.side_effect = [None, "Architecture"]

    with pytest.raises(ValueError, match="TASKS.md not found"):
        await agent._build_prompt(workflow_state)


@pytest.mark.anyio
async def test_parse_output_success_secure(agent, workflow_state):
    mock_response = MagicMock()
    mock_response.content = """# Dependency Management
    
## Production Dependencies
- package==1.0.0

## Security Scan Results
Critical Issues: 0

## License Compatibility
✅ NONE FOUND
"""
    mock_response.tokens_used = 100

    result = await agent._parse_output(mock_response, workflow_state)

    assert result["dependencies_generated"] is True
    assert result["has_security_issues"] is False
    assert result["has_license_issues"] is False
    agent._write_file.assert_called_once_with(
        "DEPENDENCIES.md", mock_response.content.strip()
    )


@pytest.mark.anyio
async def test_parse_output_with_security_issues(agent, workflow_state):
    mock_response = MagicMock()
    mock_response.content = """# Dependency Management
    
## Production Dependencies

## Security Scan Results
Critical Issues: 2

## License Compatibility
✅ NONE FOUND
"""
    mock_response.tokens_used = 100

    result = await agent._parse_output(mock_response, workflow_state)

    assert result["has_security_issues"] is True


@pytest.mark.anyio
async def test_parse_output_with_license_issues(agent, workflow_state):
    mock_response = MagicMock()
    mock_response.content = """# Dependency Management
    
## Production Dependencies

## Security Scan Results
Critical Issues: 0

## License Compatibility
GPL license detected
"""
    mock_response.tokens_used = 100

    result = await agent._parse_output(mock_response, workflow_state)

    assert result["has_license_issues"] is True


@pytest.mark.anyio
async def test_parse_output_malformed_blocks(agent, workflow_state):
    content = """```
# Dependency Management
## Production Dependencies
- pkg==1.0
## Security Scan Results
Critical Issues: 0
## License Compatibility
✅ NONE FOUND
```"""
    mock_response = MagicMock()
    mock_response.content = content
    mock_response.tokens_used = 100

    result = await agent._parse_output(mock_response, workflow_state)

    assert result["dependencies_generated"] is True
    # Check that file write was called with stripped content
    args, _ = agent._write_file.call_args
    assert args[0] == "DEPENDENCIES.md"
    assert args[1].startswith("# Dependency Management")
    assert "```" not in args[1]


@pytest.mark.anyio
async def test_parse_output_missing_sections(agent, workflow_state):
    content = """# Dependency Management
Missing Sections
"""
    mock_response = MagicMock()
    mock_response.content = content
    mock_response.tokens_used = 100

    result = await agent._parse_output(mock_response, workflow_state)

    # Should not fail, just pass through
    assert result["dependencies_generated"] is True
