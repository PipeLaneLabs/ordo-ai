"""Additional BudgetGuard tests to cover async paths and summaries."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import BudgetExhaustedError
from src.orchestration.budget_guard import BudgetGuard


class _FakeCache:
    def __init__(self, data: dict | None = None, connect_error: bool = False) -> None:
        self._data = data
        self._connect_error = connect_error
        self.set_calls: list[tuple[str, str, int | None]] = []

    async def connect(self) -> None:
        if self._connect_error:
            raise RuntimeError("connect failed")

    async def get(self, _key: str) -> str | None:
        if self._data is None:
            return None
        return json.dumps(self._data)

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        self.set_calls.append((key, value, ttl_seconds))


def _state() -> dict:
    return {
        "workflow_id": "wf-1",
        "budget_used_tokens": 50,
        "budget_used_usd": 5.0,
        "budget_remaining_tokens": 50,
        "budget_remaining_usd": 45.0,
        "agent_token_usage": {"agent": 10},
    }


def test_reserve_budget_warns_on_token_threshold() -> None:
    guard = BudgetGuard(
        max_tokens_per_workflow=100,
        max_monthly_budget_usd=100.0,
        alert_threshold_pct=75.0,
    )
    state = _state()

    result = guard.reserve_budget(
        "op", estimated_tokens=30, estimated_cost_usd=1.0, workflow_state=state
    )

    assert result["allowed"] is True
    assert result["alert"] is not None


def test_reserve_budget_warns_on_cost_threshold() -> None:
    guard = BudgetGuard(
        max_tokens_per_workflow=100,
        max_monthly_budget_usd=10.0,
        alert_threshold_pct=75.0,
    )
    state = _state()
    state["budget_used_tokens"] = 10
    state["budget_remaining_tokens"] = 90
    state["budget_used_usd"] = 7.0
    state["budget_remaining_usd"] = 3.0

    result = guard.reserve_budget(
        "op", estimated_tokens=5, estimated_cost_usd=1.0, workflow_state=state
    )

    assert result["allowed"] is True
    assert result["alert"] is not None


@pytest.mark.asyncio
async def test_check_budget_requires_workflow_id() -> None:
    guard = BudgetGuard()

    with pytest.raises(ValueError):
        await guard.check_budget(workflow_state=None, estimated_tokens=1)


@pytest.mark.asyncio
async def test_check_budget_with_workflow_id_uses_cache() -> None:
    cache = _FakeCache({"tokens_used": 10, "cost_used": 1.0})
    guard = BudgetGuard(
        max_tokens_per_workflow=100,
        max_monthly_budget_usd=10.0,
        cache=cache,
    )

    result = await guard.check_budget(
        workflow_state=None,
        workflow_id="wf-1",
        estimated_tokens=5,
        estimated_cost_usd=1.0,
    )

    assert result["allowed"] is True
    assert result["remaining_tokens"] == 90


@pytest.mark.asyncio
async def test_check_budget_raises_when_over_limit() -> None:
    cache = _FakeCache({"tokens_used": 99, "cost_used": 1.0})
    guard = BudgetGuard(
        max_tokens_per_workflow=100,
        max_monthly_budget_usd=10.0,
        cache=cache,
    )

    with pytest.raises(BudgetExhaustedError):
        await guard.check_budget(
            workflow_state=None,
            workflow_id="wf-1",
            estimated_tokens=5,
            estimated_cost_usd=1.0,
        )


@pytest.mark.asyncio
async def test_reserve_budget_async_persists_to_cache() -> None:
    cache = _FakeCache({"tokens_used": 1, "cost_used": 1.0})
    guard = BudgetGuard(
        max_tokens_per_workflow=100,
        max_monthly_budget_usd=10.0,
        cache=cache,
    )

    mock_logger = MagicMock()
    mock_logger.bind.return_value = mock_logger
    mock_logger.new.return_value = mock_logger
    mock_logger.current_timestamp = "now"

    logger_wrapper = MagicMock()
    logger_wrapper.get_logger.return_value = mock_logger

    with (
        patch.object(
            guard,
            "check_budget",
            new=AsyncMock(return_value={"allowed": True}),
        ),
        patch("src.orchestration.budget_guard.logger", logger_wrapper),
    ):
        result = await guard.reserve_budget_async(
            operation_name="op",
            estimated_tokens=5,
            estimated_cost_usd=1.0,
            workflow_id="wf-1",
        )

    assert result["reserved"] is True
    assert cache.set_calls


@pytest.mark.asyncio
async def test_ensure_cache_connected_handles_failure() -> None:
    cache = _FakeCache(connect_error=True)
    guard = BudgetGuard(cache=cache)

    with patch("src.orchestration.budget_guard.logger.warning") as mock_warn:
        await guard._ensure_cache_connected()

    mock_warn.assert_called_once()


def test_record_usage_updates_monthly_total() -> None:
    guard = BudgetGuard(max_monthly_budget_usd=10.0)
    state = _state()

    with patch("src.orchestration.budget_guard.logger.info"):
        guard.record_usage("op", tokens_used=2, cost_usd=1.5, workflow_state=state)

    assert guard.current_month_used_usd == 1.5


def test_get_budget_summary_flags_thresholds() -> None:
    guard = BudgetGuard(max_tokens_per_workflow=100, max_monthly_budget_usd=10.0)
    state = _state()
    state["budget_used_tokens"] = 80
    state["budget_remaining_tokens"] = 20
    state["budget_used_usd"] = 8.0
    state["budget_remaining_usd"] = 2.0

    summary = guard.get_budget_summary(state)

    assert summary["tokens"]["at_threshold"] is True
    assert summary["cost"]["at_threshold"] is True
