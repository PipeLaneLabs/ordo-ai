"""Unit tests for OrchestrationController routing and execution."""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from langgraph.graph import END

from src.config import Settings
from src.exceptions import BudgetExhaustedError, InfiniteLoopDetectedError
from src.orchestration.controller import OrchestrationController
from src.orchestration.state import WorkflowState, create_initial_state


def _make_settings() -> Settings:
    settings = MagicMock(spec=Settings)
    settings.total_budget_tokens = 1000
    settings.max_monthly_budget_usd = 100.0
    return settings


def _state_with_budget(workflow_id: str, remaining_tokens: int) -> WorkflowState:
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


class DummyGraph:
    """Minimal graph stub to capture build operations."""

    def __init__(self, _state_type: type[Any]) -> None:
        self.add_node = MagicMock()
        self.add_edge = MagicMock()
        self.add_conditional_edges = MagicMock()
        self.set_entry_point = MagicMock()

    def compile(self, checkpointer: object | None = None) -> SimpleNamespace:
        return SimpleNamespace(checkpointer=checkpointer)


class AsyncGraph:
    """Async graph stub with configurable updates."""

    def __init__(self, updates: list[dict[str, WorkflowState]]) -> None:
        self._updates = updates

    async def astream(
        self, _state: WorkflowState, _config: dict[str, object]
    ) -> AsyncIterator[dict[str, WorkflowState]]:
        for update in self._updates:
            yield update


def _make_controller() -> OrchestrationController:
    return OrchestrationController(
        settings=_make_settings(),
        budget_guard=MagicMock(),
        checkpoint_manager=MagicMock(),
        max_iterations=3,
    )


def test_build_graph_compiles_and_assigns() -> None:
    """Graph build compiles with checkpointer."""
    controller = _make_controller()

    with patch("src.orchestration.controller.StateGraph", DummyGraph):
        graph = controller.build_graph()

    assert graph.checkpointer == controller.checkpoint_manager
    assert controller.graph == graph


@pytest.mark.asyncio
async def test_execute_workflow_returns_final_state() -> None:
    """Return the final state from graph updates."""
    controller = _make_controller()
    workflow_id = "wf-123"

    updates = [
        {"tier_1_requirements": _state_with_budget(workflow_id, 10)},
        {"tier_2_planner": _state_with_budget(workflow_id, 5)},
    ]
    controller.graph = cast(Any, AsyncGraph(updates))

    result = await controller.execute_workflow("Do work", workflow_id)

    assert result["workflow_id"] == workflow_id
    assert result["budget_remaining_tokens"] == 5


@pytest.mark.asyncio
async def test_execute_workflow_budget_exhausted() -> None:
    """Raise when budget is exhausted."""
    controller = _make_controller()
    workflow_id = "wf-999"

    updates = [{"tier_1_requirements": _state_with_budget(workflow_id, 0)}]
    controller.graph = cast(Any, AsyncGraph(updates))

    with pytest.raises(BudgetExhaustedError):
        await controller.execute_workflow("Do work", workflow_id)


@pytest.mark.asyncio
async def test_execute_workflow_infinite_loop() -> None:
    """Raise when iteration limit is exceeded."""
    controller = _make_controller()
    controller.max_iterations = 1
    workflow_id = "wf-loop"

    updates = [
        {"tier_1_requirements": _state_with_budget(workflow_id, 10)},
        {"tier_2_planner": _state_with_budget(workflow_id, 10)},
    ]
    controller.graph = cast(Any, AsyncGraph(updates))

    with pytest.raises(InfiniteLoopDetectedError):
        await controller.execute_workflow("Do work", workflow_id)


@pytest.mark.asyncio
async def test_tier_nodes_update_state() -> None:
    """Tier node handlers set expected agent and phase."""
    controller = _make_controller()
    state = _state_with_budget("wf-1", 10)

    state = await controller._tier_1_requirements(state)
    assert state["current_agent"] == "RequirementsStrategy"
    assert state["current_phase"] == "planning"

    state = await controller._tier_3_engineer(state)
    assert state["current_agent"] == "SoftwareEngineer"
    assert state["current_phase"] == "development"

    state = await controller._tier_5_deployment(state)
    assert state["current_agent"] == "DeploymentAgent"
    assert state["current_phase"] == "completed"


def test_routing_functions() -> None:
    """Routing respects blocking issues and escalation rules."""
    controller = _make_controller()
    state = _state_with_budget("wf-1", 10)

    assert controller._route_validator_output(state) == "tier_1_architect"

    state["blocking_issues"] = ["issue"]
    assert controller._route_validator_output(state) == "tier_0_deviation"

    state["blocking_issues"] = []
    assert controller._route_deviation_output(state) == "tier_1_requirements"

    state["escalation_flag"] = True
    assert controller._route_deviation_output(state) == END

    state["escalation_flag"] = False
    state["rejection_count"] = 3
    assert controller._route_deviation_output(state) == END
