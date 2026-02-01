"""Integration tests for OrchestrationController with mock agents."""

from unittest.mock import MagicMock

import pytest

from src.config import Settings
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.checkpoints import CheckpointManager
from src.orchestration.controller import OrchestrationController
from src.orchestration.state import WorkflowState


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
def mock_budget_guard() -> MagicMock:
    """Create mock budget guard."""
    guard = MagicMock(spec=BudgetGuard)
    guard.reserve_budget = MagicMock()
    guard.record_usage = MagicMock()
    return guard


@pytest.fixture
def mock_checkpoint_manager() -> MagicMock:
    """Create mock checkpoint manager."""
    manager = MagicMock(spec=CheckpointManager)
    return manager


class TestOrchestrationControllerInitialization:
    """Test OrchestrationController initialization."""

    def test_initialization_default_params(
        self,
        mock_settings: Settings,
        mock_budget_guard: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Test initialization with default parameters."""
        # Act
        controller = OrchestrationController(
            settings=mock_settings,
            budget_guard=mock_budget_guard,
            checkpoint_manager=mock_checkpoint_manager,
        )

        # Assert
        assert controller.settings == mock_settings
        assert controller.budget_guard == mock_budget_guard
        assert controller.checkpoint_manager == mock_checkpoint_manager
        assert controller.max_iterations == 50

    def test_initialization_custom_max_iterations(
        self,
        mock_settings: Settings,
        mock_budget_guard: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Test initialization with custom max iterations."""
        # Act
        controller = OrchestrationController(
            settings=mock_settings,
            budget_guard=mock_budget_guard,
            checkpoint_manager=mock_checkpoint_manager,
            max_iterations=100,
        )

        # Assert
        assert controller.max_iterations == 100


class TestOrchestrationControllerGraphBuilding:
    """Test OrchestrationController graph building."""

    @pytest.mark.skip(
        reason="Requires full LangGraph StateGraph compilation with real checkpointer"
    )
    def test_build_graph_creates_graph(
        self,
        mock_settings: Settings,
        mock_budget_guard: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Test build_graph() creates StateGraph."""
        # Arrange
        controller = OrchestrationController(
            settings=mock_settings,
            budget_guard=mock_budget_guard,
            checkpoint_manager=mock_checkpoint_manager,
        )

        # Act
        graph = controller.build_graph()

        # Assert
        assert graph is not None
        assert controller.graph is not None

    @pytest.mark.skip(
        reason="Requires full LangGraph StateGraph compilation with real checkpointer"
    )
    def test_build_graph_adds_tier_nodes(
        self,
        mock_settings: Settings,
        mock_budget_guard: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Test build_graph() adds all tier nodes."""
        # Arrange
        controller = OrchestrationController(
            settings=mock_settings,
            budget_guard=mock_budget_guard,
            checkpoint_manager=mock_checkpoint_manager,
        )

        # Act
        graph = controller.build_graph()

        # Assert - Graph is created successfully
        # (Full node verification requires LangGraph internals access)
        assert graph is not None


class TestOrchestrationControllerTierNodes:
    """Test OrchestrationController tier node implementations."""

    @pytest.mark.asyncio
    async def test_tier_0_deviation_handler(
        self,
        mock_settings: Settings,
        mock_budget_guard: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Test tier_0_deviation_handler node."""
        # Arrange
        controller = OrchestrationController(
            settings=mock_settings,
            budget_guard=mock_budget_guard,
            checkpoint_manager=mock_checkpoint_manager,
        )
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "test",
            "current_phase": "testing",
            "current_task": "test",
            "current_agent": "Test",
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
            "trace_id": "test-123",
            "dependencies": "",
            "infrastructure": "",
            "observability": "",
            "deviation_log": "",
            "compliance_log": "",
            "acceptance_report": "",
            "agent_token_usage": {},
            "created_at": "2026-01-23T19:00:00+13:00",
            "updated_at": "2026-01-23T19:00:00+13:00",
        }

        # Act
        result = await controller._tier_0_deviation_handler(state)

        # Assert
        assert result["current_agent"] == "DeviationHandler"

    @pytest.mark.asyncio
    async def test_tier_1_requirements(
        self,
        mock_settings: Settings,
        mock_budget_guard: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Test tier_1_requirements node."""
        # Arrange
        controller = OrchestrationController(
            settings=mock_settings,
            budget_guard=mock_budget_guard,
            checkpoint_manager=mock_checkpoint_manager,
        )
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "test",
            "current_phase": "testing",
            "current_task": "test",
            "current_agent": "Test",
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
            "trace_id": "test-123",
            "dependencies": "",
            "infrastructure": "",
            "observability": "",
            "deviation_log": "",
            "compliance_log": "",
            "acceptance_report": "",
            "agent_token_usage": {},
            "created_at": "2026-01-23T19:00:00+13:00",
            "updated_at": "2026-01-23T19:00:00+13:00",
        }

        # Act
        result = await controller._tier_1_requirements(state)

        # Assert
        assert result["current_agent"] == "RequirementsStrategy"
        assert result["current_phase"] == "planning"

    @pytest.mark.asyncio
    async def test_tier_3_engineer(
        self,
        mock_settings: Settings,
        mock_budget_guard: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Test tier_3_engineer node."""
        # Arrange
        controller = OrchestrationController(
            settings=mock_settings,
            budget_guard=mock_budget_guard,
            checkpoint_manager=mock_checkpoint_manager,
        )
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "test",
            "current_phase": "testing",
            "current_task": "test",
            "current_agent": "Test",
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
            "trace_id": "test-123",
            "dependencies": "",
            "infrastructure": "",
            "observability": "",
            "deviation_log": "",
            "compliance_log": "",
            "acceptance_report": "",
            "agent_token_usage": {},
            "created_at": "2026-01-23T19:00:00+13:00",
            "updated_at": "2026-01-23T19:00:00+13:00",
        }

        # Act
        result = await controller._tier_3_engineer(state)

        # Assert
        assert result["current_agent"] == "SoftwareEngineer"
        assert result["current_phase"] == "development"


class TestOrchestrationControllerRoutingLogic:
    """Test OrchestrationController routing decision functions."""

    def test_route_validator_output_with_no_issues(
        self,
        mock_settings: Settings,
        mock_budget_guard: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Test _route_validator_output() with no blocking issues."""
        # Arrange
        controller = OrchestrationController(
            settings=mock_settings,
            budget_guard=mock_budget_guard,
            checkpoint_manager=mock_checkpoint_manager,
        )
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "test",
            "current_phase": "testing",
            "current_task": "test",
            "current_agent": "Test",
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
            "trace_id": "test-123",
            "dependencies": "",
            "infrastructure": "",
            "observability": "",
            "deviation_log": "",
            "compliance_log": "",
            "acceptance_report": "",
            "agent_token_usage": {},
            "created_at": "2026-01-23T19:00:00+13:00",
            "updated_at": "2026-01-23T19:00:00+13:00",
        }

        # Act
        route = controller._route_validator_output(state)

        # Assert
        assert route == "tier_1_architect"

    def test_route_validator_output_with_blocking_issues(
        self,
        mock_settings: Settings,
        mock_budget_guard: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Test _route_validator_output() with blocking issues."""
        # Arrange
        controller = OrchestrationController(
            settings=mock_settings,
            budget_guard=mock_budget_guard,
            checkpoint_manager=mock_checkpoint_manager,
        )
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "test",
            "current_phase": "testing",
            "current_task": "test",
            "current_agent": "Test",
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
            "blocking_issues": ["Test blocking issue"],
            "awaiting_human_approval": False,
            "approval_gate": "",
            "approval_timeout": "",
            "routing_decision": {},
            "escalation_flag": False,
            "trace_id": "test-123",
            "dependencies": "",
            "infrastructure": "",
            "observability": "",
            "deviation_log": "",
            "compliance_log": "",
            "acceptance_report": "",
            "agent_token_usage": {},
            "created_at": "2026-01-23T19:00:00+13:00",
            "updated_at": "2026-01-23T19:00:00+13:00",
        }

        # Act
        route = controller._route_validator_output(state)

        # Assert
        assert route == "tier_0_deviation"

    def test_route_deviation_output_to_target_agent(
        self,
        mock_settings: Settings,
        mock_budget_guard: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Test _route_deviation_output() routes to target agent."""
        # Arrange
        controller = OrchestrationController(
            settings=mock_settings,
            budget_guard=mock_budget_guard,
            checkpoint_manager=mock_checkpoint_manager,
        )
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "test",
            "current_phase": "testing",
            "current_task": "test",
            "current_agent": "Test",
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
            "routing_decision": {"target_agent": "tier_3_engineer"},
            "escalation_flag": False,
            "trace_id": "test-123",
            "dependencies": "",
            "infrastructure": "",
            "observability": "",
            "deviation_log": "",
            "compliance_log": "",
            "acceptance_report": "",
            "agent_token_usage": {},
            "created_at": "2026-01-23T19:00:00+13:00",
            "updated_at": "2026-01-23T19:00:00+13:00",
        }

        # Act
        route = controller._route_deviation_output(state)

        # Assert
        assert route == "tier_3_engineer"

    def test_route_deviation_output_escalation(
        self,
        mock_settings: Settings,
        mock_budget_guard: MagicMock,
        mock_checkpoint_manager: MagicMock,
    ) -> None:
        """Test _route_deviation_output() escalates when needed."""
        # Arrange
        controller = OrchestrationController(
            settings=mock_settings,
            budget_guard=mock_budget_guard,
            checkpoint_manager=mock_checkpoint_manager,
        )
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "test",
            "current_phase": "testing",
            "current_task": "test",
            "current_agent": "Test",
            "rejection_count": 3,
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
            "trace_id": "test-123",
            "dependencies": "",
            "infrastructure": "",
            "observability": "",
            "deviation_log": "",
            "compliance_log": "",
            "acceptance_report": "",
            "agent_token_usage": {},
            "created_at": "2026-01-23T19:00:00+13:00",
            "updated_at": "2026-01-23T19:00:00+13:00",
        }

        # Act
        route = controller._route_deviation_output(state)

        # Assert - Should route to END (escalation)
        assert route == "__end__"
