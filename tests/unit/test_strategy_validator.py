"""Unit tests for Strategy Validator Agent."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.tier_1.strategy_validator import StrategyValidatorAgent
from src.config import Settings
from src.exceptions import AgentRejectionError
from src.llm.base_client import LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


@pytest.fixture
def mock_llm_client_approved() -> AsyncMock:
    """Create mock LLM client with APPROVED validation."""
    client = AsyncMock()
    client.generate = AsyncMock(
        return_value=LLMResponse(
            content="""# Requirements Validation Report

**Validator:** Strategy Validator Agent
**Date:** 2026-01-23
**Status:** APPROVED

## Executive Summary

All requirements are feasible and well-defined.

**Decision:** APPROVED
**Blocking Issues:** 0
**High Priority Issues:** 0

## 7. Quality Gate Decision

**Decision:** APPROVED ✅

**Rationale:** No blocking issues found. Requirements are clear and feasible.
""",
            model="deepseek-r1",
            tokens_used=400,
            tokens_prompt=200,
            tokens_completion=200,
            cost_usd=0.004,
            latency_ms=1200,
            provider="openrouter",
            finish_reason="stop",
        )
    )
    return client


@pytest.fixture
def mock_llm_client_rejected() -> AsyncMock:
    """Create mock LLM client with REJECTED validation."""
    client = AsyncMock()
    client.generate = AsyncMock(
        return_value=LLMResponse(
            content="""# Requirements Validation Report

**Validator:** Strategy Validator Agent
**Date:** 2026-01-23
**Status:** REJECTED

## Executive Summary

Critical conflicts found in requirements.

**Decision:** REJECTED
**Blocking Issues:** 2

## 6. Recommendations

### Must-Fix (Blocking Issues)
1. Conflicting performance requirements
2. Missing security requirements

## 7. Quality Gate Decision

**Decision:** REJECTED ❌

**Rationale:** Blocking issues must be resolved.
""",
            model="deepseek-r1",
            tokens_used=400,
            tokens_prompt=200,
            tokens_completion=200,
            cost_usd=0.004,
            latency_ms=1200,
            provider="openrouter",
            finish_reason="stop",
        )
    )
    return client


@pytest.fixture
def mock_budget_guard() -> MagicMock:
    """Create mock budget guard."""
    guard = MagicMock(spec=BudgetGuard)
    guard.reserve_budget = MagicMock()
    guard.record_usage = MagicMock()
    return guard


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings."""
    return Settings(
        environment="test",
        log_level="DEBUG",
        postgres_url="postgresql://test:test@localhost/test",
        redis_url="redis://localhost:6379/0",
        minio_endpoint="localhost:9000",
        openrouter_api_key="test-api-key-12345",
        google_api_key="test-api-key-12345",
        jwt_secret_key="test-secret-key-min-32-chars-long-123456",
        human_approval_timeout=300,
        total_budget_tokens=100000,
        max_monthly_budget_usd=10.0,
    )


@pytest.fixture
def sample_workflow_state() -> WorkflowState:
    """Create sample workflow state with requirements."""
    return {
        "workflow_id": "test-workflow-790",
        "user_request": "Create a user authentication system",
        "current_phase": "planning",
        "current_task": "validation",
        "current_agent": "StrategyValidatorAgent",
        "rejection_count": 0,
        "state_version": 1,
        "requirements": "# Requirements\n\nTest requirements content",
        "architecture": "",
        "tasks": "",
        "code_files": {},
        "test_files": {},
        "partial_artifacts": {},
        "validation_report": "",
        "quality_report": "",
        "security_report": "",
        "budget_used_tokens": 500,
        "budget_used_usd": 0.005,
        "budget_remaining_tokens": 99500,
        "budget_remaining_usd": 9.995,
        "quality_gates_passed": [],
        "blocking_issues": [],
        "awaiting_human_approval": False,
        "approval_gate": "",
        "approval_timeout": "",
        "routing_decision": {},
        "escalation_flag": False,
        "trace_id": "test-trace-790",
        "dependencies": "",
        "infrastructure": "",
        "observability": "",
        "deviation_log": "",
        "compliance_log": "",
        "acceptance_report": "",
        "agent_token_usage": {},
        "created_at": "2026-01-23T23:00:00+13:00",
        "updated_at": "2026-01-23T23:00:00+13:00",
    }


class TestStrategyValidatorAgentInitialization:
    """Test StrategyValidatorAgent initialization."""

    def test_initialization(
        self,
        mock_llm_client_approved: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
    ) -> None:
        """Test agent initialization with correct parameters."""
        # Act
        agent = StrategyValidatorAgent(
            llm_client=mock_llm_client_approved,
            budget_guard=mock_budget_guard,
            settings=mock_settings,
        )

        # Assert
        assert agent.name == "StrategyValidatorAgent"
        assert agent.token_budget == 6000
        assert agent.llm_client == mock_llm_client_approved
        assert agent.budget_guard == mock_budget_guard


class TestStrategyValidatorAgentPromptBuilding:
    """Test prompt building for validation."""

    @pytest.mark.asyncio
    async def test_build_prompt_includes_requirements(
        self,
        mock_llm_client_approved: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
    ) -> None:
        """Test prompt includes requirements to validate."""
        # Arrange
        agent = StrategyValidatorAgent(
            mock_llm_client_approved, mock_budget_guard, mock_settings
        )

        # Act
        prompt = await agent._build_prompt(sample_workflow_state)

        # Assert
        assert "Test requirements content" in prompt
        assert "Requirements Validation Task" in prompt
        assert "Conflict Detection" in prompt
        assert "Feasibility Assessment" in prompt
        assert "Risk Assessment" in prompt


class TestStrategyValidatorAgentApprovalFlow:
    """Test validation approval flow."""

    @pytest.mark.asyncio
    async def test_parse_output_approved_validation(
        self,
        mock_llm_client_approved: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
        monkeypatch,
    ) -> None:
        """Test _parse_output with APPROVED validation."""
        # Arrange
        agent = StrategyValidatorAgent(
            mock_llm_client_approved, mock_budget_guard, mock_settings
        )
        response = await mock_llm_client_approved.generate(
            prompt="test", max_tokens=1000
        )

        # Mock _write_file to avoid actual file I/O
        write_file_mock = AsyncMock()
        monkeypatch.setattr(agent, "_write_file", write_file_mock)

        # Act
        result = await agent._parse_output(response, sample_workflow_state)

        # Assert
        assert result["validation_status"] == "APPROVED"
        assert result["validation_passed"] is True
        assert result["blocking_issues_count"] == 0

    @pytest.mark.asyncio
    async def test_execute_approved_validation_succeeds(
        self,
        mock_llm_client_approved: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
        monkeypatch,
    ) -> None:
        """Test execute() succeeds with APPROVED validation."""
        # Arrange
        agent = StrategyValidatorAgent(
            mock_llm_client_approved, mock_budget_guard, mock_settings
        )

        # Mock _write_file to avoid actual file I/O
        write_file_mock = AsyncMock()
        monkeypatch.setattr(agent, "_write_file", write_file_mock)

        # Act
        result_state = await agent.execute(sample_workflow_state)

        # Assert
        assert result_state["current_agent"] == "StrategyValidatorAgent"
        assert "validation_passed" in result_state["partial_artifacts"]


class TestStrategyValidatorAgentRejectionFlow:
    """Test validation rejection flow."""

    @pytest.mark.asyncio
    async def test_parse_output_rejected_validation_raises_error(
        self,
        mock_llm_client_rejected: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
        monkeypatch,
    ) -> None:
        """Test _parse_output raises AgentRejectionError when REJECTED."""
        # Arrange
        agent = StrategyValidatorAgent(
            mock_llm_client_rejected, mock_budget_guard, mock_settings
        )
        response = await mock_llm_client_rejected.generate(
            prompt="test", max_tokens=1000
        )

        # Mock _write_file to avoid actual file I/O
        write_file_mock = AsyncMock()
        monkeypatch.setattr(agent, "_write_file", write_file_mock)

        # Act & Assert
        with pytest.raises(AgentRejectionError) as exc_info:
            await agent._parse_output(response, sample_workflow_state)

        assert exc_info.value.agent == "RequirementsStrategyAgent"
        assert exc_info.value.validator == "StrategyValidatorAgent"
        assert "blocking issues found" in exc_info.value.reason

    @pytest.mark.asyncio
    async def test_execute_rejected_validation_raises_error(
        self,
        mock_llm_client_rejected: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
        monkeypatch,
    ) -> None:
        """Test execute() raises AgentRejectionError when validation fails."""
        # Arrange
        agent = StrategyValidatorAgent(
            mock_llm_client_rejected, mock_budget_guard, mock_settings
        )

        # Mock _write_file to avoid actual file I/O
        write_file_mock = AsyncMock()
        monkeypatch.setattr(agent, "_write_file", write_file_mock)

        # Act & Assert
        with pytest.raises(AgentRejectionError):
            await agent.execute(sample_workflow_state)


class TestStrategyValidatorAgentTemperature:
    """Test temperature configuration."""

    def test_get_temperature_returns_low_value(
        self,
        mock_llm_client_approved: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
    ) -> None:
        """Test temperature is set to 0.3 for deterministic validation."""
        # Arrange
        agent = StrategyValidatorAgent(
            mock_llm_client_approved, mock_budget_guard, mock_settings
        )

        # Act
        temperature = agent._get_temperature()

        # Assert
        assert temperature == 0.3


class TestStrategyValidatorAgentTokenBudget:
    """Test token budget configuration."""

    @pytest.mark.asyncio
    async def test_execute_uses_correct_token_budget(
        self,
        mock_llm_client_approved: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
        monkeypatch,
    ) -> None:
        """Test execute() reserves correct token budget."""
        # Arrange
        agent = StrategyValidatorAgent(
            mock_llm_client_approved, mock_budget_guard, mock_settings
        )

        # Mock _write_file to avoid actual file I/O
        write_file_mock = AsyncMock()
        monkeypatch.setattr(agent, "_write_file", write_file_mock)

        # Act
        await agent.execute(sample_workflow_state)

        # Assert
        call_kwargs = mock_budget_guard.reserve_budget.call_args.kwargs
        assert call_kwargs["estimated_tokens"] == 6000
