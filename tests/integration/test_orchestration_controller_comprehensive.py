"""
Comprehensive tests for OrchestrationController.

Tests cover:
- Graph building and compilation
- Workflow execution
- Tier node implementations
- Routing logic
- Budget enforcement
- Iteration limits
- Error handling
"""

import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Settings
from src.exceptions import BudgetExhaustedError, InfiniteLoopDetectedError
from src.orchestration.budget_guard import BudgetGuard
from src.orchestration.checkpoints import CheckpointManager
from src.orchestration.controller import OrchestrationController
from src.orchestration.state import WorkflowState


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock(spec=Settings)
    settings.total_budget_tokens = 10000
    settings.max_monthly_budget_usd = 100.0
    return settings


@pytest.fixture
def mock_budget_guard():
    """Create mock budget guard."""
    return MagicMock(spec=BudgetGuard)


@pytest.fixture
def mock_checkpoint_manager():
    """Create mock checkpoint manager."""
    return MagicMock(spec=CheckpointManager)


@pytest.fixture
def controller(mock_settings, mock_budget_guard, mock_checkpoint_manager):
    """Create OrchestrationController instance."""
    return OrchestrationController(
        settings=mock_settings,
        budget_guard=mock_budget_guard,
        checkpoint_manager=mock_checkpoint_manager,
        max_iterations=50,
    )


class TestOrchestrationControllerInit:
    """Tests for controller initialization."""

    def test_init_with_defaults(
        self, mock_settings, mock_budget_guard, mock_checkpoint_manager
    ):
        """Test controller initialization with default parameters."""
        controller = OrchestrationController(
            settings=mock_settings,
            budget_guard=mock_budget_guard,
            checkpoint_manager=mock_checkpoint_manager,
        )

        assert controller.settings == mock_settings
        assert controller.budget_guard == mock_budget_guard
        assert controller.checkpoint_manager == mock_checkpoint_manager
        assert controller.max_iterations == 50
        assert controller.graph is None

    def test_init_with_custom_max_iterations(
        self, mock_settings, mock_budget_guard, mock_checkpoint_manager
    ):
        """Test controller initialization with custom max iterations."""
        controller = OrchestrationController(
            settings=mock_settings,
            budget_guard=mock_budget_guard,
            checkpoint_manager=mock_checkpoint_manager,
            max_iterations=100,
        )

        assert controller.max_iterations == 100


class TestBuildGraph:
    """Tests for graph building."""

    def test_build_graph_creates_compiled_graph(self, controller):
        """Test that build_graph creates a compiled StateGraph."""
        with patch("src.orchestration.controller.StateGraph") as mock_graph_class:
            mock_graph_instance = MagicMock()
            mock_compiled_graph = MagicMock()
            mock_graph_instance.compile.return_value = mock_compiled_graph
            mock_graph_class.return_value = mock_graph_instance

            result = controller.build_graph()

            assert result == mock_compiled_graph
            assert controller.graph == mock_compiled_graph
            mock_graph_instance.compile.assert_called_once()

    def test_build_graph_adds_all_tier_nodes(self, controller):
        """Test that build_graph adds all tier nodes."""
        with patch("src.orchestration.controller.StateGraph") as mock_graph_class:
            mock_graph_instance = MagicMock()
            mock_compiled_graph = MagicMock()
            mock_graph_instance.compile.return_value = mock_compiled_graph
            mock_graph_class.return_value = mock_graph_instance

            controller.build_graph()

            # Verify all tier nodes are added
            expected_nodes = [
                "tier_0_deviation",
                "tier_1_requirements",
                "tier_1_validator",
                "tier_1_architect",
                "tier_2_planner",
                "tier_2_dependencies",
                "tier_3_engineer",
                "tier_3_static_analysis",
                "tier_3_quality",
                "tier_4_security",
                "tier_4_product",
                "tier_5_docs",
                "tier_5_deployment",
            ]

            for node in expected_nodes:
                mock_graph_instance.add_node.assert_any_call(node, unittest.mock.ANY)

    def test_build_graph_sets_entry_point(self, controller):
        """Test that build_graph sets entry point."""
        with patch("src.orchestration.controller.StateGraph") as mock_graph_class:
            mock_graph_instance = MagicMock()
            mock_compiled_graph = MagicMock()
            mock_graph_instance.compile.return_value = mock_compiled_graph
            mock_graph_class.return_value = mock_graph_instance

            controller.build_graph()

            mock_graph_instance.set_entry_point.assert_called_once_with(
                "tier_1_requirements"
            )


class TestTierNodes:
    """Tests for tier node implementations."""

    @pytest.mark.asyncio
    async def test_tier_0_deviation_handler(self, controller):
        """Test Tier 0 deviation handler node."""
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "Test request",
            "current_phase": "planning",
            "current_task": "test",
            "current_agent": "TestAgent",
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
            "budget_remaining_tokens": 10000,
            "budget_remaining_usd": 100.0,
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
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        result = await controller._tier_0_deviation_handler(state)

        assert result["current_agent"] == "DeviationHandler"

    @pytest.mark.asyncio
    async def test_tier_1_requirements(self, controller):
        """Test Tier 1 requirements node."""
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "Test request",
            "current_phase": "planning",
            "current_task": "test",
            "current_agent": "TestAgent",
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
            "budget_remaining_tokens": 10000,
            "budget_remaining_usd": 100.0,
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
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        result = await controller._tier_1_requirements(state)

        assert result["current_agent"] == "RequirementsStrategy"
        assert result["current_phase"] == "planning"

    @pytest.mark.asyncio
    async def test_tier_3_engineer(self, controller):
        """Test Tier 3 engineer node."""
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "Test request",
            "current_phase": "planning",
            "current_task": "test",
            "current_agent": "TestAgent",
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
            "budget_remaining_tokens": 10000,
            "budget_remaining_usd": 100.0,
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
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        result = await controller._tier_3_engineer(state)

        assert result["current_agent"] == "SoftwareEngineer"
        assert result["current_phase"] == "development"


class TestRoutingFunctions:
    """Tests for routing logic."""

    def test_route_validator_output_with_blocking_issues(self, controller):
        """Test validator routing with blocking issues."""
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "Test request",
            "current_phase": "planning",
            "current_task": "test",
            "current_agent": "TestAgent",
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
            "budget_remaining_tokens": 10000,
            "budget_remaining_usd": 100.0,
            "quality_gates_passed": [],
            "blocking_issues": ["Issue 1"],
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
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        result = controller._route_validator_output(state)

        assert result == "tier_0_deviation"

    def test_route_validator_output_without_blocking_issues(self, controller):
        """Test validator routing without blocking issues."""
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "Test request",
            "current_phase": "planning",
            "current_task": "test",
            "current_agent": "TestAgent",
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
            "budget_remaining_tokens": 10000,
            "budget_remaining_usd": 100.0,
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
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        result = controller._route_validator_output(state)

        assert result == "tier_1_architect"

    def test_route_dependencies_output_with_blocking_issues(self, controller):
        """Test dependencies routing with blocking issues."""
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "Test request",
            "current_phase": "planning",
            "current_task": "test",
            "current_agent": "TestAgent",
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
            "budget_remaining_tokens": 10000,
            "budget_remaining_usd": 100.0,
            "quality_gates_passed": [],
            "blocking_issues": ["Issue 1"],
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
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        result = controller._route_dependencies_output(state)

        assert result == "tier_0_deviation"

    def test_route_deviation_output_with_escalation(self, controller):
        """Test deviation routing with escalation flag."""
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "Test request",
            "current_phase": "planning",
            "current_task": "test",
            "current_agent": "TestAgent",
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
            "budget_remaining_tokens": 10000,
            "budget_remaining_usd": 100.0,
            "quality_gates_passed": [],
            "blocking_issues": [],
            "awaiting_human_approval": False,
            "approval_gate": "",
            "approval_timeout": "",
            "routing_decision": {},
            "escalation_flag": True,
            "trace_id": "test-123",
            "dependencies": "",
            "infrastructure": "",
            "observability": "",
            "deviation_log": "",
            "compliance_log": "",
            "acceptance_report": "",
            "agent_token_usage": {},
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        from langgraph.graph import END

        result = controller._route_deviation_output(state)

        assert result == END

    def test_route_deviation_output_with_max_rejections(self, controller):
        """Test deviation routing with max rejections reached."""
        state: WorkflowState = {
            "workflow_id": "test-123",
            "user_request": "Test request",
            "current_phase": "planning",
            "current_task": "test",
            "current_agent": "TestAgent",
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
            "budget_remaining_tokens": 10000,
            "budget_remaining_usd": 100.0,
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
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        from langgraph.graph import END

        result = controller._route_deviation_output(state)

        assert result == END


class TestExecuteWorkflow:
    """Tests for workflow execution."""

    @pytest.mark.asyncio
    async def test_execute_workflow_builds_graph_if_needed(self, controller):
        """Test that execute_workflow builds graph if not already built."""
        controller.graph = None

        with patch.object(controller, "build_graph") as mock_build:
            mock_graph = MagicMock()
            mock_graph.astream = AsyncMock(return_value=AsyncMock())
            mock_build.return_value = mock_graph
            controller.graph = mock_graph

            # Mock astream to return empty async generator
            async def mock_astream(*args, **kwargs):
                # LangGraph wraps state updates in node names
                yield {
                    "planning": {
                        "workflow_id": "test-123",
                        "user_request": "Test request",
                        "current_phase": "planning",
                        "current_task": "test",
                        "current_agent": "TestAgent",
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
                        "budget_remaining_tokens": 10000,
                        "budget_remaining_usd": 100.0,
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
                        "created_at": datetime.now(UTC).isoformat(),
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                }

            mock_graph.astream = mock_astream

            result = await controller.execute_workflow("Test request", "test-123")

            assert result["workflow_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_execute_workflow_raises_budget_exhausted(self, controller):
        """Test that execute_workflow raises BudgetExhaustedError when budget exhausted."""
        mock_graph = MagicMock()
        controller.graph = mock_graph

        async def mock_astream(*args, **kwargs):
            # LangGraph wraps state updates in node names
            yield {
                "planning": {
                    "workflow_id": "test-123",
                    "user_request": "Test request",
                    "current_phase": "planning",
                    "current_task": "test",
                    "current_agent": "TestAgent",
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
                    "budget_used_tokens": 10000,
                    "budget_used_usd": 100.0,
                    "budget_remaining_tokens": -1,
                    "budget_remaining_usd": -1.0,
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
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            }

        mock_graph.astream = mock_astream

        with pytest.raises(BudgetExhaustedError):
            await controller.execute_workflow("Test request", "test-123")

    @pytest.mark.asyncio
    async def test_execute_workflow_raises_infinite_loop_detected(self, controller):
        """Test that execute_workflow raises InfiniteLoopDetectedError at max iterations."""
        controller.max_iterations = 2
        mock_graph = MagicMock()
        controller.graph = mock_graph

        async def mock_astream(*args, **kwargs):
            for _i in range(3):
                # LangGraph wraps state updates in node names
                yield {
                    "planning": {
                        "workflow_id": "test-123",
                        "user_request": "Test request",
                        "current_phase": "planning",
                        "current_task": "test",
                        "current_agent": "TestAgent",
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
                        "budget_remaining_tokens": 10000,
                        "budget_remaining_usd": 100.0,
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
                        "created_at": datetime.now(UTC).isoformat(),
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                }

        mock_graph.astream = mock_astream

        with pytest.raises(InfiniteLoopDetectedError):
            await controller.execute_workflow("Test request", "test-123")
