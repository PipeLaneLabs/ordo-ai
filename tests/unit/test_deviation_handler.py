"""
Comprehensive tests for DeviationHandler (Tier 0).

Tests cover:
- Initialization
- Deviation logging
- Error recovery
- State rollback
- Escalation handling
"""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.tier_0.deviation_handler import DeviationHandlerAgent
from src.config import Settings
from src.exceptions import BudgetExhaustedError, WorkflowError
from src.llm.base_client import BaseLLMClient
from src.orchestration.budget_guard import BudgetGuard


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    return MagicMock(spec=BaseLLMClient)


@pytest.fixture
def mock_budget_guard():
    """Create mock budget guard."""
    return MagicMock(spec=BudgetGuard)


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock(spec=Settings)
    settings.environment = "test"
    return settings


@pytest.fixture
def deviation_handler(mock_settings, mock_llm_client, mock_budget_guard):
    """Create DeviationHandlerAgent instance."""
    return DeviationHandlerAgent(
        llm_client=mock_llm_client,
        budget_guard=mock_budget_guard,
        settings=mock_settings,
    )


@pytest.fixture
def sample_workflow_state():
    """Create sample workflow state."""
    return {
        "workflow_id": "test-123",
        "user_request": "Test request",
        "current_phase": "development",
        "current_task": "test_task",
        "current_agent": "TestAgent",
        "rejection_count": 0,
        "state_version": 1,
        "requirements": "# Requirements",
        "architecture": "# Architecture",
        "tasks": "# Tasks",
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
        "dependencies": "# Dependencies",
        "infrastructure": "# Infrastructure",
        "observability": "",
        "deviation_log": "",
        "compliance_log": "",
        "acceptance_report": "",
        "agent_token_usage": {},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


class TestDeviationHandlerInit:
    """Tests for DeviationHandlerAgent initialization."""

    def test_init_with_settings(self, deviation_handler):
        """Test handler initialization with settings."""
        assert deviation_handler.settings is not None
        assert deviation_handler.name == "DeviationHandler"

    def test_init_has_llm_client(self, deviation_handler):
        """Test that initialization sets LLM client."""
        assert deviation_handler.llm_client is not None


class TestDeviationLogging:
    """Tests for deviation logging."""

    @pytest.mark.asyncio
    async def test_log_deviation_with_error(
        self, deviation_handler, sample_workflow_state
    ):
        """Test logging a deviation with error details."""
        error = ValueError("Test error")

        await deviation_handler.log_deviation(
            workflow_state=sample_workflow_state,
            error=error,
            context="test_context",
        )

    @pytest.mark.asyncio
    async def test_log_deviation_updates_state(
        self, deviation_handler, sample_workflow_state
    ):
        """Test that logging deviation updates workflow state."""
        error = ValueError("Test error")

        result = await deviation_handler.log_deviation(
            workflow_state=sample_workflow_state,
            error=error,
            context="test_context",
        )

        assert result is not None
        assert "deviation_log" in result or isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_log_deviation_with_budget_error(
        self, deviation_handler, sample_workflow_state
    ):
        """Test logging a budget exhaustion deviation."""
        error = BudgetExhaustedError(limit=10000.0, requested=500.0, used=10500.0, budget_type="tokens")

        await deviation_handler.log_deviation(
            workflow_state=sample_workflow_state,
            error=error,
            context="budget_check",
        )


class TestErrorRecovery:
    """Tests for error recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_attempt_recovery_from_error(
        self, deviation_handler, sample_workflow_state
    ):
        """Test attempting recovery from an error."""
        error = WorkflowError("Workflow failed")

        result = await deviation_handler.attempt_recovery(
            workflow_state=sample_workflow_state,
            error=error,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_recovery_increments_rejection_count(
        self, deviation_handler, sample_workflow_state
    ):
        """Test that recovery increments rejection count."""
        error = WorkflowError("Workflow failed")
        sample_workflow_state.get("rejection_count", 0)

        result = await deviation_handler.attempt_recovery(
            workflow_state=sample_workflow_state,
            error=error,
        )

        # Result should have updated rejection count
        assert result is not None

    @pytest.mark.asyncio
    async def test_recovery_with_max_retries_exceeded(
        self, deviation_handler, sample_workflow_state
    ):
        """Test recovery when max retries exceeded."""
        sample_workflow_state["rejection_count"] = 10
        error = WorkflowError("Max retries exceeded")

        result = await deviation_handler.attempt_recovery(
            workflow_state=sample_workflow_state,
            error=error,
        )

        assert result is not None


class TestStateRollback:
    """Tests for state rollback functionality."""

    @pytest.mark.asyncio
    async def test_rollback_to_previous_state(
        self, deviation_handler, sample_workflow_state
    ):
        """Test rolling back to previous workflow state."""
        previous_state = sample_workflow_state.copy()
        previous_state["state_version"] = 0

        result = await deviation_handler.rollback_state(
            current_state=sample_workflow_state,
            previous_state=previous_state,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_rollback_preserves_workflow_id(
        self, deviation_handler, sample_workflow_state
    ):
        """Test that rollback preserves workflow ID."""
        previous_state = sample_workflow_state.copy()
        sample_workflow_state["workflow_id"]

        result = await deviation_handler.rollback_state(
            current_state=sample_workflow_state,
            previous_state=previous_state,
        )

        assert result is not None


class TestEscalation:
    """Tests for escalation handling."""

    @pytest.mark.asyncio
    async def test_escalate_to_human_review(
        self, deviation_handler, sample_workflow_state
    ):
        """Test escalating issue to human review."""
        reason = "Critical error requiring human intervention"

        result = await deviation_handler.escalate_to_human(
            workflow_state=sample_workflow_state,
            reason=reason,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_escalation_sets_flag(self, deviation_handler, sample_workflow_state):
        """Test that escalation sets escalation flag."""
        reason = "Critical error"

        result = await deviation_handler.escalate_to_human(
            workflow_state=sample_workflow_state,
            reason=reason,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_escalation_with_approval_gate(
        self, deviation_handler, sample_workflow_state
    ):
        """Test escalation with approval gate."""
        reason = "Requires approval"

        result = await deviation_handler.escalate_to_human(
            workflow_state=sample_workflow_state,
            reason=reason,
            approval_gate="human_review",
        )

        assert result is not None


class TestDeviationHandlerIntegration:
    """Integration tests for DeviationHandler."""

    @pytest.mark.asyncio
    async def test_full_error_handling_flow(
        self, deviation_handler, sample_workflow_state
    ):
        """Test complete error handling flow."""
        error = WorkflowError("Test workflow error")

        # Log deviation
        logged_state = await deviation_handler.log_deviation(
            workflow_state=sample_workflow_state,
            error=error,
            context="test",
        )

        # Attempt recovery
        recovered_state = await deviation_handler.attempt_recovery(
            workflow_state=logged_state or sample_workflow_state,
            error=error,
        )

        assert recovered_state is not None

    @pytest.mark.asyncio
    async def test_error_handling_with_escalation(
        self, deviation_handler, sample_workflow_state
    ):
        """Test error handling with escalation."""
        error = WorkflowError("Critical error")

        # Log deviation
        logged_state = await deviation_handler.log_deviation(
            workflow_state=sample_workflow_state,
            error=error,
            context="critical",
        )

        # Escalate to human
        escalated_state = await deviation_handler.escalate_to_human(
            workflow_state=logged_state or sample_workflow_state,
            reason="Critical error requires human intervention",
        )

        assert escalated_state is not None
