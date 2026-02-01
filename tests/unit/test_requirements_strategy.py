"""Unit tests for Requirements & Strategy Agent."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.tier_1.requirements_strategy import RequirementsStrategyAgent
from src.config import Settings
from src.llm.base_client import LLMResponse
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.state import WorkflowState


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    """Create mock LLM client."""
    client = AsyncMock()
    client.generate = AsyncMock(
        return_value=LLMResponse(
            content="""# Requirements Specification

**Project:** Test Project
**Version:** 1.0
**Date:** 2026-01-23
**Author:** Requirements & Strategy Agent

## 1. Executive Summary

Test requirements document.

## 2. Functional Requirements

### FR-001: User Authentication
- **Description:** Users must be able to log in
- **Priority:** Critical
- **Acceptance Criteria:**
  - [ ] User can log in with email and password
  - [ ] Session persists for 24 hours

## 3. Non-Functional Requirements

### NFR-001: Performance
- **Metric:** Response time
- **Target:** < 200ms
- **Priority:** High

## 5. Security Requirements

### SEC-001: Password Security
- **Description:** Passwords must be hashed
- **Implementation:** bcrypt
- **Priority:** Critical
""",
            model="deepseek-r1",
            tokens_used=500,
            tokens_prompt=250,
            tokens_completion=250,
            cost_usd=0.005,
            latency_ms=1500,
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
    """Create sample workflow state."""
    return {
        "workflow_id": "test-workflow-789",
        "user_request": "Create a user authentication system",
        "current_phase": "planning",
        "current_task": "requirements",
        "current_agent": "RequirementsStrategyAgent",
        "rejection_count": 0,
        "state_version": 1,
        "requirements": "",
        "architecture": "",
        "tasks": "",
        "code_files": {},
        "test_files": {},
        "partial_artifacts": {},
        "validation_report": "",
        "quality_report": "",
        "security_report": "",
        "budget_used_tokens": 0,
        "budget_used_usd": 0.0,
        "budget_remaining_tokens": 100000,
        "budget_remaining_usd": 10.0,
        "quality_gates_passed": [],
        "blocking_issues": [],
        "awaiting_human_approval": False,
        "approval_gate": "",
        "approval_timeout": "",
        "routing_decision": {},
        "escalation_flag": False,
        "trace_id": "test-trace-789",
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


class TestRequirementsStrategyAgentInitialization:
    """Test RequirementsStrategyAgent initialization."""

    def test_initialization(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
    ) -> None:
        """Test agent initialization with correct parameters."""
        # Act
        agent = RequirementsStrategyAgent(
            llm_client=mock_llm_client,
            budget_guard=mock_budget_guard,
            settings=mock_settings,
        )

        # Assert
        assert agent.name == "RequirementsStrategyAgent"
        assert agent.token_budget == 8000
        assert agent.llm_client == mock_llm_client
        assert agent.budget_guard == mock_budget_guard


class TestRequirementsStrategyAgentPromptBuilding:
    """Test prompt building for requirements analysis."""

    @pytest.mark.asyncio
    async def test_build_prompt_with_user_request(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
    ) -> None:
        """Test prompt includes user request."""
        # Arrange
        agent = RequirementsStrategyAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )

        # Act
        prompt = await agent._build_prompt(sample_workflow_state)

        # Assert
        assert "Create a user authentication system" in prompt
        assert "Requirements Analysis Task" in prompt
        assert "Functional Requirements" in prompt
        assert "Non-Functional Requirements" in prompt
        assert "Security Requirements" in prompt

    @pytest.mark.asyncio
    async def test_build_prompt_includes_analysis_framework(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
    ) -> None:
        """Test prompt includes comprehensive analysis framework."""
        # Arrange
        agent = RequirementsStrategyAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )

        # Act
        prompt = await agent._build_prompt(sample_workflow_state)

        # Assert
        assert "Acceptance Criteria" in prompt
        assert "Constraints" in prompt
        assert "REQUIREMENTS.md" in prompt


class TestRequirementsStrategyAgentOutputParsing:
    """Test output parsing and REQUIREMENTS.md generation."""

    @pytest.mark.asyncio
    async def test_parse_output_generates_requirements_file(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
        monkeypatch,
    ) -> None:
        """Test _parse_output generates REQUIREMENTS.md file."""
        # Arrange
        agent = RequirementsStrategyAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )
        response = LLMResponse(
            content="# Requirements Specification\n\n## 2. Functional Requirements\n\n## 3. Non-Functional Requirements\n\n## 5. Security Requirements",
            model="deepseek-r1",
            tokens_used=500,
            tokens_prompt=250,
            tokens_completion=250,
            cost_usd=0.005,
            latency_ms=1500,
            provider="openrouter",
            finish_reason="stop",
        )

        # Mock _write_file to avoid actual file I/O
        write_file_mock = AsyncMock()
        monkeypatch.setattr(agent, "_write_file", write_file_mock)

        # Act
        result = await agent._parse_output(response, sample_workflow_state)

        # Assert
        assert result["requirements_generated"] is True
        assert result["requirements_token_count"] == 500
        assert "requirements" in result
        write_file_mock.assert_called_once_with(
            "REQUIREMENTS.md", result["requirements"]
        )

    @pytest.mark.asyncio
    async def test_parse_output_removes_markdown_code_blocks(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
        monkeypatch,
    ) -> None:
        """Test _parse_output removes markdown code blocks."""
        # Arrange
        agent = RequirementsStrategyAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )
        response = LLMResponse(
            content="```markdown\n# Requirements Specification\n\n## 2. Functional Requirements\n```",
            model="deepseek-r1",
            tokens_used=100,
            tokens_prompt=50,
            tokens_completion=50,
            cost_usd=0.001,
            latency_ms=500,
            provider="openrouter",
            finish_reason="stop",
        )

        # Mock _write_file to avoid actual file I/O
        write_file_mock = AsyncMock()
        monkeypatch.setattr(agent, "_write_file", write_file_mock)

        # Act
        result = await agent._parse_output(response, sample_workflow_state)

        # Assert
        assert "```markdown" not in result["requirements"]
        assert "# Requirements Specification" in result["requirements"]


class TestRequirementsStrategyAgentTemperature:
    """Test temperature configuration."""

    def test_get_temperature_returns_moderate_value(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
    ) -> None:
        """Test temperature is set to 0.4 for structured output."""
        # Arrange
        agent = RequirementsStrategyAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )

        # Act
        temperature = agent._get_temperature()

        # Assert
        assert temperature == 0.4


class TestRequirementsStrategyAgentExecution:
    """Test full agent execution flow."""

    @pytest.mark.asyncio
    async def test_execute_generates_requirements(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
        monkeypatch,
    ) -> None:
        """Test execute() generates requirements successfully."""
        # Arrange
        agent = RequirementsStrategyAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )

        # Mock _write_file to avoid actual file I/O
        write_file_mock = AsyncMock()
        monkeypatch.setattr(agent, "_write_file", write_file_mock)

        # Act
        result_state = await agent.execute(sample_workflow_state)

        # Assert
        mock_budget_guard.reserve_budget.assert_called_once()
        mock_llm_client.generate.assert_called_once()
        mock_budget_guard.record_usage.assert_called_once()
        assert result_state["current_agent"] == "RequirementsStrategyAgent"
        assert result_state["state_version"] == 2

    @pytest.mark.asyncio
    async def test_execute_uses_correct_token_budget(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
    ) -> None:
        """Test execute() reserves correct token budget."""
        # Arrange
        agent = RequirementsStrategyAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )

        # Act
        await agent.execute(sample_workflow_state)

        # Assert
        call_kwargs = mock_budget_guard.reserve_budget.call_args.kwargs
        assert call_kwargs["estimated_tokens"] == 8000
