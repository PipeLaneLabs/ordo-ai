"""
LangGraph Workflow State Schema

Single source of truth for workflow state managed by LangGraph.
All agents read from and write to this shared state schema.
"""

from datetime import UTC, datetime
from typing import Any, Literal, NotRequired, TypedDict


class WorkflowState(TypedDict):
    """
    Complete workflow state schema.

    This TypedDict is the single source of truth for workflow execution state.
    Managed by LangGraph and persisted in PostgreSQL checkpoints.

    All agents interact with this state:
    - Read: Current requirements, architecture, code, etc.
    - Write: Generated artifacts, updated metrics, routing decisions

    State updates are atomic and versioned to prevent race conditions.
    """

    # ========== Workflow Identity ==========
    workflow_id: str  # Unique workflow identifier (e.g., "wf_20260122_001")
    user_request: str  # Original user request text
    trace_id: str  # Distributed tracing ID

    # ========== Execution State ==========
    current_phase: Literal[
        "planning",  # Tier 1: Requirements → Architecture
        "preparation",  # Tier 2: Tasks → Dependencies → Infrastructure
        "development",  # Tier 3: Code → Tests
        "validation",  # Tier 4: Security → Product validation
        "delivery",  # Tier 5: Documentation → Deployment
        "completed",  # Workflow finished successfully
        "failed",  # Workflow failed (unrecoverable error)
        "paused",  # Awaiting human approval
    ]
    current_task: str  # Current task being executed (e.g., "TASK-011")
    current_agent: str  # Agent currently executing (e.g., "software_engineer")
    rejection_count: int  # Number of times any agent has been rejected
    state_version: int  # Optimistic locking version (incremented on each update)

    # ========== Artifacts (Validated Files) ==========
    requirements: str  # REQUIREMENTS.md content
    architecture: str  # ARCHITECTURE.md content
    tasks: str  # TASKS.md content
    dependencies: str  # DEPENDENCIES.md content
    infrastructure: str  # INFRASTRUCTURE.md content
    observability: str  # OBSERVABILITY.md content

    # Code files (validated by Quality Engineer)
    code_files: dict[str, str]  # {"src/main.py": "content", ...}
    test_files: dict[str, str]  # {"tests/test_main.py": "content", ...}

    # ========== Partial Artifacts (In-Progress Work) ==========
    # Work that hasn't passed validation yet
    # Agents should resume from here on rejection (not regenerate from scratch)
    partial_artifacts: dict[str, dict[str, str]]  # {task_id: {file_path: content}}

    # ========== Reports ==========
    validation_report: str  # Strategy Validator report (VALIDATION_REPORT.md)
    deviation_log: str  # Deviation Handler log (DEVIATION_LOG.md)
    compliance_log: str  # Static Analysis report (COMPLIANCE_LOG.md)
    quality_report: str  # Quality Engineer report (QUALITY_REPORT.md)
    security_report: str  # Security Validator report (SECURITY_REPORT.md)
    acceptance_report: str  # Product Validator report (ACCEPTANCE_REPORT.md)

    # ========== Budget Tracking ==========
    budget_used_tokens: int  # Total tokens consumed so far
    budget_used_usd: float  # Total cost in USD
    budget_remaining_tokens: int  # Remaining token budget
    budget_remaining_usd: float  # Remaining cost budget

    # Per-agent token usage (for cost breakdown visualization)
    agent_token_usage: dict[str, int]  # {agent_name: tokens_consumed}

    # ========== Quality Gates ==========
    quality_gates_passed: list[str]  # ["tier_1_planning", "tier_2_preparation", ...]
    blocking_issues: list[str]  # Critical issues preventing progression

    # ========== Human Approval ==========
    awaiting_human_approval: bool  # Is workflow paused for human approval?
    approval_gate: str  # Name of approval gate (e.g., "tier_3_development")
    approval_timeout: str  # ISO 8601 timestamp when approval times out

    # ========== Routing & Deviation Handling ==========
    routing_decision: dict[str, str]  # {target_agent, reason, iteration_count}
    escalation_flag: bool  # Has workflow been escalated to human?

    # ========== Checkpoint Management ==========
    checkpoint_id: NotRequired[str]  # Current checkpoint ID (optional)
    previous_checkpoint_id: NotRequired[str]  # Previous checkpoint (for rollback)

    # ========== Additional State (Dynamic) ==========
    tool_results: NotRequired[dict[str, dict[str, Any]]]  # Static analysis tool results
    deviations: NotRequired[list[dict[str, Any]]]  # Deviation entries
    last_error: NotRequired[str]  # Last error message
    retry_count: NotRequired[int]  # Retry attempt counter
    last_retry_timestamp: NotRequired[str]  # Last retry timestamp
    rollback_performed: NotRequired[bool]  # Whether rollback was performed
    rollback_timestamp: NotRequired[str]  # Rollback timestamp
    requires_human_approval: NotRequired[bool]  # Requires human approval (escalation)
    approval_reason: NotRequired[str]  # Reason for approval requirement
    escalation_details: NotRequired[dict[str, Any]]  # Escalation details
    escalation_timestamp: NotRequired[str]  # Escalation timestamp

    # ========== Timestamps ==========
    created_at: str  # ISO 8601 workflow creation time
    updated_at: str  # ISO 8601 last update time
    completed_at: NotRequired[str]  # ISO 8601 completion time (if completed)


def create_initial_state(
    workflow_id: str,
    user_request: str,
    trace_id: str,
) -> WorkflowState:
    """
    Create initial workflow state.

    Args:
        workflow_id: Unique workflow identifier
        user_request: Original user request text
        trace_id: Distributed tracing ID

    Returns:
        WorkflowState: Initial state for new workflow
    """
    now = datetime.now(UTC).isoformat()

    return {
        # Workflow Identity
        "workflow_id": workflow_id,
        "user_request": user_request,
        "trace_id": trace_id,
        # Execution State
        "current_phase": "planning",
        "current_task": "",
        "current_agent": "",
        "rejection_count": 0,
        "state_version": 0,
        # Artifacts (Empty at start)
        "requirements": "",
        "architecture": "",
        "tasks": "",
        "dependencies": "",
        "infrastructure": "",
        "observability": "",
        "code_files": {},
        "test_files": {},
        # Partial Artifacts
        "partial_artifacts": {},
        # Reports (Empty at start)
        "validation_report": "",
        "deviation_log": "",
        "compliance_log": "",
        "quality_report": "",
        "security_report": "",
        "acceptance_report": "",
        # Budget Tracking
        "budget_used_tokens": 0,
        "budget_used_usd": 0.0,
        "budget_remaining_tokens": 500000,  # Default: 500K tokens
        "budget_remaining_usd": 20.0,  # Default: $20
        "agent_token_usage": {},
        # Quality Gates
        "quality_gates_passed": [],
        "blocking_issues": [],
        # Human Approval
        "awaiting_human_approval": False,
        "approval_gate": "",
        "approval_timeout": "",
        # Routing
        "routing_decision": {},
        "escalation_flag": False,
        # Timestamps
        "created_at": now,
        "updated_at": now,
    }


def increment_rejection_count(state: WorkflowState) -> WorkflowState:
    """
    Atomic increment of rejection count.

    This is a LangGraph reducer function for safely incrementing rejection count.

    Args:
        state: Current workflow state

    Returns:
        WorkflowState: Updated state with incremented rejection count
    """
    return {
        **state,
        "rejection_count": state["rejection_count"] + 1,
        "state_version": state["state_version"] + 1,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def update_budget(
    state: WorkflowState,
    tokens_consumed: int,
    cost_usd: float,
    agent_name: str,
) -> WorkflowState:
    """
    Update budget tracking.

    Args:
        state: Current workflow state
        tokens_consumed: Tokens consumed by this operation
        cost_usd: Cost in USD
        agent_name: Name of agent that consumed tokens

    Returns:
        WorkflowState: Updated state with budget tracking
    """
    # Update per-agent token usage
    agent_token_usage = state["agent_token_usage"].copy()
    agent_token_usage[agent_name] = (
        agent_token_usage.get(agent_name, 0) + tokens_consumed
    )

    return {
        **state,
        "budget_used_tokens": state["budget_used_tokens"] + tokens_consumed,
        "budget_used_usd": state["budget_used_usd"] + cost_usd,
        "budget_remaining_tokens": state["budget_remaining_tokens"] - tokens_consumed,
        "budget_remaining_usd": state["budget_remaining_usd"] - cost_usd,
        "agent_token_usage": agent_token_usage,
        "state_version": state["state_version"] + 1,
        "updated_at": datetime.now(UTC).isoformat(),
    }
