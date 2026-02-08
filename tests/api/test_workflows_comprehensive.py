"""
Comprehensive tests for workflow API endpoints.

Tests cover all workflow control endpoints including:
- Starting workflows
- Checking workflow status
- Approving/rejecting workflows
- Retrieving budget information
- Authentication and authorization
- Error handling and edge cases
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status


try:
    from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
except ImportError:
    try:
        from jwt import ExpiredSignatureError, InvalidTokenError
    except ImportError:
        # Fallback for PyJWT 2.8+
        class ExpiredSignatureError(Exception):
            pass

        class InvalidTokenError(Exception):
            pass


from src.api.schemas import (
    AgentTier,
    ApprovalRequest,
    WorkflowStartRequest,
    WorkflowStatus,
)
from src.api.workflows import (
    _WORKFLOWS,
    _check_permission_dependency,
    _WorkflowRecord,
    approve_workflow,
    get_current_user,
    get_workflow_budget,
    get_workflow_status,
    start_workflow,
)


class TestGetCurrentUser:
    """Tests for JWT token extraction and validation."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test extracting user from valid JWT token."""
        valid_payload = {"sub": "user123", "roles": ["admin"]}

        with patch("src.api.workflows.jwt_service.verify_token") as mock_verify:
            mock_verify.return_value = valid_payload
            result = await get_current_user("valid_token")

            assert result == valid_payload
            mock_verify.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self):
        """Test handling of expired JWT token."""
        with patch("src.api.workflows.jwt_service.verify_token") as mock_verify:
            mock_verify.side_effect = ExpiredSignatureError("Token expired")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("expired_token")

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert exc_info.value.detail == "Token expired"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test handling of invalid JWT token."""
        with patch("src.api.workflows.jwt_service.verify_token") as mock_verify:
            mock_verify.side_effect = InvalidTokenError("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("invalid_token")

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert exc_info.value.detail == "Invalid token"


class TestCheckPermissionDependency:
    """Tests for permission checking."""

    @pytest.mark.asyncio
    async def test_check_permission_granted(self):
        """Test permission check when user has required permission."""
        user = {"sub": "user123", "roles": ["admin"]}

        with patch("src.api.workflows.check_permission") as mock_check:
            mock_check.return_value = True
            result = await _check_permission_dependency("workflow:start", user)

            assert result == user
            mock_check.assert_called_once_with(["admin"], "workflow:start")

    @pytest.mark.asyncio
    async def test_check_permission_denied(self):
        """Test permission check when user lacks required permission."""
        user = {"sub": "user123", "roles": ["viewer"]}

        with patch("src.api.workflows.check_permission") as mock_check:
            mock_check.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await _check_permission_dependency("workflow:start", user)

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Missing permission" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_check_permission_no_roles(self):
        """Test permission check when user has no roles."""
        user = {"sub": "user123"}

        with patch("src.api.workflows.check_permission") as mock_check:
            mock_check.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await _check_permission_dependency("workflow:start", user)

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestStartWorkflow:
    """Tests for workflow start endpoint."""

    @pytest.mark.asyncio
    async def test_start_workflow_success(self):
        """Test successful workflow start."""
        _WORKFLOWS.clear()

        request = WorkflowStartRequest(
            user_request="Create a new feature for the system", priority=5
        )
        user = {"sub": "user123", "roles": ["admin"]}

        with (
            patch("src.api.workflows.bind_workflow_context"),
            patch("src.api.workflows.bind_agent_context"),
        ):
            response = await start_workflow(request, user)

        assert response.status == WorkflowStatus.PENDING
        assert response.current_phase == "initialization"
        assert response.current_agent == "orchestration_controller"
        assert response.current_tier == AgentTier.TIER_0
        assert response.progress == 0.0
        assert response.budget_used_tokens == 0
        assert response.budget_used_cost == 0.0
        assert response.workflow_id in _WORKFLOWS

    @pytest.mark.asyncio
    async def test_start_workflow_with_different_priority(self):
        """Test workflow start with different priority levels."""
        _WORKFLOWS.clear()

        for priority in [1, 5, 10]:
            request = WorkflowStartRequest(
                user_request="Create a new feature for the system", priority=priority
            )
            user = {"sub": "user123", "roles": ["admin"]}

            with (
                patch("src.api.workflows.bind_workflow_context"),
                patch("src.api.workflows.bind_agent_context"),
            ):
                response = await start_workflow(request, user)

            assert response.status == WorkflowStatus.PENDING

    @pytest.mark.asyncio
    async def test_start_workflow_unexpected_error(self):
        """Test workflow start with unexpected error."""
        request = WorkflowStartRequest(
            user_request="Create a new feature for the system", priority=5
        )
        user = {"sub": "user123", "roles": ["admin"]}

        with (
            patch("src.api.workflows.bind_workflow_context"),
            patch("src.api.workflows.bind_agent_context"),
            patch("src.api.workflows.datetime") as mock_datetime,
        ):
            mock_datetime.now.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(HTTPException) as exc_info:
                await start_workflow(request, user)

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestGetWorkflowStatus:
    """Tests for workflow status endpoint."""

    @pytest.mark.asyncio
    async def test_get_workflow_status_success(self):
        """Test successful workflow status retrieval."""
        _WORKFLOWS.clear()
        workflow_id = uuid.uuid4()

        # Create a mock workflow record
        mock_status = MagicMock()
        mock_status.status = WorkflowStatus.IN_PROGRESS
        mock_status.progress = 50.0

        _WORKFLOWS[workflow_id] = _WorkflowRecord(status=mock_status)

        user = {"sub": "user123", "roles": ["admin"]}

        with (
            patch("src.api.workflows.bind_workflow_context"),
            patch("src.api.workflows.bind_agent_context"),
        ):
            response = await get_workflow_status(workflow_id, user)

        assert response == mock_status

    @pytest.mark.asyncio
    async def test_get_workflow_status_not_found(self):
        """Test workflow status retrieval for non-existent workflow."""
        _WORKFLOWS.clear()
        workflow_id = uuid.uuid4()
        user = {"sub": "user123", "roles": ["admin"]}

        with (
            patch("src.api.workflows.bind_workflow_context"),
            patch("src.api.workflows.bind_agent_context"),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_workflow_status(workflow_id, user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Workflow not found"


class TestApproveWorkflow:
    """Tests for workflow approval endpoint."""

    @pytest.mark.asyncio
    async def test_approve_workflow_success(self):
        """Test successful workflow approval."""
        _WORKFLOWS.clear()
        workflow_id = uuid.uuid4()

        # Create a mock workflow record
        mock_status = MagicMock()
        mock_status.status = WorkflowStatus.PENDING
        mock_status.model_copy = MagicMock(
            return_value=MagicMock(
                status=WorkflowStatus.IN_PROGRESS,
                current_phase="development",
                updated_at=datetime.now(tz=UTC),
                completed_at=None,
            )
        )

        _WORKFLOWS[workflow_id] = _WorkflowRecord(status=mock_status)

        request = ApprovalRequest(decision="approve", reason=None)
        user = {"sub": "user123", "roles": ["admin"]}

        with (
            patch("src.api.workflows.bind_workflow_context"),
            patch("src.api.workflows.bind_agent_context"),
        ):
            response = await approve_workflow(workflow_id, request, user)

        assert response.workflow_id == workflow_id
        assert response.decision == "approve"

    @pytest.mark.asyncio
    async def test_reject_workflow_without_reason(self):
        """Test workflow rejection without reason."""
        workflow_id = uuid.uuid4()
        request = ApprovalRequest(decision="reject", reason=None)
        user = {"sub": "user123", "roles": ["admin"]}

        with (
            patch("src.api.workflows.bind_workflow_context"),
            patch("src.api.workflows.bind_agent_context"),
            pytest.raises(HTTPException) as exc_info,
        ):
            await approve_workflow(workflow_id, request, user)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Reason is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_reject_workflow_with_reason(self):
        """Test successful workflow rejection with reason."""
        _WORKFLOWS.clear()
        workflow_id = uuid.uuid4()

        # Create a mock workflow record
        mock_status = MagicMock()
        mock_status.status = WorkflowStatus.PENDING
        mock_status.model_copy = MagicMock(
            return_value=MagicMock(
                status=WorkflowStatus.REJECTED,
                current_phase="failed",
                updated_at=datetime.now(tz=UTC),
                completed_at=datetime.now(tz=UTC),
            )
        )

        _WORKFLOWS[workflow_id] = _WorkflowRecord(status=mock_status)

        request = ApprovalRequest(decision="reject", reason="Invalid requirements")
        user = {"sub": "user123", "roles": ["admin"]}

        with (
            patch("src.api.workflows.bind_workflow_context"),
            patch("src.api.workflows.bind_agent_context"),
        ):
            response = await approve_workflow(workflow_id, request, user)

        assert response.workflow_id == workflow_id
        assert response.decision == "reject"
        assert response.reason == "Invalid requirements"

    @pytest.mark.asyncio
    async def test_approve_workflow_not_found(self):
        """Test approval of non-existent workflow."""
        _WORKFLOWS.clear()
        workflow_id = uuid.uuid4()
        request = ApprovalRequest(decision="approve", reason=None)
        user = {"sub": "user123", "roles": ["admin"]}

        with (
            patch("src.api.workflows.bind_workflow_context"),
            patch("src.api.workflows.bind_agent_context"),
            pytest.raises(HTTPException) as exc_info,
        ):
            await approve_workflow(workflow_id, request, user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestGetWorkflowBudget:
    """Tests for workflow budget endpoint."""

    @pytest.mark.asyncio
    async def test_get_workflow_budget_success(self):
        """Test successful budget retrieval."""
        _WORKFLOWS.clear()
        workflow_id = uuid.uuid4()

        # Create a mock workflow record
        mock_status = MagicMock()
        mock_status.budget_used_tokens = 1000
        mock_status.budget_used_cost = 10.0
        mock_status.budget_remaining_tokens = 9000
        mock_status.budget_remaining_cost = 90.0

        _WORKFLOWS[workflow_id] = _WorkflowRecord(status=mock_status)

        user = {"sub": "user123", "roles": ["admin"]}

        with (
            patch("src.api.workflows.bind_workflow_context"),
            patch("src.api.workflows.bind_agent_context"),
        ):
            response = await get_workflow_budget(workflow_id, user)

        assert response.workflow_id == workflow_id
        assert response.used_tokens == 1000
        assert response.used_cost_usd == 10.0
        assert response.remaining_tokens == 9000
        assert response.remaining_cost_usd == 90.0

    @pytest.mark.asyncio
    async def test_get_workflow_budget_not_found(self):
        """Test budget retrieval for non-existent workflow."""
        _WORKFLOWS.clear()
        workflow_id = uuid.uuid4()
        user = {"sub": "user123", "roles": ["admin"]}

        with (
            patch("src.api.workflows.bind_workflow_context"),
            patch("src.api.workflows.bind_agent_context"),
            pytest.raises(HTTPException) as exc_info,
        ):
            await get_workflow_budget(workflow_id, user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestWorkflowIntegration:
    """Integration tests for workflow endpoints."""

    @pytest.mark.asyncio
    async def test_workflow_lifecycle(self):
        """Test complete workflow lifecycle."""
        _WORKFLOWS.clear()

        # Start workflow
        start_request = WorkflowStartRequest(
            user_request="Create a new feature for the system", priority=5
        )
        user = {"sub": "user123", "roles": ["admin"]}

        with (
            patch("src.api.workflows.bind_workflow_context"),
            patch("src.api.workflows.bind_agent_context"),
        ):
            start_response = await start_workflow(start_request, user)

        workflow_id = start_response.workflow_id

        # Get status
        with (
            patch("src.api.workflows.bind_workflow_context"),
            patch("src.api.workflows.bind_agent_context"),
        ):
            status_response = await get_workflow_status(workflow_id, user)

        assert status_response.status == WorkflowStatus.PENDING

        # Approve workflow
        approve_request = ApprovalRequest(decision="approve", reason=None)

        with (
            patch("src.api.workflows.bind_workflow_context"),
            patch("src.api.workflows.bind_agent_context"),
        ):
            approve_response = await approve_workflow(
                workflow_id, approve_request, user
            )

        assert approve_response.decision == "approve"

    @pytest.mark.asyncio
    async def test_multiple_workflows(self):
        """Test handling multiple workflows."""
        _WORKFLOWS.clear()

        user = {"sub": "user123", "roles": ["admin"]}
        workflow_ids = []

        # Create multiple workflows
        for i in range(3):
            request = WorkflowStartRequest(
                user_request=f"Create feature number {i} for the system", priority=5
            )

            with (
                patch("src.api.workflows.bind_workflow_context"),
                patch("src.api.workflows.bind_agent_context"),
            ):
                response = await start_workflow(request, user)

            workflow_ids.append(response.workflow_id)

        # Verify all workflows exist
        assert len(_WORKFLOWS) == 3
        for wid in workflow_ids:
            assert wid in _WORKFLOWS
