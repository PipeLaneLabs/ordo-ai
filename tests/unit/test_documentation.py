"""Unit tests for DocumentationAgent.

Tests the Documentation Agent's documentation generation, parsing,
and file creation capabilities.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.tier_5.documentation import DocumentationAgent
from src.config import Settings
from src.llm.base_client import LLMResponse


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = AsyncMock()
    client.generate = AsyncMock(
        return_value=LLMResponse(
            content="# Project Title\n\nThis is a README file.",
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
def documentation_agent(mock_llm_client, mock_budget_guard, mock_settings):
    """Create DocumentationAgent instance for testing."""
    return DocumentationAgent(
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
    )


def test_initialization(documentation_agent):
    """Test DocumentationAgent initializes correctly."""
    assert documentation_agent.name == "DocumentationAgent"
    assert documentation_agent.token_budget == 8000


def test_get_temperature(documentation_agent):
    """Test temperature is 0.3 for documentation generation."""
    assert documentation_agent._get_temperature() == 0.3


def test_estimate_cost(documentation_agent):
    """Test cost estimation for 8,000 tokens."""
    cost = documentation_agent._estimate_cost()
    assert cost == (8000 / 1_000_000) * 1.0
    assert cost == 0.008


@pytest.mark.asyncio
async def test_parse_output_readme(documentation_agent):
    """Test parsing README content from LLM response."""
    response = LLMResponse(
        content="# Project Title\n\nThis is a README file.",
        model="deepseek/deepseek-chat",
        tokens_used=100,
        cost_usd=0.0001,
        latency_ms=500,
        provider="openrouter",
    )

    with patch.object(
        documentation_agent, "_write_file", new=AsyncMock()
    ) as mock_write:
        result = await documentation_agent._parse_output(response, {})

        assert "documentation_files" in result
        assert "README.md" in result["documentation_files"]
        mock_write.assert_called_once_with(
            "README.md", "# Project Title\n\nThis is a README file."
        )


@pytest.mark.asyncio
async def test_parse_output_structured_format(documentation_agent):
    """Test parsing structured XML-like format from LLM response."""
    response = LLMResponse(
        content="""<file name="README.md">
# Project Title

This is documentation.
</file>

<file name="docs/API_REFERENCE.md">
# API Reference

Endpoint documentation here.
</file>""",
        model="deepseek/deepseek-chat",
        tokens_used=200,
        cost_usd=0.0002,
        latency_ms=600,
        provider="openrouter",
    )

    with patch.object(
        documentation_agent, "_write_file", new=AsyncMock()
    ) as mock_write:
        result = await documentation_agent._parse_output(response, {})

        assert "documentation_files" in result
        assert len(result["documentation_files"]) == 2
        assert "README.md" in result["documentation_files"]
        assert "docs/API_REFERENCE.md" in result["documentation_files"]
        assert mock_write.call_count == 2


@pytest.mark.asyncio
async def test_parse_output_no_valid_files(documentation_agent):
    """Test handling of response with no valid documentation files."""
    response = LLMResponse(
        content="This is just plain text with no structured content.",
        model="deepseek/deepseek-chat",
        tokens_used=50,
        cost_usd=0.00005,
        latency_ms=300,
        provider="openrouter",
    )

    with pytest.raises(
        ValueError, match="No valid documentation files could be parsed"
    ):
        await documentation_agent._parse_output(response, {})
