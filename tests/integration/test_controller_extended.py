"""Integration-style tests for OrchestrationController aligned to current API."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from langgraph.graph import END

from src.config import Settings
from src.exceptions import BudgetExhaustedError, InfiniteLoopDetectedError
from src.orchestration.controller import OrchestrationController


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="Requires LangGraph routing setup",
)


class AsyncGraph:
    def __init__(self, updates):
        self._updates = updates

    async def astream(self, _state, _config):
        for update in self._updates:
            yield update


def _make_state(workflow_id: str, remaining_tokens: int) -> dict:
    return {
        "workflow_id": workflow_id,
        "current_agent": "TestAgent",
        "current_phase": "planning",
        "budget_remaining_tokens": remaining_tokens,
        "budget_used_tokens": 10,
        "budget_remaining_usd": 10.0,
        "budget_used_usd": 0.5,
        "blocking_issues": [],
        "routing_decision": {},
        "rejection_count": 0,
        "escalation_flag": False,
    }


@pytest.fixture
def controller() -> OrchestrationController:
    settings = MagicMock(spec=Settings)
    settings.total_budget_tokens = 1000
    settings.max_monthly_budget_usd = 100.0

    return OrchestrationController(
        settings=settings,
        budget_guard=MagicMock(),
        checkpoint_manager=MagicMock(),
        max_iterations=3,
    )


@pytest.mark.asyncio
async def test_execute_workflow_happy_path(controller) -> None:
    workflow_id = "wf-1"
    controller.graph = AsyncGraph(
        [
            {"tier_1_requirements": _make_state(workflow_id, 10)},
            {"tier_2_planner": _make_state(workflow_id, 5)},
        ]
    )

    result = await controller.execute_workflow("Do work", workflow_id)

    assert result["workflow_id"] == workflow_id
    assert result["budget_remaining_tokens"] == 5


@pytest.mark.asyncio
async def test_execute_workflow_budget_exhausted(controller) -> None:
    workflow_id = "wf-2"
    controller.graph = AsyncGraph(
        [{"tier_1_requirements": _make_state(workflow_id, 0)}]
    )

    with pytest.raises(BudgetExhaustedError):
        await controller.execute_workflow("Do work", workflow_id)


@pytest.mark.asyncio
async def test_execute_workflow_infinite_loop(controller) -> None:
    controller.max_iterations = 1
    workflow_id = "wf-3"
    controller.graph = AsyncGraph(
        [
            {"tier_1_requirements": _make_state(workflow_id, 10)},
            {"tier_2_planner": _make_state(workflow_id, 10)},
        ]
    )

    with pytest.raises(InfiniteLoopDetectedError):
        await controller.execute_workflow("Do work", workflow_id)


def test_routing_functions(controller) -> None:
    state = _make_state("wf-4", 10)

    assert controller._route_validator_output(state) == "tier_1_architect"

    state["blocking_issues"] = ["issue"]
    assert controller._route_validator_output(state) == "tier_0_deviation"

    state["blocking_issues"] = []
    assert controller._route_deviation_output(state) == "tier_1_requirements"

    state["escalation_flag"] = True
    assert controller._route_deviation_output(state) == END
