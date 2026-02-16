"""Unit tests for ObservabilityAgent."""

import sys
from unittest.mock import MagicMock


sys.modules["structlog"] = MagicMock()


from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.tier_2.observability import ObservabilityAgent
from src.orchestration.state import WorkflowState, create_initial_state


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
    # Mocking read_if_exists directly on instance instead of class if possible or override
    agent = ObservabilityAgent(
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
    )
    typed_agent: Any = agent
    typed_agent._read_if_exists = AsyncMock()
    typed_agent._write_file = AsyncMock()
    return agent


@pytest.fixture
def workflow_state() -> WorkflowState:
    state = create_initial_state(
        workflow_id="wf-123",
        user_request="Test request",
        trace_id="trace-123",
    )
    state["budget_remaining_tokens"] = 5000
    state["budget_remaining_usd"] = 1.0
    state["budget_used_tokens"] = 0
    state["budget_used_usd"] = 0.0
    return state


@pytest.mark.anyio
async def test_build_prompt_success(agent, workflow_state):
    agent._read_if_exists.side_effect = ["Architecture", "Tasks", "Requirements"]

    prompt = await agent._build_prompt(workflow_state)

    assert "Architecture Document" in prompt
    assert "Tasks Document" in prompt
    assert "Requirements Document" in prompt


@pytest.mark.anyio
async def test_parse_output_success(agent, workflow_state):
    content = """# Observability Strategy

## Logging Strategy
Structlog...

## Metrics & Monitoring
Prometheus...
Counter(
Gauge(

## Distributed Tracing
OTEL...

## Alerting Rules
...

## Dashboards
...
"""
    mock_response = MagicMock()
    mock_response.content = content
    mock_response.tokens_used = 100

    result = await agent._parse_output(mock_response, workflow_state)

    assert result["observability_generated"] is True
    assert result["metrics_count"] == 2
    assert result["has_logging_strategy"] is True
    assert result["has_tracing_strategy"] is True
    assert result["has_alerting_rules"] is True
    agent._write_file.assert_called_once_with("OBSERVABILITY.md", content.strip())
