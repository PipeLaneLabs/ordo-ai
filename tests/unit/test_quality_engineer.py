"""Unit tests for QualityEngineerAgent.

Tests the Quality Engineer Agent's test generation, execution,
and coverage analysis capabilities.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.tier_3.quality_engineer import QualityEngineerAgent
from src.config import Settings
from src.llm.base_client import LLMResponse


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = AsyncMock()
    client.generate = AsyncMock(
        return_value=LLMResponse(
            content="```python:tests/unit/test_example.py\ndef test_example():\n    assert True\n```",
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
def quality_engineer(mock_llm_client, mock_budget_guard, mock_settings):
    """Create QualityEngineerAgent instance for testing."""
    return QualityEngineerAgent(
        name="QualityEngineerAgent",
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
        token_budget=12000,
    )


def test_initialization(quality_engineer):
    """Test QualityEngineerAgent initializes correctly."""
    assert quality_engineer.name == "QualityEngineerAgent"
    assert quality_engineer.token_budget == 12000


def test_get_temperature(quality_engineer):
    """Test temperature is 0.3 for balanced creativity."""
    assert quality_engineer._get_temperature() == 0.3


def test_extract_coverage_from_output(quality_engineer):
    """Test coverage percentage extraction from pytest output."""
    results = {
        "stdout": "TOTAL    1234    567    75%",
        "stderr": "",
    }

    coverage = quality_engineer._extract_coverage(results)
    assert coverage == 75.0


def test_extract_coverage_no_match(quality_engineer):
    """Test coverage extraction when no match found."""
    results = {
        "stdout": "No coverage info here",
        "stderr": "",
    }

    coverage = quality_engineer._extract_coverage(results)
    assert coverage == 0.0


def test_is_approved_passing_tests_good_coverage(quality_engineer):
    """Test approval when tests pass and coverage >= 70%."""
    results = {"return_code": 0}
    coverage = 75.0

    assert quality_engineer._is_approved(results, coverage) is True


def test_is_approved_failing_tests(quality_engineer):
    """Test rejection when tests fail."""
    results = {"return_code": 1}
    coverage = 75.0

    assert quality_engineer._is_approved(results, coverage) is False


def test_is_approved_low_coverage(quality_engineer):
    """Test rejection when coverage < 70%."""
    results = {"return_code": 0}
    coverage = 65.0

    assert quality_engineer._is_approved(results, coverage) is False


def test_is_approved_exact_threshold(quality_engineer):
    """Test approval at exactly 70% coverage."""
    results = {"return_code": 0}
    coverage = 70.0

    assert quality_engineer._is_approved(results, coverage) is True


def test_generate_quality_report_passing(quality_engineer):
    """Test quality report generation for passing tests."""
    results = {"return_code": 0, "stdout": "All tests passed", "stderr": ""}
    new_tests = ["tests/unit/test_a.py", "tests/unit/test_b.py"]
    coverage = 85.0

    report = quality_engineer._generate_quality_report(results, new_tests, coverage)

    assert "✅ PASSED" in report
    assert "85.0%" in report
    assert "test_a.py" in report
    assert "test_b.py" in report
    assert "✅ APPROVED" in report


def test_generate_quality_report_failing(quality_engineer):
    """Test quality report generation for failing tests."""
    results = {"return_code": 1, "stdout": "Tests failed", "stderr": "Error"}
    new_tests = ["tests/unit/test_a.py"]
    coverage = 65.0

    report = quality_engineer._generate_quality_report(results, new_tests, coverage)

    assert "❌ FAILED" in report
    assert "65.0%" in report
    assert "❌ REJECTED" in report


@pytest.mark.asyncio
async def test_parse_output_extracts_test_files(quality_engineer):
    """Test extraction of test files from LLM response."""
    response = LLMResponse(
        content="""```python:tests/unit/test_a.py
def test_a():
    assert True
```

```python:tests/unit/test_b.py
def test_b():
    assert True
```""",
        model="deepseek/deepseek-chat",
        tokens_used=200,
        cost_usd=0.0002,
        latency_ms=500,
        provider="openrouter",
    )

    with (
        patch.object(quality_engineer, "_write_file", new=AsyncMock()),
        patch.object(
            quality_engineer,
            "_run_pytest",
            new=AsyncMock(
                return_value={
                    "return_code": 0,
                    "stdout": "TOTAL 100 0 100%",
                    "stderr": "",
                }
            ),
        ),
    ):
        result = await quality_engineer._parse_output(response, {})

        assert len(result["files_created"]) == 2
        assert "tests/unit/test_a.py" in result["files_created"]
        assert "tests/unit/test_b.py" in result["files_created"]


@pytest.mark.asyncio
async def test_parse_output_ignores_non_test_files(quality_engineer):
    """Test that non-test files are ignored."""
    response = LLMResponse(
        content="""```python:src/main.py
print("not a test")
```

```python:tests/unit/test_a.py
def test_a():
    assert True
```""",
        model="deepseek/deepseek-chat",
        tokens_used=200,
        cost_usd=0.0002,
        latency_ms=500,
        provider="openrouter",
    )

    with (
        patch.object(quality_engineer, "_write_file", new=AsyncMock()),
        patch.object(
            quality_engineer,
            "_run_pytest",
            new=AsyncMock(
                return_value={
                    "return_code": 0,
                    "stdout": "TOTAL 100 0 100%",
                    "stderr": "",
                }
            ),
        ),
    ):
        result = await quality_engineer._parse_output(response, {})

        assert len(result["files_created"]) == 1
        assert "tests/unit/test_a.py" in result["files_created"]
        assert "src/main.py" not in result["files_created"]


@pytest.mark.asyncio
async def test_run_pytest_success(quality_engineer):
    """Test pytest execution success."""
    with patch("asyncio.create_subprocess_shell") as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"All tests passed\nTOTAL 100 0 100%", b"")
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        result = await quality_engineer._run_pytest()

        assert result["return_code"] == 0
        assert "All tests passed" in result["stdout"]


@pytest.mark.asyncio
async def test_run_pytest_failure(quality_engineer):
    """Test pytest execution failure."""
    with patch("asyncio.create_subprocess_shell") as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"Tests failed", b"Error details")
        )
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        result = await quality_engineer._run_pytest()

        assert result["return_code"] == 1
        assert "Tests failed" in result["stdout"]


@pytest.mark.asyncio
async def test_build_prompt_includes_requirements(quality_engineer):
    """Test prompt includes REQUIREMENTS.md content."""
    state = {"current_phase": "development"}

    with (
        patch.object(
            quality_engineer,
            "_read_if_exists",
            new=AsyncMock(return_value="Requirements content"),
        ),
        patch.object(
            quality_engineer, "_read_src_files", new=AsyncMock(return_value="")
        ),
        patch.object(
            quality_engineer, "_read_existing_tests", new=AsyncMock(return_value="")
        ),
    ):
        prompt = await quality_engineer._build_prompt(state)

        assert "Requirements content" in prompt or "REQUIREMENTS.md" in prompt
