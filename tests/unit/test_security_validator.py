from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from src.agents.tier_4.security_validator import SecurityValidatorAgent
from src.llm.base_client import LLMResponse
from src.orchestration.state import WorkflowState


@pytest.fixture
def mock_llm_client():
    return AsyncMock()


@pytest.fixture
def mock_budget_guard():
    return MagicMock()


@pytest.fixture
def mock_settings():
    return MagicMock()


@pytest.fixture
def security_agent(mock_llm_client, mock_budget_guard, mock_settings):
    return SecurityValidatorAgent(
        name="SecurityValidator",
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
        token_budget=6000,
    )


@pytest.mark.asyncio
async def test_initialization(security_agent):
    assert security_agent.name == "SecurityValidator"
    assert security_agent.token_budget == 6000
    assert security_agent._get_temperature() == 0.5
    assert security_agent._estimate_cost() == 0.0


@pytest.mark.asyncio
async def test_build_prompt(security_agent):
    # Mock data
    state: WorkflowState = {"current_phase": "tier_4"}

    # Mock file reading
    security_agent._read_if_exists = AsyncMock(
        side_effect=["Reqs Content", "Arch Content", "Tasks Content", "Previous Report"]
    )

    # Mock code collection
    with (
        patch.object(
            security_agent, "_collect_code_files", return_value=[Path("src/main.py")]
        ),
        patch.object(
            security_agent, "_format_code_files", return_value="Formatted Code"
        ),
    ):

        prompt = await security_agent._build_prompt(state)

        assert "Security Validation Task" in prompt
        assert "Reqs Content" in prompt
        assert "Formatted Code" in prompt
        assert "Previous Security Report" in prompt


@pytest.mark.asyncio
async def test_format_code_files(security_agent, tmp_path):
    # Create temp files
    f1 = tmp_path / "file1.py"
    f1.write_text("print('hello')", encoding="utf-8")

    formatted = security_agent._format_code_files([f1])

    assert "### File:" in formatted
    assert str(f1) in formatted
    assert "print('hello')" in formatted


@pytest.mark.asyncio
async def test_format_code_files_limit(security_agent):
    # Test strict limit logic without creating 21 files
    mock_files = [Path(f"file_{i}.py") for i in range(25)]

    with patch.multiple(Path, read_text=MagicMock(return_value="code")):
        formatted = security_agent._format_code_files(mock_files)

    assert "Showing 20 of 25 files" in formatted


@pytest.mark.asyncio
async def test_parse_output_approved(security_agent):
    state: WorkflowState = {}
    llm_response = LLMResponse(
        content="""
```markdown
# Security Validation Report
**Overall Status:** ✅ APPROVED
**Critical Issues (P0):** 0
**High Issues (P1):** 0
```
""",
        tokens_used=100,
        cost_usd=0.0,
        model="test-model",
        latency_ms=150,
        provider="test-provider",
    )

    security_agent._write_file = AsyncMock()

    result = await security_agent._parse_output(llm_response, state)

    assert result["security_status"] == "APPROVED"
    assert result["critical_issues"] == 0
    assert result["high_issues"] == 0
    security_agent._write_file.assert_called_with("SECURITY_REPORT.md", ANY)


@pytest.mark.asyncio
async def test_parse_output_rejected(security_agent):
    state: WorkflowState = {}
    llm_response = LLMResponse(
        content="""
# Security Validation Report
**Overall Status:** ❌ REJECTED
**Critical Issues (P0):** 2
```
## Critical Issues (P0) - BLOCKING
### Issue #1: Secret
### Issue #2: SQL Injection
```
""",
        tokens_used=100,
        cost_usd=0.0,
        model="test-model",
        latency_ms=150,
        provider="test-provider",
    )

    security_agent._write_file = AsyncMock()

    result = await security_agent._parse_output(llm_response, state)

    assert result["security_status"] == "REJECTED"
    assert result["critical_issues"] == 2


@pytest.mark.asyncio
async def test_extract_issue_count(security_agent):
    content = "**Critical Issues (P0):** 5"
    assert security_agent._extract_issue_count(content, "Critical Issues (P0)") == 5

    content_alt = """
## Critical Issues (P0) - BLOCKING
### Issue #1
### Issue #2
"""
    assert security_agent._extract_issue_count(content_alt, "Critical Issues (P0)") == 2

    assert security_agent._extract_issue_count("No issues", "Critical Issues (P0)") == 0
