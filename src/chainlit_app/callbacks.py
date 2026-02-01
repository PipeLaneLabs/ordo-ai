"""LangGraph Callback Integration for Chainlit.

Implements LangGraph callbacks to stream agent execution updates
to Chainlit UI in real-time. Provides visibility into agent outputs,
rejection routing decisions, and workflow state transitions.

Acceptance Criteria:
- UI-005: Stream agent execution updates to Chainlit
- UI-006: Display agent outputs (files, reports)
- UI-007: Show rejection routing decisions
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import chainlit as cl

from src.observability.logging import bind_workflow_context
from src.orchestration.state import WorkflowState


logger = logging.getLogger(__name__)


class ChainlitCallback:
    """LangGraph callback handler for Chainlit integration.

    Streams workflow state changes, agent outputs, and routing
    decisions to Chainlit UI via WebSocket.

    Attributes:
        workflow_id: Current workflow ID
        user_id: Current user ID
        message_queue: Queue of pending messages to send
    """

    def __init__(self, workflow_id: str, user_id: str) -> None:
        """Initialize Chainlit callback handler.

        Args:
            workflow_id: ID of workflow being executed
            user_id: ID of user running workflow
        """
        self.workflow_id = workflow_id
        self.user_id = user_id
        self.message_queue: list[str] = []

        bind_workflow_context(
            workflow_id=workflow_id,
            trace_id=workflow_id,
        )

        logger.info(
            "Chainlit callback initialized",
            extra={
                "workflow_id": workflow_id,
                "user_id": user_id,
            },
        )

    async def on_node_start(
        self,
        node_name: str,
        _state: WorkflowState,
    ) -> None:
        """Handle node execution start.

        Called when a LangGraph node begins execution.
        Sends status update to Chainlit UI.

        Args:
            node_name: Name of node being executed
            _state: Current workflow state
        """
        bind_workflow_context(
            workflow_id=self.workflow_id,
            trace_id=self.workflow_id,
        )

        logger.info(
            "Node execution started",
            extra={
                "node_name": node_name,
                "workflow_id": self.workflow_id,
            },
        )

        # Extract tier from node name
        tier_name = self._extract_tier_name(node_name)

        message = f"""
## Executing: {tier_name}

**Node:** {node_name}
**Workflow ID:** `{self.workflow_id}`
**Status:** In Progress...

Processing...
"""

        await cl.Message(content=message).send()  # type: ignore[no-untyped-call]

    async def on_node_end(
        self,
        node_name: str,
        _state: WorkflowState,
        output: dict[str, object],
    ) -> None:
        """Handle node execution completion.

        Called when a LangGraph node completes execution.
        Sends completion status and output to Chainlit UI.

        Args:
            node_name: Name of completed node
            _state: Current workflow state
            output: Output from node execution
        """
        logger.info(
            "Node execution completed",
            extra={
                "node_name": node_name,
                "workflow_id": self.workflow_id,
            },
        )

        tier_name = self._extract_tier_name(node_name)

        # Format output for display
        output_summary = self._format_output(output)

        message = f"""
**{tier_name}** completed

**Node:** {node_name}
**Status:** Complete
**Output:** {output_summary}
"""

        await cl.Message(content=message).send()  # type: ignore[no-untyped-call]

    async def on_rejection(
        self,
        node_name: str,
        reason: str,
        _state: WorkflowState,
    ) -> None:
        """Handle workflow rejection.

        Called when a validation node rejects workflow output.
        Sends rejection reason and routing decision to Chainlit UI.

        Args:
            node_name: Name of node that rejected
            reason: Reason for rejection
            _state: Current workflow state
        """
        logger.warning(
            "Workflow rejected",
            extra={
                "node_name": node_name,
                "reason": reason,
                "workflow_id": self.workflow_id,
            },
        )

        message = f"""
## Rejection Detected

**Rejected By:** {node_name}
**Reason:** {reason}
**Workflow ID:** `{self.workflow_id}`

**Routing Decision:** Returning to previous tier for remediation...

The workflow will be re-executed with corrections.
"""

        await cl.Message(content=message).send()  # type: ignore[no-untyped-call]

    async def on_approval(
        self,
        node_name: str,
        _state: WorkflowState,
    ) -> None:
        """Handle workflow approval.

        Called when a validation node approves workflow output.
        Sends approval confirmation to Chainlit UI.

        Args:
            node_name: Name of node that approved
            _state: Current workflow state
        """
        logger.info(
            "Workflow approved",
            extra={
                "node_name": node_name,
                "workflow_id": self.workflow_id,
            },
        )

        message = f"""
## Approval Granted

**Approved By:** {node_name}
**Workflow ID:** `{self.workflow_id}`

Proceeding to next tier...
"""

        await cl.Message(content=message).send()  # type: ignore[no-untyped-call]

    async def on_human_gate(
        self,
        gate_name: str,
        _state: WorkflowState,
        required_decision: str,
    ) -> None:
        """Handle human approval gate.

        Called when workflow reaches human approval gate.
        Prompts user for approval/rejection decision.

        Args:
            gate_name: Name of approval gate
            _state: Current workflow state
            required_decision: Description of decision needed
        """
        logger.info(
            "Human approval gate reached",
            extra={
                "gate_name": gate_name,
                "workflow_id": self.workflow_id,
            },
        )

        message = f"""
## Human Approval Required

**Gate:** {gate_name}
**Workflow ID:** `{self.workflow_id}`

**Decision Needed:**
{required_decision}

Please respond with "approve" or "reject" to proceed.
"""

        await cl.Message(content=message).send()  # type: ignore[no-untyped-call]

    async def on_budget_warning(
        self,
        current_cost: float,
        budget_limit: float,
        percentage: float,
    ) -> None:
        """Handle budget warning threshold.

        Called when workflow cost reaches 75% of budget.
        Sends warning to Chainlit UI.

        Args:
            current_cost: Current workflow cost
            budget_limit: Total budget limit
            percentage: Percentage of budget used
        """
        logger.warning(
            "Budget warning threshold reached",
            extra={
                "current_cost": current_cost,
                "budget_limit": budget_limit,
                "percentage": percentage,
                "workflow_id": self.workflow_id,
            },
        )

        message = f"""
## Budget Warning

**Current Cost:** ${current_cost:.2f}
**Budget Limit:** ${budget_limit:.2f}
**Usage:** {percentage:.1f}%

You are approaching your budget limit. Consider reviewing
workflow progress or adjusting budget settings.
"""

        await cl.Message(content=message).send()  # type: ignore[no-untyped-call]

    async def on_budget_exceeded(
        self,
        current_cost: float,
        budget_limit: float,
    ) -> None:
        """Handle budget exceeded.

        Called when workflow cost exceeds budget limit.
        Sends critical alert and halts workflow.

        Args:
            current_cost: Current workflow cost
            budget_limit: Total budget limit
        """
        logger.error(
            "Budget limit exceeded",
            extra={
                "current_cost": current_cost,
                "budget_limit": budget_limit,
                "workflow_id": self.workflow_id,
            },
        )

        message = f"""
## Budget Limit Exceeded

**Current Cost:** ${current_cost:.2f}
**Budget Limit:** ${budget_limit:.2f}

Workflow has been halted due to budget constraints.
Please increase your budget limit or contact support.
"""

        await cl.Message(content=message).send()  # type: ignore[no-untyped-call]

    async def on_error(
        self,
        error_type: str,
        error_message: str,
        node_name: str | None = None,
    ) -> None:
        """Handle workflow error.

        Called when an error occurs during workflow execution.
        Sends error details to Chainlit UI.

        Args:
            error_type: Type of error that occurred
            error_message: Error message
            node_name: Name of node where error occurred (optional)
        """
        logger.error(
            "Workflow error",
            extra={
                "error_type": error_type,
                "error_message": error_message,
                "node_name": node_name,
                "workflow_id": self.workflow_id,
            },
        )

        node_info = f"\n**Node:** {node_name}" if node_name else ""

        message = f"""
## Error Occurred

**Error Type:** {error_type}
**Message:** {error_message}{node_info}
**Workflow ID:** `{self.workflow_id}`

Workflow execution has been halted. Please review the error
and try again, or contact support for assistance.
"""

        await cl.Message(content=message).send()  # type: ignore[no-untyped-call]

    def _extract_tier_name(self, node_name: str) -> str:
        """Extract human-readable tier name from node name.

        Args:
            node_name: Internal node name

        Returns:
            Human-readable tier name
        """
        tier_map = {
            "tier_0": "Tier 0 - Control & Governance",
            "tier_1": "Tier 1 - Planning & Strategy",
            "tier_2": "Tier 2 - Preparation",
            "tier_3": "Tier 3 - Development",
            "tier_4": "Tier 4 - Validation & Security",
            "tier_5": "Tier 5 - Integration & Delivery",
        }

        for key, value in tier_map.items():
            if key in node_name.lower():
                return value

        return node_name

    def _format_output(self, output: dict[str, object]) -> str:
        """Format node output for display in Chainlit.

        Args:
            output: Output from node execution

        Returns:
            Formatted output string
        """
        if isinstance(output, dict):
            # Extract key information from output dict
            if "files_created" in output:
                files = output["files_created"]
                if isinstance(files, list):
                    return f"{len(files)} files created"
                return "Files created"
            elif "report" in output:
                return "Report generated"
            elif "status" in output:
                status = output["status"]
                if isinstance(status, str):
                    return status
                return "Completed"
            else:
                return "Completed"
        elif isinstance(output, str):
            return output[:100]
        else:
            return "Completed"


def create_chainlit_callbacks(
    workflow_id: str,
    user_id: str,
) -> dict[str, Callable[[Any], Any]]:
    """Create LangGraph callback handlers for Chainlit.

    Factory function to create callback handlers that integrate
    LangGraph execution with Chainlit UI.

    Args:
        workflow_id: ID of workflow being executed
        user_id: ID of user running workflow

    Returns:
        Dictionary of callback handlers for LangGraph
    """
    callback = ChainlitCallback(workflow_id, user_id)

    return {
        "on_node_start": callback.on_node_start,  # type: ignore[dict-item]
        "on_node_end": callback.on_node_end,  # type: ignore[dict-item]
        "on_rejection": callback.on_rejection,  # type: ignore[dict-item]
        "on_approval": callback.on_approval,  # type: ignore[dict-item]
        "on_human_gate": callback.on_human_gate,  # type: ignore[dict-item]
        "on_budget_warning": callback.on_budget_warning,  # type: ignore[dict-item]
        "on_budget_exceeded": callback.on_budget_exceeded,  # type: ignore[dict-item]
        "on_error": callback.on_error,  # type: ignore[dict-item]
    }
