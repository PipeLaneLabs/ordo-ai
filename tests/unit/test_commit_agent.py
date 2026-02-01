"""Unit tests for CommitAgent.

Tests the Commit Agent's commit message generation, parsing,
and git operations.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.tier_5.commit_agent import CommitAgent
from src.config import Settings
from src.llm.base_client import LLMResponse


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = AsyncMock()
    client.generate = AsyncMock(
        return_value=LLMResponse(
            content="<COMMIT_MESSAGE>\nfeat: add new feature\n</COMMIT_MESSAGE>",
            model="deepseek/deepseek-chat",
            tokens_used=100,
            cost_usd=0.0001,
            latency_ms=500,
            provider="openrouter",
        )
    )
    return client


@pytest.fixture
def mock_budget_guard():
    """Mock budget guard for testing."""
    guard = MagicMock()
    guard.reserve_budget = MagicMock()
    guard.record_usage = MagicMock()
    return guard


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return Settings()


@pytest.fixture
def commit_agent(mock_llm_client, mock_budget_guard, mock_settings):
    """Create CommitAgent instance for testing."""
    return CommitAgent(
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
    )


def test_initialization(commit_agent):
    """Test CommitAgent initializes correctly."""
    assert commit_agent.name == "CommitAgent"
    assert commit_agent.token_budget == 2000


def test_get_temperature(commit_agent):
    """Test temperature is 0.2 for commit message generation."""
    assert commit_agent._get_temperature() == 0.2


def test_estimate_cost(commit_agent):
    """Test cost estimation for 2,000 tokens."""
    cost = commit_agent._estimate_cost()
    assert cost == (2000 / 1_000_000) * 1.0
    assert cost == 0.002


@pytest.mark.asyncio
async def test_parse_output_with_commit_message(commit_agent):
    """Test parsing commit message from LLM response."""
    response = LLMResponse(
        content="<COMMIT_MESSAGE>\nfeat: add new feature\n</COMMIT_MESSAGE>",
        model="deepseek/deepseek-chat",
        tokens_used=100,
        cost_usd=0.0001,
        latency_ms=500,
        provider="openrouter",
    )

    with patch.object(commit_agent, "_run_git_command", new=AsyncMock()) as mock_git:
        mock_git.side_effect = RuntimeError("not a git repository")
        result = await commit_agent._parse_output(response, {})

        assert "commit_message" in result
        assert result["commit_message"] == "Not in git repository"


@pytest.mark.asyncio
async def test_parse_output_no_commit_tags(commit_agent):
    """Test handling response without commit message tags."""
    response = LLMResponse(
        content="This is just a plain message without tags.",
        model="deepseek/deepseek-chat",
        tokens_used=50,
        cost_usd=0.00005,
        latency_ms=300,
        provider="openrouter",
    )

    with patch.object(commit_agent, "_run_git_command", new=AsyncMock()) as mock_git:
        mock_git.side_effect = RuntimeError("not a git repository")
        result = await commit_agent._parse_output(response, {})

        assert "commit_message" in result
        assert result["commit_message"] == "Not in git repository"


@pytest.mark.asyncio
async def test_git_operations_with_changes(commit_agent):
    """Test git operations when there are changes to commit."""
    response = LLMResponse(
        content="<COMMIT_MESSAGE>\nfeat: add new feature\n</COMMIT_MESSAGE>",
        model="deepseek/deepseek-chat",
        tokens_used=100,
        cost_usd=0.0001,
        latency_ms=500,
        provider="openrouter",
    )

    with patch.object(commit_agent, "_run_git_command", new=AsyncMock()) as mock_git:
        # Mock git status showing changes
        mock_git.side_effect = ["", "", "M file.txt", ""]

        result = await commit_agent._parse_output(response, {})

        assert result["commit_message"] == "feat: add new feature"
        # Should call: rev-parse, add, status, commit
        assert mock_git.call_count == 4


@pytest.mark.asyncio
async def test_git_operations_no_changes(commit_agent):
    """Test git operations when there are no changes to commit."""
    response = LLMResponse(
        content="<COMMIT_MESSAGE>\nfeat: add new feature\n</COMMIT_MESSAGE>",
        model="deepseek/deepseek-chat",
        tokens_used=100,
        cost_usd=0.0001,
        latency_ms=500,
        provider="openrouter",
    )

    with patch.object(commit_agent, "_run_git_command", new=AsyncMock()) as mock_git:
        # Mock git status showing no changes
        mock_git.side_effect = ["", "", "", ""]

        result = await commit_agent._parse_output(response, {})

        assert result["commit_message"] == "No changes to commit"
        # Should call: rev-parse, add, status (no commit)
        assert mock_git.call_count == 3


@pytest.mark.asyncio
async def test_git_operations_not_repository(commit_agent):
    """Test handling when not in a git repository."""
    response = LLMResponse(
        content="<COMMIT_MESSAGE>\nfeat: add new feature\n</COMMIT_MESSAGE>",
        model="deepseek/deepseek-chat",
        tokens_used=100,
        cost_usd=0.0001,
        latency_ms=500,
        provider="openrouter",
    )

    with patch.object(commit_agent, "_run_git_command", new=AsyncMock()) as mock_git:
        # Mock git rev-parse failing
        mock_git.side_effect = RuntimeError("fatal: not a git repository")

        result = await commit_agent._parse_output(response, {})

        assert result["commit_message"] == "Not in git repository"


@pytest.mark.asyncio
async def test_run_git_command_success(commit_agent):
    """Test successful git command execution."""
    with patch("asyncio.create_subprocess_exec", new=AsyncMock()) as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_subprocess.return_value = mock_process

        result = await commit_agent._run_git_command(["git", "status"])

        assert result == "output"
        mock_subprocess.assert_called_once()


@pytest.mark.asyncio
async def test_run_git_command_failure(commit_agent):
    """Test git command execution failure."""
    with patch("asyncio.create_subprocess_exec", new=AsyncMock()) as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"error message"))
        mock_subprocess.return_value = mock_process

        with pytest.raises(RuntimeError, match="Git command failed"):
            await commit_agent._run_git_command(["git", "invalid"])
