"""Unit tests for Solution Architect Agent."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.tier_1.solution_architect import SolutionArchitectAgent
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
            content="""# System Architecture

**Project:** Test Project
**Version:** 1.0
**Date:** 2026-01-24
**Architect:** Solution Architect Agent

## 2. Technology Stack

### 2.1 Backend
- **Language:** Python 3.12
- **Framework:** FastAPI 0.110+
- **API Style:** REST

### 2.2 Frontend
- **Framework:** React 18

### 2.3 Database
- **Primary Database:** PostgreSQL 15

## 4. Architectural Decision Records (ADRs)

### ADR-001: Use FastAPI for Backend
- **Status:** Accepted
- **Context:** Need high-performance async API framework
- **Decision:** Use FastAPI
- **Consequences:** Fast development, excellent docs

## 5. Security Architecture

### 5.1 Authentication
- **Mechanism:** JWT tokens
""",
            model="deepseek-r1",
            tokens_used=600,
            tokens_prompt=300,
            tokens_completion=300,
            cost_usd=0.006,
            latency_ms=1800,
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
    """Create sample workflow state with requirements and validation."""
    return {
        "workflow_id": "test-workflow-791",
        "user_request": "Create a user authentication system",
        "current_phase": "planning",
        "current_task": "architecture",
        "current_agent": "SolutionArchitectAgent",
        "rejection_count": 0,
        "state_version": 1,
        "requirements": "# Requirements\n\nTest requirements content",
        "architecture": "",
        "tasks": "",
        "code_files": {},
        "test_files": {},
        "partial_artifacts": {},
        "validation_report": "# Validation Report\n\nAPPROVED",
        "quality_report": "",
        "security_report": "",
        "budget_used_tokens": 900,
        "budget_used_usd": 0.009,
        "budget_remaining_tokens": 99100,
        "budget_remaining_usd": 9.991,
        "quality_gates_passed": ["requirements_validation"],
        "blocking_issues": [],
        "awaiting_human_approval": False,
        "approval_gate": "",
        "approval_timeout": "",
        "routing_decision": {},
        "escalation_flag": False,
        "trace_id": "test-trace-791",
        "dependencies": "",
        "infrastructure": "",
        "observability": "",
        "deviation_log": "",
        "compliance_log": "",
        "acceptance_report": "",
        "agent_token_usage": {},
        "created_at": "2026-01-24T00:00:00+13:00",
        "updated_at": "2026-01-24T00:00:00+13:00",
    }


class TestSolutionArchitectAgentInitialization:
    """Test SolutionArchitectAgent initialization."""

    def test_initialization(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
    ) -> None:
        """Test agent initialization with correct parameters."""
        # Act
        agent = SolutionArchitectAgent(
            llm_client=mock_llm_client,
            budget_guard=mock_budget_guard,
            settings=mock_settings,
        )

        # Assert
        assert agent.name == "SolutionArchitectAgent"
        assert agent.token_budget == 8000
        assert agent.llm_client == mock_llm_client
        assert agent.budget_guard == mock_budget_guard


class TestSolutionArchitectAgentPromptBuilding:
    """Test prompt building for architecture design."""

    @pytest.mark.asyncio
    async def test_build_prompt_includes_requirements(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
    ) -> None:
        """Test prompt includes requirements."""
        # Arrange
        agent = SolutionArchitectAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )

        # Act
        prompt = await agent._build_prompt(sample_workflow_state)

        # Assert
        assert "Test requirements content" in prompt
        assert "System Architecture Design Task" in prompt
        assert "Technology Stack Selection" in prompt
        assert "System Design" in prompt
        assert "Architectural Decision Records" in prompt

    @pytest.mark.asyncio
    async def test_build_prompt_includes_validation_report(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
    ) -> None:
        """Test prompt includes validation report."""
        # Arrange
        agent = SolutionArchitectAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )

        # Act
        prompt = await agent._build_prompt(sample_workflow_state)

        # Assert
        assert "APPROVED" in prompt
        assert "Validation Report" in prompt


class TestSolutionArchitectAgentOutputParsing:
    """Test output parsing and ARCHITECTURE.md generation."""

    @pytest.mark.asyncio
    async def test_parse_output_generates_architecture_file(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
        monkeypatch,
    ) -> None:
        """Test _parse_output generates ARCHITECTURE.md file."""
        # Arrange
        agent = SolutionArchitectAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )
        response = await mock_llm_client.generate(prompt="test", max_tokens=1000)

        # Mock _write_file to avoid actual file I/O
        write_file_mock = AsyncMock()
        monkeypatch.setattr(agent, "_write_file", write_file_mock)

        # Act
        result = await agent._parse_output(response, sample_workflow_state)

        # Assert
        assert result["architecture_generated"] is True
        assert result["architecture_token_count"] == 600
        assert "architecture" in result
        write_file_mock.assert_called_once_with(
            "ARCHITECTURE.md", result["architecture"]
        )

    @pytest.mark.asyncio
    async def test_parse_output_extracts_tech_stack(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
        monkeypatch,
    ) -> None:
        """Test _parse_output extracts technology stack."""
        # Arrange
        agent = SolutionArchitectAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )
        response = await mock_llm_client.generate(prompt="test", max_tokens=1000)

        # Mock _write_file
        write_file_mock = AsyncMock()
        monkeypatch.setattr(agent, "_write_file", write_file_mock)

        # Act
        result = await agent._parse_output(response, sample_workflow_state)

        # Assert
        assert "tech_stack" in result
        assert result["tech_stack"]["backend"] == "Defined"
        assert result["tech_stack"]["frontend"] == "Defined"
        assert result["tech_stack"]["database"] == "Defined"

    @pytest.mark.asyncio
    async def test_parse_output_counts_adrs(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
        monkeypatch,
    ) -> None:
        """Test _parse_output counts ADRs."""
        # Arrange
        agent = SolutionArchitectAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )
        response = await mock_llm_client.generate(prompt="test", max_tokens=1000)

        # Mock _write_file
        write_file_mock = AsyncMock()
        monkeypatch.setattr(agent, "_write_file", write_file_mock)

        # Act
        result = await agent._parse_output(response, sample_workflow_state)

        # Assert
        assert result["adr_count"] == 1  # One ADR in mock response


class TestSolutionArchitectAgentTemperature:
    """Test temperature configuration."""

    def test_get_temperature_returns_moderate_value(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
    ) -> None:
        """Test temperature is set to 0.5 for balanced design."""
        # Arrange
        agent = SolutionArchitectAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )

        # Act
        temperature = agent._get_temperature()

        # Assert
        assert temperature == 0.5


class TestSolutionArchitectAgentExecution:
    """Test full agent execution flow."""

    @pytest.mark.asyncio
    async def test_execute_generates_architecture(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
        monkeypatch,
    ) -> None:
        """Test execute() generates architecture successfully."""
        # Arrange
        agent = SolutionArchitectAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )

        # Mock _write_file
        write_file_mock = AsyncMock()
        monkeypatch.setattr(agent, "_write_file", write_file_mock)

        # Act
        result_state = await agent.execute(sample_workflow_state)

        # Assert
        mock_budget_guard.reserve_budget.assert_called_once()
        mock_llm_client.generate.assert_called_once()
        mock_budget_guard.record_usage.assert_called_once()
        assert result_state["current_agent"] == "SolutionArchitectAgent"
        assert result_state["state_version"] == 2

    @pytest.mark.asyncio
    async def test_execute_uses_correct_token_budget(
        self,
        mock_llm_client: AsyncMock,
        mock_budget_guard: MagicMock,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
        monkeypatch,
    ) -> None:
        """Test execute() reserves correct token budget."""
        # Arrange
        agent = SolutionArchitectAgent(
            mock_llm_client, mock_budget_guard, mock_settings
        )

        # Mock _write_file
        write_file_mock = AsyncMock()
        monkeypatch.setattr(agent, "_write_file", write_file_mock)

        # Act
        await agent.execute(sample_workflow_state)

        # Assert
        call_kwargs = mock_budget_guard.reserve_budget.call_args.kwargs
        assert call_kwargs["estimated_tokens"] == 8000
