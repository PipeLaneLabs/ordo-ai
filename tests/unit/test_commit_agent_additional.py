"""Additional tests for CommitAgent prompt building and status handling."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.tier_5.commit_agent import CommitAgent
from src.config import Settings
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState, create_initial_state


@pytest.fixture
def commit_agent() -> CommitAgent:
    return CommitAgent(
        llm_client=MagicMock(),
        budget_guard=MagicMock(spec=BudgetGuard),
        settings=MagicMock(spec=Settings),
    )


@pytest.mark.asyncio
async def test_build_prompt_includes_context(commit_agent: CommitAgent) -> None:
    base_state = create_initial_state(
        workflow_id="wf-1",
        user_request="Add endpoint",
        trace_id="trace-1",
    )
    state = cast(
        WorkflowState,
        {
            **base_state,
            "current_phase": "delivery",
            "completed_tasks": ["task-1"],
        },
    )

    with patch.object(
        commit_agent,
        "_get_git_status",
        new=AsyncMock(return_value="Changes: M file.py"),
    ):
        prompt = await commit_agent._build_prompt(state)

    assert "Add endpoint" in prompt
    assert "delivery" in prompt
    assert "task-1" in prompt
    assert "Changes: M file.py" in prompt


@pytest.mark.asyncio
async def test_get_git_status_no_changes(commit_agent: CommitAgent) -> None:
    with patch.object(commit_agent, "_run_git_command", new=AsyncMock(return_value="")):
        result = await commit_agent._get_git_status()

    assert result == "No changes detected"


@pytest.mark.asyncio
async def test_get_git_status_not_git_repo(commit_agent: CommitAgent) -> None:
    with patch.object(
        commit_agent,
        "_run_git_command",
        new=AsyncMock(side_effect=RuntimeError("fail")),
    ):
        result = await commit_agent._get_git_status()

    assert "Not in a git repository" in result
