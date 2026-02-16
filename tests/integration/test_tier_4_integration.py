from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.tier_4.product_validator import ProductValidatorAgent
from src.agents.tier_4.security_validator import SecurityValidatorAgent
from src.llm.base_client import LLMResponse
from src.orchestration.state import create_initial_state


@pytest.fixture
def mock_deps():
    return {
        "llm_client": AsyncMock(),
        "budget_guard": MagicMock(),
        "settings": MagicMock(),
    }


@pytest.mark.asyncio
async def test_security_validator_workflow(mock_deps, tmp_path):
    """Integration test for Security Validator workflow."""
    agent = SecurityValidatorAgent(name="SecurityValidator", **mock_deps)

    # Setup mock file reading/writing to use tmp_path logic implicitly via mocks?
    # Ideally integration tests use real I/O, but we need to control the environment.
    # We'll monkeypatch the BaseAgent file operations to use tmp_path

    async def mock_read(filename):
        p = tmp_path / filename
        if p.exists():
            return p.read_text(encoding="utf-8")
        return None

    async def mock_write(filename, content):
        p = tmp_path / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    agent_any = cast(Any, agent)
    agent_any._read_if_exists = mock_read
    agent_any._write_file = mock_write

    # Create required files
    (tmp_path / "REQUIREMENTS.md").write_text("Requirements...", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("print('hello')", encoding="utf-8")

    # Mock LLM response
    mock_deps["llm_client"].generate.return_value = LLMResponse(
        content="**Overall Status:** ✅ APPROVED\n**Critical Issues (P0):** 0",
        tokens_used=100,
        tokens_prompt=50,
        tokens_completion=50,
        cost_usd=0.0,
        model="test-model",
        latency_ms=150,
        provider="test-provider",
        finish_reason="stop",
    )

    state = create_initial_state("wf-1", "Security validation", "trace-1")
    state["current_phase"] = "validation"

    # Execute
    new_state = await agent.execute(state)

    # Verify State Update
    partial_artifacts = cast(dict[str, object], new_state["partial_artifacts"])
    security_status = cast(str, partial_artifacts["security_status"])
    assert security_status == "APPROVED"
    assert new_state["current_agent"] == "SecurityValidator"

    # Verify Report Created
    assert (tmp_path / "SECURITY_REPORT.md").exists()


@pytest.mark.asyncio
async def test_product_validator_workflow(mock_deps, tmp_path):
    """Integration test for Product Validator workflow."""
    agent = ProductValidatorAgent(name="ProductValidator", **mock_deps)

    async def mock_read(filename):
        p = tmp_path / filename
        if p.exists():
            return p.read_text(encoding="utf-8")
        return None

    async def mock_write(filename, content):
        p = tmp_path / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    agent_any = cast(Any, agent)
    agent_any._read_if_exists = mock_read
    agent_any._write_file = mock_write

    # Create required files
    (tmp_path / "REQUIREMENTS.md").write_text("Reqs", encoding="utf-8")

    mock_deps["llm_client"].generate.return_value = LLMResponse(
        content="**Overall Status:** ✅ APPROVED\n**Functional Requirements Met:** 5/5",
        tokens_used=100,
        tokens_prompt=50,
        tokens_completion=50,
        cost_usd=0.0,
        model="test-model",
        latency_ms=150,
        provider="test-provider",
        finish_reason="stop",
    )

    state = create_initial_state("wf-2", "Test Request", "trace-2")
    state["current_phase"] = "validation"

    new_state = await agent.execute(state)

    partial_artifacts = cast(dict[str, object], new_state["partial_artifacts"])
    acceptance_status = cast(str, partial_artifacts["acceptance_status"])
    assert acceptance_status == "APPROVED"
    assert (tmp_path / "ACCEPTANCE_REPORT.md").exists()
