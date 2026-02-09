"""Unit tests for OrchestrationController routing and execution."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from langgraph.graph import END

from src.config import Settings
from src.exceptions import BudgetExhaustedError, InfiniteLoopDetectedError
from src.orchestration.controller import OrchestrationController


def _make_settings():
    settings = MagicMock(spec=Settings)
    settings.total_budget_tokens = 1000
    settings.max_monthly_budget_usd = 100.0
    return settings


def _state_with_budget(workflow_id: str, remaining_tokens: int) -> dict:
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


class DummyGraph:
    """Minimal graph stub to capture build operations."""

    def __init__(self, _state_type):
        self.add_node = MagicMock()
        self.add_edge = MagicMock()
        self.add_conditional_edges = MagicMock()
        self.set_entry_point = MagicMock()

    def compile(self, checkpointer=None):
        return SimpleNamespace(checkpointer=checkpointer)


class AsyncGraph:
    """Async graph stub with configurable updates."""

    def __init__(self, updates):
        self._updates = updates

    async def astream(self, _state, _config):
        for update in self._updates:
            yield update


def _make_controller():
    return OrchestrationController(
        settings=_make_settings(),
        budget_guard=MagicMock(),
        checkpoint_manager=MagicMock(),
        max_iterations=3,
    )


def test_build_graph_compiles_and_assigns():
    """Graph build compiles with checkpointer."""
    controller = _make_controller()

    with patch("src.orchestration.controller.StateGraph", DummyGraph):
        graph = controller.build_graph()

    assert graph.checkpointer == controller.checkpoint_manager
    assert controller.graph == graph


@pytest.mark.asyncio
async def test_execute_workflow_returns_final_state():
    """Return the final state from graph updates."""
    controller = _make_controller()
    workflow_id = "wf-123"

    updates = [
        {"tier_1_requirements": _state_with_budget(workflow_id, 10)},
        {"tier_2_planner": _state_with_budget(workflow_id, 5)},
    ]
    controller.graph = AsyncGraph(updates)

    result = await controller.execute_workflow("Do work", workflow_id)

    assert result["workflow_id"] == workflow_id
    assert result["budget_remaining_tokens"] == 5


@pytest.mark.asyncio
async def test_execute_workflow_budget_exhausted():
    """Raise when budget is exhausted."""
    controller = _make_controller()
    workflow_id = "wf-999"

    updates = [{"tier_1_requirements": _state_with_budget(workflow_id, 0)}]
    controller.graph = AsyncGraph(updates)

    with pytest.raises(BudgetExhaustedError):
        await controller.execute_workflow("Do work", workflow_id)


@pytest.mark.asyncio
async def test_execute_workflow_infinite_loop():
    """Raise when iteration limit is exceeded."""
    controller = _make_controller()
    controller.max_iterations = 1
    workflow_id = "wf-loop"

    updates = [
        {"tier_1_requirements": _state_with_budget(workflow_id, 10)},
        {"tier_2_planner": _state_with_budget(workflow_id, 10)},
    ]
    controller.graph = AsyncGraph(updates)

    with pytest.raises(InfiniteLoopDetectedError):
        await controller.execute_workflow("Do work", workflow_id)


@pytest.mark.asyncio
async def test_tier_nodes_update_state():
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


def test_routing_functions():
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
