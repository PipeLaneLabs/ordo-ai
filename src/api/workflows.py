"""
Workflow Control Endpoints

FastAPI endpoints for workflow control operations.
Includes starting workflows, checking status, and handling approvals.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer


try:
    from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
except ImportError:
    from jwt import ExpiredSignatureError, InvalidTokenError


from pydantic import BaseModel

from src.api.schemas import (
    AgentTier,
    ApprovalRequest,
    ApprovalResponse,
    BudgetSummaryResponse,
    WorkflowStartRequest,
    WorkflowStatus,
    WorkflowStatusResponse,
)
from src.auth.jwt_handler import jwt_service
from src.auth.rbac import check_permission
from src.config import settings
from src.exceptions import WorkflowError
from src.observability.logging import bind_agent_context, bind_workflow_context


# Get logger for this module
logger = logging.getLogger(__name__)

# Create router for workflow endpoints
router = APIRouter(prefix="/workflow", tags=["workflows"])

# Define OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@dataclass
class _WorkflowRecord:
    status: WorkflowStatusResponse


_WORKFLOWS: dict[UUID, _WorkflowRecord] = {}


class TokenData(BaseModel):
    """Data structure for JWT claims."""

    sub: str
    roles: list[str]


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """
    Extract user from JWT token.

    Args:
        token: JWT token from Authorization header

    Returns:
        Dictionary containing user claims

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt_service.verify_token(token)
        return payload
    except ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        ) from e
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from e


async def _check_permission_dependency(
    permission: str, user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Check workflow permission for authenticated user.

    Args:
        permission: Required permission to check
        user: Authenticated user data

    Returns:
        User data if permission is granted

    Raises:
        HTTPException: If permission is denied
    """
    user_roles = user.get("roles", [])
    if not check_permission(user_roles, permission):
        logger.warning(
            "Access denied",
            extra={
                "user_id": user.get("sub"),
                "required_permission": permission,
                "user_roles": user_roles,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {permission}",
        )
    return user


@router.post("/start", response_model=WorkflowStatusResponse)
async def start_workflow(
    request: WorkflowStartRequest,
    user: dict[str, Any] = Depends(
        lambda: _check_permission_dependency("workflow:start")
    ),
) -> WorkflowStatusResponse:
    """
    Start a new workflow.

    Requires 'workflow:start' permission.

    Args:
        request: Workflow start request with user requirements
        user: Authenticated user data

    Returns:
        Workflow status response with workflow ID

    Raises:
        HTTPException: If workflow cannot be started
    """
    # Bind context for observability
    workflow_id = uuid.uuid4()
    bind_workflow_context(str(workflow_id), "workflow_start")
    bind_agent_context("api", 0)

    logger.info(
        "Starting new workflow",
        extra={
            "user_id": user.get("sub"),
            "workflow_id": str(workflow_id),
            "request_length": len(request.user_request),
            "priority": request.priority,
        },
    )

    try:
        now = datetime.now(tz=UTC)
        response = WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus.PENDING,
            current_phase="initialization",
            current_agent="orchestration_controller",
            current_tier=AgentTier.TIER_0,
            progress=0.0,
            created_at=now,
            updated_at=now,
            completed_at=None,
            budget_used_tokens=0,
            budget_used_cost=0.0,
            budget_remaining_tokens=settings.max_tokens_per_workflow,
            budget_remaining_cost=settings.max_monthly_budget_usd,
        )

        _WORKFLOWS[workflow_id] = _WorkflowRecord(status=response)

        logger.info(
            "Workflow started successfully",
            extra={"workflow_id": str(workflow_id), "user_id": user.get("sub")},
        )

        return response

    except WorkflowError as e:
        logger.error(
            "Failed to start workflow",
            extra={
                "user_id": user.get("sub"),
                "workflow_id": str(workflow_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to start workflow: {e!s}",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error starting workflow",
            extra={
                "user_id": user.get("sub"),
                "workflow_id": str(workflow_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: UUID,
    user: dict[str, Any] = Depends(
        lambda: _check_permission_dependency("workflow:view")
    ),
) -> WorkflowStatusResponse:
    """
    Get workflow status.

    Requires 'workflow:view' permission.

    Args:
        workflow_id: ID of the workflow to check
        user: Authenticated user data

    Returns:
        Workflow status response

    Raises:
        HTTPException: If workflow not found or access denied
    """
    # Bind context for observability
    bind_workflow_context(str(workflow_id), "workflow_status")
    bind_agent_context("api", 0)

    logger.info(
        "Fetching workflow status",
        extra={"user_id": user.get("sub"), "workflow_id": str(workflow_id)},
    )

    try:
        record = _WORKFLOWS.get(workflow_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )

        response = record.status

        logger.debug(
            "Workflow status retrieved",
            extra={
                "workflow_id": str(workflow_id),
                "status": response.status,
                "progress": response.progress,
            },
        )

        return response

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "Failed to fetch workflow status",
            extra={
                "user_id": user.get("sub"),
                "workflow_id": str(workflow_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch workflow status",
        ) from e


@router.post("/{workflow_id}/approve", response_model=ApprovalResponse)
async def approve_workflow(
    workflow_id: UUID,
    request: ApprovalRequest,
    user: dict[str, Any] = Depends(
        lambda: _check_permission_dependency("workflow:approve")
    ),
) -> ApprovalResponse:
    """
    Approve or reject a workflow step.

    Requires 'workflow:approve' permission.

    Args:
        workflow_id: ID of the workflow to approve/reject
        request: Approval request with decision and reason
        user: Authenticated user data

    Returns:
        Approval response with next steps

    Raises:
        HTTPException: If approval fails or access denied
    """
    # Bind context for observability
    bind_workflow_context(str(workflow_id), "workflow_approval")
    bind_agent_context("api", 0)

    logger.info(
        "Processing workflow approval",
        extra={
            "user_id": user.get("sub"),
            "workflow_id": str(workflow_id),
            "decision": request.decision,
        },
    )

    if request.decision == "reject" and not request.reason:
        logger.warning(
            "Rejection without reason",
            extra={"user_id": user.get("sub"), "workflow_id": str(workflow_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reason is required for rejection",
        )

    try:
        record = _WORKFLOWS.get(workflow_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )

        updated = record.status.model_copy(deep=True)
        updated.updated_at = datetime.now(tz=UTC)

        if request.decision == "approve":
            updated.status = WorkflowStatus.IN_PROGRESS
            updated.current_phase = "development"
            next_step = "Proceeding to next workflow phase"
        else:
            updated.status = WorkflowStatus.REJECTED
            updated.current_phase = "failed"
            updated.completed_at = datetime.now(tz=UTC)
            next_step = "Workflow rejected and terminated"

        record.status = updated

        response = ApprovalResponse(
            workflow_id=workflow_id,
            decision=request.decision,
            reason=request.reason,
            next_step=next_step,
            status=updated.status,
        )

        logger.info(
            "Workflow approval processed",
            extra={
                "workflow_id": str(workflow_id),
                "user_id": user.get("sub"),
                "decision": request.decision,
            },
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to process workflow approval",
            extra={
                "user_id": user.get("sub"),
                "workflow_id": str(workflow_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process approval",
        ) from e


@router.get("/{workflow_id}/budget", response_model=BudgetSummaryResponse)
async def get_workflow_budget(
    workflow_id: UUID,
    user: dict[str, Any] = Depends(
        lambda: _check_permission_dependency("workflow:view")
    ),
) -> BudgetSummaryResponse:
    """
    Get workflow budget summary.

    Requires 'workflow:view' permission.

    Args:
        workflow_id: ID of the workflow to check budget for
        user: Authenticated user data

    Returns:
        Budget summary response

    Raises:
        HTTPException: If budget data not found or access denied
    """
    # Bind context for observability
    bind_workflow_context(str(workflow_id), "workflow_budget")
    bind_agent_context("api", 0)

    logger.info(
        "Fetching workflow budget",
        extra={"user_id": user.get("sub"), "workflow_id": str(workflow_id)},
    )

    try:
        record = _WORKFLOWS.get(workflow_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )

        used_tokens = record.status.budget_used_tokens
        used_cost = record.status.budget_used_cost
        remaining_tokens = record.status.budget_remaining_tokens
        remaining_cost = record.status.budget_remaining_cost

        response = BudgetSummaryResponse(
            workflow_id=workflow_id,
            total_tokens=settings.max_tokens_per_workflow,
            used_tokens=used_tokens,
            remaining_tokens=remaining_tokens,
            token_usage_percent=(used_tokens / settings.max_tokens_per_workflow) * 100,
            total_cost_usd=settings.max_monthly_budget_usd,
            used_cost_usd=used_cost,
            remaining_cost_usd=remaining_cost,
            cost_usage_percent=(used_cost / settings.max_monthly_budget_usd) * 100,
        )

        logger.debug(
            "Workflow budget retrieved",
            extra={
                "workflow_id": str(workflow_id),
                "used_tokens": response.used_tokens,
                "used_cost": response.used_cost_usd,
            },
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch workflow budget",
            extra={
                "user_id": user.get("sub"),
                "workflow_id": str(workflow_id),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch budget information",
        ) from e
