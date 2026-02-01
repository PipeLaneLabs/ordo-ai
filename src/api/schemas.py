"""
API Schemas

Pydantic models for API requests and responses.
Defines data validation and serialization for all API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Possible workflow statuses."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVAL_NEEDED = "approval_needed"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AgentTier(int, Enum):
    """Agent tiers in the workflow."""

    TIER_0 = 0  # Control & Governance
    TIER_1 = 1  # Planning & Strategy
    TIER_2 = 2  # Preparation
    TIER_3 = 3  # Development
    TIER_4 = 4  # Validation & Security
    TIER_5 = 5  # Integration & Delivery


class WorkflowStartRequest(BaseModel):
    """
    Request schema for starting a new workflow.
    """

    user_request: str = Field(
        ...,
        description="User's natural language request for the workflow",
        min_length=10,
        max_length=1000,
    )
    priority: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Workflow priority (1-10, higher is more urgent)",
    )
    tags: list[str] = Field(
        default_factory=list, description="Optional tags for categorizing the workflow"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata for the workflow"
    )


class WorkflowStatusResponse(BaseModel):
    """
    Response schema for workflow status.
    """

    workflow_id: UUID = Field(..., description="Unique identifier for the workflow")
    status: WorkflowStatus = Field(..., description="Current status of the workflow")
    current_phase: str = Field(..., description="Current phase of the workflow")
    current_agent: str = Field(..., description="Currently executing agent")
    current_tier: AgentTier = Field(..., description="Current tier of the workflow")
    progress: float = Field(
        ..., ge=0.0, le=100.0, description="Workflow progress percentage"
    )
    created_at: datetime = Field(..., description="Timestamp when workflow was created")
    updated_at: datetime = Field(
        ..., description="Timestamp when workflow was last updated"
    )
    completed_at: datetime | None = Field(
        None, description="Timestamp when workflow was completed"
    )
    budget_used_tokens: int = Field(
        ..., ge=0, description="Number of tokens used by the workflow"
    )
    budget_used_cost: float = Field(
        ..., ge=0.0, description="Cost in USD used by the workflow"
    )
    budget_remaining_tokens: int = Field(
        ..., ge=0, description="Remaining token budget"
    )
    budget_remaining_cost: float = Field(
        ..., ge=0.0, description="Remaining cost budget in USD"
    )


class ApprovalRequest(BaseModel):
    """
    Request schema for approving or rejecting a workflow step.
    """

    decision: str = Field(
        ...,
        description="Approval decision ('approve' or 'reject')",
        pattern="^(approve|reject)$",
    )
    reason: str | None = Field(
        None,
        description="Reason for the decision (required for rejection)",
        max_length=500,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata for the approval"
    )


class ApprovalResponse(BaseModel):
    """
    Response schema for approval actions.
    """

    workflow_id: UUID = Field(..., description="Unique identifier for the workflow")
    decision: str = Field(..., description="Approval decision that was recorded")
    reason: str | None = Field(None, description="Reason for the decision")
    next_step: str = Field(..., description="Description of the next workflow step")
    status: WorkflowStatus = Field(..., description="Updated workflow status")


class BudgetSummaryResponse(BaseModel):
    """
    Response schema for budget summary.
    """

    workflow_id: UUID = Field(..., description="Unique identifier for the workflow")
    total_tokens: int = Field(
        ..., ge=0, description="Total token budget for the workflow"
    )
    used_tokens: int = Field(..., ge=0, description="Tokens used by the workflow")
    remaining_tokens: int = Field(..., ge=0, description="Remaining token budget")
    token_usage_percent: float = Field(
        ..., ge=0.0, le=100.0, description="Percentage of token budget used"
    )
    total_cost_usd: float = Field(..., ge=0.0, description="Total cost budget in USD")
    used_cost_usd: float = Field(
        ..., ge=0.0, description="Cost in USD used by the workflow"
    )
    remaining_cost_usd: float = Field(
        ..., ge=0.0, description="Remaining cost budget in USD"
    )
    cost_usage_percent: float = Field(
        ..., ge=0.0, le=100.0, description="Percentage of cost budget used"
    )


class HealthStatus(str, Enum):
    """Health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheckResponse(BaseModel):
    """
    Response schema for health check endpoints.
    """

    status: HealthStatus = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Timestamp of the health check")
    services: dict[str, HealthStatus] = Field(
        ..., description="Health status of individual services"
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional health check details"
    )


class ReadinessCheckResponse(BaseModel):
    """
    Response schema for readiness check endpoints.
    """

    status: HealthStatus = Field(..., description="Overall readiness status")
    timestamp: datetime = Field(..., description="Timestamp of the readiness check")
    dependencies: dict[str, HealthStatus] = Field(
        ..., description="Readiness status of dependencies"
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional readiness check details"
    )
