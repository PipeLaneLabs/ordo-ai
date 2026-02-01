from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from src.agents.tier_4.product_validator import ProductValidatorAgent
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
def product_agent(mock_llm_client, mock_budget_guard, mock_settings):
    return ProductValidatorAgent(
        name="ProductValidator",
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
        token_budget=6000,
    )


@pytest.mark.asyncio
async def test_initialization(product_agent):
    assert product_agent.name == "ProductValidator"
    assert product_agent.token_budget == 6000
    assert product_agent._get_temperature() == 0.5
    assert product_agent._estimate_cost() == 0.0


@pytest.mark.asyncio
async def test_build_prompt(product_agent):
    state: WorkflowState = {
        "user_request": "Build a web app",
        "current_phase": "tier_4",
    }

    # Mock data
    product_agent._read_if_exists = AsyncMock(
        side_effect=["Reqs", "Arch", "Tasks", "Qual Report", "Prev Report"]
    )

    with (
        patch.object(product_agent, "_collect_code_files", return_value=[]),
        patch.object(
            product_agent, "_summarize_code_files", return_value="Code Summary"
        ),
        patch.object(product_agent, "_collect_test_files", return_value=[]),
        patch.object(
            product_agent, "_summarize_test_files", return_value="Test Summary"
        ),
    ):

        prompt = await product_agent._build_prompt(state)

        assert "Product Validation Task" in prompt
        assert "Build a web app" in prompt
        assert "Code Summary" in prompt
        assert "Test Summary" in prompt


@pytest.mark.asyncio
async def test_summarize_code_files(product_agent, tmp_path):
    f1 = tmp_path / "main.py"
    f1.write_text(
        "class MyClass:\n    def my_method(self):\n        pass", encoding="utf-8"
    )

    summary = product_agent._summarize_code_files([f1])

    assert "**Total Code Files:** 1" in summary
    assert "main.py" in summary
    assert "Classes: MyClass" in summary


@pytest.mark.asyncio
async def test_summarize_test_files(product_agent, tmp_path):
    t1 = tmp_path / "test_main.py"
    t1.write_text("def test_one(): pass\ndef test_two(): pass", encoding="utf-8")

    summary = product_agent._summarize_test_files([t1])

    assert "**Total Test Files:** 1" in summary
    assert "test_main.py" in summary
    assert "(2 tests)" in summary


@pytest.mark.asyncio
async def test_parse_output(product_agent):
    state: WorkflowState = {}
    llm_response = LLMResponse(
        content="""
# Product Acceptance Report
**Overall Status:** ✅ APPROVED
**Functional Requirements Met:** 10/10
**Acceptance Criteria Met:** 5/5
""",
        tokens_used=100,
        cost_usd=0.0,
        model="test-model",
        latency_ms=150,
        provider="test-provider",
    )

    product_agent._write_file = AsyncMock()

    result = await product_agent._parse_output(llm_response, state)

    assert result["acceptance_status"] == "APPROVED"
    assert result["functional_requirements_met"] == "10/10"
    assert result["acceptance_criteria_met"] == "5/5"
    product_agent._write_file.assert_called_with("ACCEPTANCE_REPORT.md", ANY)


@pytest.mark.asyncio
async def test_extract_fraction(product_agent):
    content = "**Functional Requirements Met:** 10/10"
    assert (
        product_agent._extract_fraction(content, "Functional Requirements Met")
        == "10/10"
    )

    assert product_agent._extract_fraction("No data", "Metric") == "Unknown"
