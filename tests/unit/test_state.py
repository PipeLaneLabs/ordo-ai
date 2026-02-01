"""Unit tests for workflow state management."""

from src.orchestration.state import (
    create_initial_state,
    increment_rejection_count,
    update_budget,
)


def test_create_initial_state() -> None:
    """Test initial state creation implies default values."""
    wf_id = "wf-123"
    request = "build a bot"
    trace_id = "trace-456"

    state = create_initial_state(wf_id, request, trace_id)

    assert state["workflow_id"] == wf_id
    assert state["user_request"] == request
    assert state["trace_id"] == trace_id
    assert state["current_phase"] == "planning"
    assert state["rejection_count"] == 0
    assert state["budget_remaining_tokens"] == 500_000
    assert state["budget_remaining_usd"] == 20.0
    assert state["code_files"] == {}


def test_increment_rejection_count() -> None:
    """Test rejection count increment."""
    state = create_initial_state("id", "req", "trace")
    initial_version = state["state_version"]

    new_state = increment_rejection_count(state)

    assert new_state["rejection_count"] == 1
    assert new_state["state_version"] == initial_version + 1
    assert new_state["workflow_id"] == state["workflow_id"]  # Preserves other fields


def test_update_budget() -> None:
    """Test budget deduction and tracking."""
    state = create_initial_state("id", "req", "trace")
    initial_tokens = state["budget_remaining_tokens"]
    initial_usd = state["budget_remaining_usd"]

    tokens_used = 1000
    cost = 0.05
    agent = "TestAgent"

    new_state = update_budget(state, tokens_used, cost, agent)

    assert new_state["budget_used_tokens"] == tokens_used
    assert new_state["budget_used_usd"] == cost
    assert new_state["budget_remaining_tokens"] == initial_tokens - tokens_used
    assert new_state["budget_remaining_usd"] == initial_usd - cost
    assert new_state["agent_token_usage"][agent] == tokens_used
    assert new_state["state_version"] == state["state_version"] + 1
