"""Unit tests for SoftwareEngineerAgent.

Tests the Software Engineer Agent's code generation, parsing,
and validation capabilities.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.tier_3.software_engineer import SoftwareEngineerAgent
from src.config import Settings
from src.llm.base_client import LLMResponse


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = AsyncMock()
    client.generate = AsyncMock(
        return_value=LLMResponse(
            content="```python:test.py\nprint('hello')\n```",
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
def software_engineer(mock_llm_client, mock_budget_guard, mock_settings):
    """Create SoftwareEngineerAgent instance for testing."""
    return SoftwareEngineerAgent(
        name="SoftwareEngineerAgent",
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
        token_budget=16000,
    )


def test_initialization(software_engineer):
    """Test SoftwareEngineerAgent initializes correctly."""
    assert software_engineer.name == "SoftwareEngineerAgent"
    assert software_engineer.token_budget == 16000


def test_get_temperature(software_engineer):
    """Test temperature is 0.2 for precision."""
    assert software_engineer._get_temperature() == 0.2


def test_estimate_cost(software_engineer):
    """Test cost estimation for 16,000 tokens."""
    cost = software_engineer._estimate_cost()
    assert cost == (16000 / 1_000_000) * 1.0
    assert cost == 0.016


def test_is_valid_code_file_python(software_engineer):
    """Test .py files are allowed."""
    assert software_engineer._is_valid_code_file("src/test.py") is True


def test_is_valid_code_file_javascript(software_engineer):
    """Test .js files are allowed."""
    assert software_engineer._is_valid_code_file("src/test.js") is True


def test_is_valid_code_file_yaml(software_engineer):
    """Test .yaml files are allowed."""
    assert software_engineer._is_valid_code_file("config.yaml") is True


def test_is_valid_code_file_rejects_readme(software_engineer):
    """Test README.md is rejected."""
    assert software_engineer._is_valid_code_file("README.md") is False


def test_is_valid_code_file_rejects_architecture(software_engineer):
    """Test ARCHITECTURE.md is rejected."""
    assert software_engineer._is_valid_code_file("ARCHITECTURE.md") is False


def test_is_valid_code_file_rejects_path_traversal(software_engineer):
    """Test path traversal is rejected."""
    assert software_engineer._is_valid_code_file("../etc/passwd") is False
    assert software_engineer._is_valid_code_file("../../secret.py") is False


def test_is_valid_code_file_rejects_absolute_path(software_engineer):
    """Test absolute paths are rejected."""
    assert software_engineer._is_valid_code_file("/etc/passwd") is False


def test_is_valid_code_file_allows_env_example(software_engineer):
    """Test .env.example is allowed."""
    assert software_engineer._is_valid_code_file(".env.example") is True


@pytest.mark.asyncio
async def test_parse_output_valid_code_block(software_engineer, tmp_path):
    """Test parsing valid code blocks from LLM response."""
    response = LLMResponse(
        content='```python:test.py\nprint("hello")\n```',
        model="deepseek/deepseek-chat",
        tokens_used=100,
        cost_usd=0.0001,
        latency_ms=500,
        provider="openrouter",
    )

    with patch.object(software_engineer, "_write_file", new=AsyncMock()) as mock_write:
        result = await software_engineer._parse_output(response, {})

        assert result["status"] == "completed"
        assert "test.py" in result["files_created"]
        mock_write.assert_called_once()


@pytest.mark.asyncio
async def test_parse_output_multiple_code_blocks(software_engineer):
    """Test parsing multiple code blocks."""
    response = LLMResponse(
        content="""```python:file1.py
print("file1")
```

```python:file2.py
print("file2")
```""",
        model="deepseek/deepseek-chat",
        tokens_used=200,
        cost_usd=0.0002,
        latency_ms=500,
        provider="openrouter",
    )

    with patch.object(software_engineer, "_write_file", new=AsyncMock()):
        result = await software_engineer._parse_output(response, {})

        assert result["status"] == "completed"
        assert len(result["files_created"]) == 2
        assert "file1.py" in result["files_created"]
        assert "file2.py" in result["files_created"]


@pytest.mark.asyncio
async def test_parse_output_rejects_invalid_filename(software_engineer):
    """Test parsing rejects invalid filenames."""
    response = LLMResponse(
        content='```python:README.md\nprint("invalid")\n```',
        model="deepseek/deepseek-chat",
        tokens_used=100,
        cost_usd=0.0001,
        latency_ms=500,
        provider="openrouter",
    )

    with patch.object(software_engineer, "_write_file", new=AsyncMock()):
        result = await software_engineer._parse_output(response, {})

        assert result["status"] == "no_files_generated"
        assert len(result["files_created"]) == 0
        assert result["errors"] is not None


@pytest.mark.asyncio
async def test_parse_output_no_code_blocks(software_engineer):
    """Test parsing when no code blocks present."""
    response = LLMResponse(
        content="Just some text without code blocks",
        model="deepseek/deepseek-chat",
        tokens_used=50,
        cost_usd=0.00005,
        latency_ms=500,
        provider="openrouter",
    )

    result = await software_engineer._parse_output(response, {})

    assert result["status"] == "no_files_generated"
    assert len(result["files_created"]) == 0


@pytest.mark.asyncio
async def test_build_prompt_includes_tasks(software_engineer):
    """Test prompt includes TASKS.md content."""
    state = {"workflow_id": "test-001", "current_task_id": "TASK-025"}

    with patch.object(
        software_engineer,
        "_read_if_exists",
        new=AsyncMock(return_value="TASKS content"),
    ):
        prompt = await software_engineer._build_prompt(state)

        assert "TASKS content" in prompt
        assert "TASK-025" in prompt


@pytest.mark.asyncio
async def test_build_prompt_includes_feedback(software_engineer):
    """Test prompt includes rejection feedback."""
    state = {
        "workflow_id": "test-001",
        "feedback": "Fix type errors",
        "rejection_count": 1,
        "rejected_by": "StaticAnalysisAgent",
    }

    with patch.object(
        software_engineer, "_read_if_exists", new=AsyncMock(return_value="")
    ):
        prompt = await software_engineer._build_prompt(state)

        assert "Fix type errors" in prompt
        assert "Rejection Count: 1" in prompt
        assert "StaticAnalysisAgent" in prompt
