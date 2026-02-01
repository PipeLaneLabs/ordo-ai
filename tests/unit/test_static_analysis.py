"""Unit tests for StaticAnalysisAgent.

Tests the Static Analysis Agent's tool execution, report generation,
and quality checking capabilities.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.tier_3.static_analysis import StaticAnalysisAgent
from src.config import Settings
from src.llm.base_client import LLMResponse


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = AsyncMock()
    client.generate = AsyncMock(
        return_value=LLMResponse(
            content="""```markdown:COMPLIANCE_LOG.md
# Code Compliance Log
Status: APPROVED
```

```json
{"status": "APPROVED", "critical_issues_count": 0}
```""",
            model="google/gemini-2.0-flash-exp:free",
            tokens_used=100,
            cost_usd=0.0001,
            latency_ms=300,
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
def static_analysis(mock_llm_client, mock_budget_guard, mock_settings):
    """Create StaticAnalysisAgent instance for testing."""
    return StaticAnalysisAgent(
        name="StaticAnalysisAgent",
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
        token_budget=2000,
    )


def test_initialization(static_analysis):
    """Test StaticAnalysisAgent initializes correctly."""
    assert static_analysis.name == "StaticAnalysisAgent"
    assert static_analysis.token_budget == 2000


def test_get_temperature(static_analysis):
    """Test temperature is 0.1 for determinism."""
    assert static_analysis._get_temperature() == 0.1


def test_error_result_creates_proper_structure(static_analysis):
    """Test error result has correct format."""
    exception = Exception("Test error")
    result = static_analysis._error_result("test_tool", exception)

    assert result["command"] == "test_tool"
    assert result["return_code"] == -1
    assert result["stdout"] == ""
    assert "Test error" in result["stderr"]


@pytest.mark.asyncio
async def test_run_command_success(static_analysis):
    """Test successful command execution."""
    with patch("asyncio.create_subprocess_shell") as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        result = await static_analysis._run_command("echo test")

        assert result["command"] == "echo test"
        assert result["return_code"] == 0
        assert result["stdout"] == "output"


@pytest.mark.asyncio
async def test_run_command_failure(static_analysis):
    """Test command execution failure."""
    with patch("asyncio.create_subprocess_shell") as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b"error"))
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        result = await static_analysis._run_command("false")

        assert result["return_code"] == 1
        assert result["stderr"] == "error"


@pytest.mark.asyncio
async def test_run_command_exception(static_analysis):
    """Test command execution with exception."""
    with patch(
        "asyncio.create_subprocess_shell", side_effect=Exception("Command failed")
    ):
        result = await static_analysis._run_command("invalid")

        assert result["return_code"] == -1
        assert "Command failed" in result["stderr"]


@pytest.mark.asyncio
async def test_parse_output_extracts_compliance_log(static_analysis):
    """Test COMPLIANCE_LOG.md extraction."""
    response = LLMResponse(
        content="""```markdown:COMPLIANCE_LOG.md
# Code Compliance Log
Status: APPROVED
```""",
        model="google/gemini-2.0-flash-exp:free",
        tokens_used=100,
        cost_usd=0.0001,
        latency_ms=300,
        provider="openrouter",
    )

    with patch.object(static_analysis, "_write_file", new=AsyncMock()):
        result = await static_analysis._parse_output(response, {})

        assert result["report_generated"] is True


@pytest.mark.asyncio
async def test_parse_output_extracts_json_summary(static_analysis):
    """Test JSON summary extraction."""
    response = LLMResponse(
        content="""```json
{"status": "APPROVED", "critical_issues_count": 0}
```""",
        model="google/gemini-2.0-flash-exp:free",
        tokens_used=100,
        cost_usd=0.0001,
        latency_ms=300,
        provider="openrouter",
    )

    result = await static_analysis._parse_output(response, {})

    assert result["status"] == "APPROVED"
    assert result["critical_issues_count"] == 0


@pytest.mark.asyncio
async def test_parse_output_fallback_markdown(static_analysis):
    """Test fallback markdown parsing without filename."""
    response = LLMResponse(
        content="""```markdown
# Code Compliance Log
```""",
        model="google/gemini-2.0-flash-exp:free",
        tokens_used=100,
        cost_usd=0.0001,
        latency_ms=300,
        provider="openrouter",
    )

    with patch.object(static_analysis, "_write_file", new=AsyncMock()):
        result = await static_analysis._parse_output(response, {})

        assert result["report_generated"] is True


@pytest.mark.asyncio
async def test_parse_output_invalid_json(static_analysis):
    """Test handling of invalid JSON."""
    response = LLMResponse(
        content="""```json
{invalid json}
```""",
        model="google/gemini-2.0-flash-exp:free",
        tokens_used=100,
        cost_usd=0.0001,
        latency_ms=300,
        provider="openrouter",
    )

    result = await static_analysis._parse_output(response, {})

    assert result["status"] == "ERROR"
    assert "error" in result


@pytest.mark.asyncio
async def test_parse_output_defaults_to_approved(static_analysis):
    """Test default status is APPROVED if no JSON."""
    response = LLMResponse(
        content="No JSON here",
        model="google/gemini-2.0-flash-exp:free",
        tokens_used=50,
        cost_usd=0.00005,
        latency_ms=300,
        provider="openrouter",
    )

    result = await static_analysis._parse_output(response, {})

    assert result["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_build_prompt_includes_tool_results(static_analysis):
    """Test prompt includes all tool outputs."""
    state = {}
    tool_results = {
        "black": {"command": "black --check", "return_code": 0, "stdout": "All done!"},
        "ruff": {"command": "ruff check", "return_code": 0, "stdout": ""},
        "mypy": {"command": "mypy", "return_code": 0, "stdout": "Success"},
        "radon": {"command": "radon cc", "return_code": 0, "stdout": "B"},
    }

    with patch.object(
        static_analysis, "_read_if_exists", new=AsyncMock(return_value="")
    ):
        prompt = await static_analysis._build_prompt(state, **{"tool_results": tool_results})

        assert "Black (Code Formatting)" in prompt
        assert "Ruff (Linting)" in prompt
        assert "Mypy (Type Checking)" in prompt
        assert "Radon (Complexity Analysis)" in prompt
