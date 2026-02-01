"""Unit tests for DeploymentAgent.

Tests the Deployment Agent's deployment configuration generation, parsing,
and file creation capabilities.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.tier_5.deployment import DeploymentAgent
from src.config import Settings
from src.llm.base_client import LLMResponse


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = AsyncMock()
    client.generate = AsyncMock(
        return_value=LLMResponse(
            content='<FILE name="docker/docker-compose.yml">\nversion: "3.8"\n</FILE>',
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
def deployment_agent(mock_llm_client, mock_budget_guard, mock_settings):
    """Create DeploymentAgent instance for testing."""
    return DeploymentAgent(
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
    )


def test_initialization(deployment_agent):
    """Test DeploymentAgent initializes correctly."""
    assert deployment_agent.name == "DeploymentAgent"
    assert deployment_agent.token_budget == 4000


def test_get_temperature(deployment_agent):
    """Test temperature is 0.1 for deployment configuration."""
    assert deployment_agent._get_temperature() == 0.1


def test_estimate_cost(deployment_agent):
    """Test cost estimation for 4,000 tokens."""
    cost = deployment_agent._estimate_cost()
    assert cost == (4000 / 1_000_000) * 1.0
    assert cost == 0.004


@pytest.mark.asyncio
async def test_parse_output_single_file(deployment_agent):
    """Test parsing single deployment file from LLM response."""
    response = LLMResponse(
        content='<FILE name="docker/docker-compose.yml">\nversion: "3.8"\nservices:\n  app:\n    image: myapp\n</FILE>',
        model="deepseek/deepseek-chat",
        tokens_used=100,
        cost_usd=0.0001,
        latency_ms=500,
        provider="openrouter",
    )

    with patch.object(deployment_agent, "_write_file", new=AsyncMock()) as mock_write:
        result = await deployment_agent._parse_output(response, {})

        assert "deployment_files" in result
        assert "docker/docker-compose.yml" in result["deployment_files"]
        mock_write.assert_called_once_with(
            "docker/docker-compose.yml",
            'version: "3.8"\nservices:\n  app:\n    image: myapp',
        )


@pytest.mark.asyncio
async def test_parse_output_multiple_files(deployment_agent):
    """Test parsing multiple deployment files from LLM response."""
    response = LLMResponse(
        content="""<FILE name="docker/Dockerfile">
FROM python:3.9
COPY . /app
</FILE>

<FILE name=".github/workflows/deploy.yml">
name: Deploy
on: [push]
</FILE>""",
        model="deepseek/deepseek-chat",
        tokens_used=200,
        cost_usd=0.0002,
        latency_ms=600,
        provider="openrouter",
    )

    with patch.object(deployment_agent, "_write_file", new=AsyncMock()) as mock_write:
        result = await deployment_agent._parse_output(response, {})

        assert "deployment_files" in result
        assert len(result["deployment_files"]) == 2
        assert "docker/Dockerfile" in result["deployment_files"]
        assert ".github/workflows/deploy.yml" in result["deployment_files"]
        assert mock_write.call_count == 2


@pytest.mark.asyncio
async def test_parse_output_no_valid_files(deployment_agent):
    """Test handling of response with no valid deployment files."""
    response = LLMResponse(
        content="This is just plain text with no FILE tags.",
        model="deepseek/deepseek-chat",
        tokens_used=50,
        cost_usd=0.00005,
        latency_ms=300,
        provider="openrouter",
    )

    with pytest.raises(ValueError, match="No valid deployment files could be parsed"):
        await deployment_agent._parse_output(response, {})
