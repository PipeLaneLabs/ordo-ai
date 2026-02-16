"""Integration-style tests for OrchestrationController aligned to current API."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from langgraph.graph import END

from src.config import Settings
from src.exceptions import BudgetExhaustedError, InfiniteLoopDetectedError
from src.orchestration.controller import OrchestrationController
from src.orchestration.state import WorkflowState, create_initial_state


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="Requires LangGraph routing setup",
)


class AsyncGraph:
    def __init__(self, updates: list[dict[str, WorkflowState]]) -> None:
        self._updates = updates

    async def astream(
        self, _state: WorkflowState, _config: dict[str, object]
    ) -> AsyncIterator[dict[str, WorkflowState]]:
        for update in self._updates:
            yield update


def _make_state(workflow_id: str, remaining_tokens: int) -> WorkflowState:
    state = create_initial_state(workflow_id, "test request", workflow_id)
    state["current_agent"] = "TestAgent"
    state["current_phase"] = "planning"
    state["budget_remaining_tokens"] = remaining_tokens
    state["budget_used_tokens"] = 10
    state["budget_remaining_usd"] = 10.0
    state["budget_used_usd"] = 0.5
    state["blocking_issues"] = []
    state["routing_decision"] = {}
    state["rejection_count"] = 0
    state["escalation_flag"] = False
    return state


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
async def test_execute_workflow_happy_path(
    controller: OrchestrationController,
) -> None:
    workflow_id = "wf-1"
    controller.graph = cast(
        Any,
        AsyncGraph(
            [
                {"tier_1_requirements": _make_state(workflow_id, 10)},
                {"tier_2_planner": _make_state(workflow_id, 5)},
            ]
        ),
    )

    result = await controller.execute_workflow("Do work", workflow_id)

    assert result["workflow_id"] == workflow_id
    assert result["budget_remaining_tokens"] == 5


@pytest.mark.asyncio
async def test_execute_workflow_budget_exhausted(
    controller: OrchestrationController,
) -> None:
    workflow_id = "wf-2"
    controller.graph = cast(
        Any,
        AsyncGraph([{"tier_1_requirements": _make_state(workflow_id, 0)}]),
    )

    with pytest.raises(BudgetExhaustedError):
        await controller.execute_workflow("Do work", workflow_id)


@pytest.mark.asyncio
async def test_execute_workflow_infinite_loop(
    controller: OrchestrationController,
) -> None:
    controller.max_iterations = 1
    workflow_id = "wf-3"
    controller.graph = cast(
        Any,
        AsyncGraph(
            [
                {"tier_1_requirements": _make_state(workflow_id, 10)},
                {"tier_2_planner": _make_state(workflow_id, 10)},
            ]
        ),
    )

    with pytest.raises(InfiniteLoopDetectedError):
        await controller.execute_workflow("Do work", workflow_id)


def test_routing_functions(controller: OrchestrationController) -> None:
    state = _make_state("wf-4", 10)

    assert controller._route_validator_output(state) == "tier_1_architect"

    state["blocking_issues"] = ["issue"]
    assert controller._route_validator_output(state) == "tier_0_deviation"

    state["blocking_issues"] = []
    assert controller._route_deviation_output(state) == "tier_1_requirements"

    state["escalation_flag"] = True
    assert controller._route_deviation_output(state) == END
