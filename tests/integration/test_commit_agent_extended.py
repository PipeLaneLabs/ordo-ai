"""Integration-style tests for CommitAgent aligned with current API."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.tier_5.commit_agent import CommitAgent
from src.config import Settings
from src.llm.base_client import LLMResponse
from src.orchestration.budget_guard import BudgetGuard


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_GIT") != "1",
    reason="Requires git repository initialization and proper subprocess mocking",
)


@pytest.fixture
def commit_agent() -> CommitAgent:
    return CommitAgent(
        llm_client=MagicMock(),
        budget_guard=MagicMock(spec=BudgetGuard),
        settings=MagicMock(spec=Settings),
    )


@pytest.mark.asyncio
async def test_build_prompt_includes_git_status(commit_agent) -> None:
    state = {
        "user_request": "Add endpoint",
        "current_phase": "delivery",
        "completed_tasks": ["task-1"],
    }

    commit_agent._get_git_status = AsyncMock(return_value="Changes: M file.py")

    prompt = await commit_agent._build_prompt(state)

    assert "Add endpoint" in prompt
    assert "delivery" in prompt
    assert "task-1" in prompt
    assert "Changes: M file.py" in prompt


@pytest.mark.asyncio
async def test_parse_output_commits_when_changes(commit_agent) -> None:
    response = LLMResponse(
        content="<COMMIT_MESSAGE>feat: add thing</COMMIT_MESSAGE>",
        model="test",
        tokens_used=1,
        cost_usd=0.0,
        latency_ms=1,
        provider="test",
    )

    commit_agent._run_git_command = AsyncMock(side_effect=["", "", "M file.txt", ""])

    result = await commit_agent._parse_output(response, {})

    assert result["commit_status"] == "committed"


@pytest.mark.asyncio
async def test_parse_output_no_changes(commit_agent) -> None:
    response = LLMResponse(
        content="<COMMIT_MESSAGE>feat: add thing</COMMIT_MESSAGE>",
        model="test",
        tokens_used=1,
        cost_usd=0.0,
        latency_ms=1,
        provider="test",
    )

    commit_agent._run_git_command = AsyncMock(side_effect=["", "", "", ""])

    result = await commit_agent._parse_output(response, {})

    assert result["commit_status"] == "no_changes"


@pytest.mark.asyncio
async def test_get_git_status_not_repo(commit_agent) -> None:
    commit_agent._run_git_command = AsyncMock(side_effect=RuntimeError("fail"))

    result = await commit_agent._get_git_status()

    assert "Not in a git repository" in result


@pytest.mark.asyncio
async def test_run_git_command_success(commit_agent) -> None:
    with patch("asyncio.create_subprocess_exec", new=AsyncMock()) as mock_proc:
        process = AsyncMock()
        process.returncode = 0
        process.communicate = AsyncMock(return_value=(b"ok", b""))
        mock_proc.return_value = process

        result = await commit_agent._run_git_command(["git", "status"])

    assert result == "ok"


@pytest.mark.asyncio
async def test_run_git_command_failure(commit_agent) -> None:
    with patch("asyncio.create_subprocess_exec", new=AsyncMock()) as mock_proc:
        process = AsyncMock()
        process.returncode = 1
        process.communicate = AsyncMock(return_value=(b"", b"bad"))
        mock_proc.return_value = process

        with pytest.raises(RuntimeError):
            await commit_agent._run_git_command(["git", "status"])
