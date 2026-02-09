"""Additional tests for DeviationHandlerAgent to improve coverage."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.tier_0.deviation_handler import DeviationHandlerAgent
from src.config import Settings
from src.exceptions import HumanApprovalTimeoutError, WorkflowError
from src.llm.base_client import LLMResponse
from src.orchestration.budget_guard import BudgetGuard


@pytest.fixture
def handler() -> DeviationHandlerAgent:
    settings = MagicMock(spec=Settings)
    settings.human_approval_timeout = 60
    return DeviationHandlerAgent(
        llm_client=MagicMock(),
        budget_guard=MagicMock(spec=BudgetGuard),
        settings=settings,
        max_routing_iterations=2,
        max_log_entries=1,
    )


def _state() -> dict:
    return {
        "workflow_id": "wf-1",
        "user_request": "Do work",
        "current_phase": "planning",
        "current_agent": "Validator",
        "rejection_count": 0,
        "blocking_issues": ["issue"],
        "code_files": {},
        "test_files": {},
        "routing_decision": {},
    }


@pytest.mark.asyncio
async def test_parse_output_valid_json(handler) -> None:
    response = LLMResponse(
        content='{"root_cause":"x","target_agent":"QualityEngineer","reasoning":"y","circular_routing_detected":false,"escalate_to_human":false,"recommended_action":"fix"}',
        model="test",
        tokens_used=1,
        cost_usd=0.0,
        latency_ms=1,
        provider="test",
    )

    with patch.object(handler, "_append_deviation_log", new=AsyncMock()):
        result = await handler._parse_output(response, _state())

    assert result["routing_decision"]["target_agent"] == "tier_3_quality"


@pytest.mark.asyncio
async def test_build_prompt_includes_context(handler) -> None:
    state = _state()

    prompt = await handler._build_prompt(
        state,
        rejection_reason="Tests failed",
        rejecting_agent="QualityEngineer",
    )

    assert "Tests failed" in prompt
    assert "QualityEngineer" in prompt


@pytest.mark.asyncio
async def test_append_deviation_log_writes_entry(handler) -> None:
    state = _state()
    analysis = {
        "root_cause": "x",
        "target_agent": "QualityEngineer",
        "reasoning": "y",
        "recommended_action": "fix",
        "circular_routing_detected": False,
        "escalate_to_human": False,
    }

    with (
        patch.object(handler, "_maybe_archive_log", new=AsyncMock()),
        patch.object(handler, "_append_to_file", new=AsyncMock()) as append_file,
    ):
        await handler._append_deviation_log(state, analysis)

    append_file.assert_called_once()


@pytest.mark.asyncio
async def test_parse_output_invalid_json_fallback(handler) -> None:
    response = LLMResponse(
        content="not-json",
        model="test",
        tokens_used=1,
        cost_usd=0.0,
        latency_ms=1,
        provider="test",
    )

    with patch.object(handler, "_append_deviation_log", new=AsyncMock()):
        result = await handler._parse_output(response, _state())

    assert result["routing_decision"]["target_agent"] == "tier_3_engineer"


@pytest.mark.asyncio
async def test_parse_output_escalates_on_max_iterations(handler) -> None:
    response = LLMResponse(
        content='{"root_cause":"x","target_agent":"QualityEngineer","reasoning":"y","circular_routing_detected":false,"escalate_to_human":false,"recommended_action":"fix"}',
        model="test",
        tokens_used=1,
        cost_usd=0.0,
        latency_ms=1,
        provider="test",
    )
    state = _state()
    state["rejection_count"] = 2

    with (
        patch.object(handler, "_append_deviation_log", new=AsyncMock()),
        pytest.raises(HumanApprovalTimeoutError),
    ):
        await handler._parse_output(response, state)


def test_format_blocking_issues(handler) -> None:
    assert handler._format_blocking_issues([]) == "None"
    assert "- a" in handler._format_blocking_issues(["a"])


def test_map_agent_to_tier_default(handler) -> None:
    assert handler._map_agent_to_tier("UnknownAgent") == "tier_3_engineer"


def test_check_circular_routing(handler) -> None:
    state = _state()
    state["routing_decision"] = {"target_agent": "QualityEngineer"}
    state["rejection_count"] = 2

    assert handler._check_circular_routing(state, "QualityEngineer") is True


@pytest.mark.asyncio
async def test_log_deviation_updates_state(handler) -> None:
    state = _state()

    with patch.object(handler, "_append_to_file", new=AsyncMock()):
        updated = await handler.log_deviation(state, ValueError("bad"))

    assert "deviations" in updated
    assert updated["last_error"] == "bad"


@pytest.mark.asyncio
async def test_maybe_archive_log_archives(handler, tmp_path) -> None:
    log_path = tmp_path / "DEVIATION_LOG.md"
    log_path.write_text("## Deviation Entry\n## Deviation Entry\n", encoding="utf-8")
    handler.deviation_log_path = log_path

    with (
        patch.object(
            handler,
            "_read_if_exists",
            new=AsyncMock(return_value=log_path.read_text(encoding="utf-8")),
        ),
        patch.object(handler, "_write_file", new=AsyncMock()) as write_file,
    ):
        await handler._maybe_archive_log()

    assert write_file.call_count == 2


@pytest.mark.asyncio
async def test_attempt_recovery_max_retries(handler) -> None:
    state = _state()
    state["retry_count"] = 3

    with pytest.raises(WorkflowError):
        await handler.attempt_recovery(state, RuntimeError("fail"), max_retries=3)


@pytest.mark.asyncio
async def test_rollback_state_with_checkpoint_manager(handler) -> None:
    state = _state()
    checkpoint = SimpleNamespace(checkpoint_id="ckpt-1")
    manager = MagicMock()
    manager.alist = AsyncMock(return_value=[checkpoint, checkpoint])

    result = await handler.rollback_state(state, checkpoint_manager=manager)

    assert result["rollback_performed"] is True


@pytest.mark.asyncio
async def test_escalate_to_human_sets_flags(handler) -> None:
    state = _state()

    with (
        patch.object(handler, "_append_to_file", new=AsyncMock()),
        pytest.raises(HumanApprovalTimeoutError),
    ):
        await handler.escalate_to_human(state, reason="Needs review")


def test_format_dict(handler) -> None:
    assert handler._format_dict({}) == "None"
    assert "key" in handler._format_dict({"key": "value"})
