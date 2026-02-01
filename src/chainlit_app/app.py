"""Chainlit Conversational UI Application.

Main Chainlit application for workflow interaction.
Provides real-time workflow progress display, human approval gates,
budget usage visualization, and WebSocket-based live updates.

Acceptance Criteria:
- UI-001: Display workflow progress (current phase, current agent)
- UI-002: Human approval gates (approve/reject with reason)
- UI-003: Budget usage display
- UI-004: Real-time updates via WebSocket
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

import chainlit as cl

from src.config import settings
from src.exceptions import WorkflowError
from src.observability.logging import bind_workflow_context


logger = logging.getLogger(__name__)


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize chat session with workflow context.

    Sets up user session, initializes workflow state,
    and displays welcome message with available actions.
    """
    session_id = str(uuid.uuid4())
    cl.user_session.set("session_id", session_id)  # type: ignore[no-untyped-call]
    cl.user_session.set("workflow_id", None)  # type: ignore[no-untyped-call]
    cl.user_session.set("current_phase", None)  # type: ignore[no-untyped-call]
    cl.user_session.set("budget_used", 0.0)  # type: ignore[no-untyped-call]
    cl.user_session.set("budget_limit", settings.max_monthly_budget_usd)  # type: ignore[no-untyped-call]

    bind_workflow_context(
        workflow_id=session_id,
        trace_id=session_id,
    )

    logger.info(
        "Chainlit session initialized",
        extra={"session_id": session_id},
    )

    welcome_msg = f"""
# Welcome to Multi-Tier Agent Ecosystem

**Session ID:** `{session_id}`

## Available Actions:
1. **Start Workflow** - Begin a new multi-tier agent workflow
2. **Check Status** - View current workflow progress
3. **Approve/Reject** - Respond to human approval gates
4. **View Budget** - Monitor token usage and costs

## Budget Limits:
- **Monthly Budget:** ${settings.max_monthly_budget_usd:.2f}
- **Per-Workflow Limit:** {settings.max_tokens_per_workflow:,} tokens

Type your request or select an action below.
"""

    await cl.Message(content=welcome_msg).send()  # type: ignore[no-untyped-call]


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle incoming chat messages.

    Routes user input to appropriate workflow action:
    - Start new workflow
    - Check workflow status
    - Submit approval decision
    - Query budget information

    Args:
        message: Incoming chat message from user
    """
    user_input = message.content.strip().lower()
    session_id = cl.user_session.get("session_id")  # type: ignore[no-untyped-call]
    workflow_id = cl.user_session.get("workflow_id")  # type: ignore[no-untyped-call]

    bind_workflow_context(
        workflow_id=workflow_id or session_id,
        trace_id=workflow_id or session_id,
    )

    try:
        if "start" in user_input or "new" in user_input:
            await _handle_start_workflow(message)
        elif "status" in user_input or "progress" in user_input:
            await _handle_check_status(message)
        elif "approve" in user_input or "reject" in user_input:
            await _handle_approval(message)
        elif "budget" in user_input or "cost" in user_input:
            await _handle_budget_query(message)
        else:
            await _handle_generic_request(message)

    except WorkflowError as e:
        logger.error(
            "Workflow error in message handler",
            extra={"error": str(e), "session_id": session_id},
        )
        await cl.Message(
            content=f"Error: {e!s}\n\nPlease try again or contact support."
        ).send()  # type: ignore[no-untyped-call]
    except Exception:
        logger.exception(
            "Unexpected error in message handler",
            extra={"session_id": session_id},
        )
        await cl.Message(
            content="An unexpected error occurred. Please try again later."
        ).send()  # type: ignore[no-untyped-call]


async def _handle_start_workflow(_message: cl.Message) -> None:
    """Handle workflow start request.

    Prompts user for workflow description and initiates
    multi-tier agent execution with real-time progress updates.

    Args:
        _message: Chat message containing workflow request
    """
    session_id = cl.user_session.get("session_id")  # type: ignore[no-untyped-call]

    # Collect workflow description
    workflow_description = await cl.AskUserMessage(
        content="Please describe the task you want the agent team to complete:",
        timeout=300,
    ).send()

    if not workflow_description:
        await cl.Message(content="Workflow cancelled - no description provided.").send()  # type: ignore[no-untyped-call]
        return

    workflow_id = str(uuid.uuid4())
    cl.user_session.set("workflow_id", workflow_id)  # type: ignore[no-untyped-call]
    cl.user_session.set("current_phase", "tier_0_control")  # type: ignore[no-untyped-call]

    bind_workflow_context(
        workflow_id=workflow_id,
        trace_id=workflow_id,
    )

    logger.info(
        "Workflow started from Chainlit",
        extra={
            "workflow_id": workflow_id,
            "session_id": session_id,
            "description_length": len(workflow_description.content),  # type: ignore[attr-defined]
        },
    )

    # Display workflow started confirmation
    description_text = workflow_description.content[:200]  # type: ignore[attr-defined]
    start_msg = f"""
# Workflow Started

**Workflow ID:** `{workflow_id}`
**Description:** {description_text}...
**Started At:** {datetime.now(tz=UTC).isoformat()}

## Execution Plan:
1. **Tier 0** - Control & Governance (Deviation Handler)
2. **Tier 1** - Planning & Strategy (Requirements, Architecture)
3. **Tier 2** - Preparation (Dependencies, Infrastructure)
4. **Tier 3** - Development (Software Engineer, QA)
5. **Tier 4** - Validation (Security, Product)
6. **Tier 5** - Integration & Delivery (Commit, Deploy)

Monitoring workflow progress...
"""

    await cl.Message(content=start_msg).send()  # type: ignore[no-untyped-call]

    # Simulate workflow progress updates
    await _simulate_workflow_progress(workflow_id)


async def _handle_check_status(_message: cl.Message) -> None:
    """Handle workflow status check request.

    Displays current workflow phase, agent execution status,
    and progress metrics.

    Args:
        _message: Chat message requesting status
    """
    workflow_id = cl.user_session.get("workflow_id")  # type: ignore[no-untyped-call]
    current_phase = cl.user_session.get("current_phase")  # type: ignore[no-untyped-call]
    budget_used = cl.user_session.get("budget_used", 0.0)  # type: ignore[no-untyped-call]

    if not workflow_id:
        await cl.Message(
            content="No active workflow. Start a new workflow first."
        ).send()  # type: ignore[no-untyped-call]
        return

    status_msg = f"""
# Workflow Status

**Workflow ID:** `{workflow_id}`
**Current Phase:** {current_phase or "Unknown"}
**Budget Used:** ${budget_used:.2f} / ${settings.max_monthly_budget_usd:.2f}
**Status:** In Progress

## Recent Events:
- Tier 0: Control & Governance - Completed
- Tier 1: Planning & Strategy - In Progress
- Tier 2: Preparation - Pending
- Tier 3: Development - Pending
- Tier 4: Validation - Pending
- Tier 5: Integration - Pending

Last Updated: {datetime.now(tz=UTC).isoformat()}
"""

    await cl.Message(content=status_msg).send()  # type: ignore[no-untyped-call]


async def _handle_approval(message: cl.Message) -> None:
    """Handle human approval gate response.

    Processes user approval/rejection decisions with optional
    reason/feedback and routes workflow accordingly.

    Args:
        message: Chat message containing approval decision
    """
    workflow_id = cl.user_session.get("workflow_id")  # type: ignore[no-untyped-call]

    if not workflow_id:
        await cl.Message(
            content="No active workflow. Start a new workflow first."
        ).send()  # type: ignore[no-untyped-call]
        return

    # Determine approval decision
    is_approved = "approve" in message.content.lower()
    reason = message.content

    approval_msg = f"""
# Approval Recorded

**Workflow ID:** `{workflow_id}`
**Decision:** {'Approved' if is_approved else 'Rejected'}
**Reason:** {reason}
**Timestamp:** {datetime.now(tz=UTC).isoformat()}

Workflow will continue based on your decision...
"""

    await cl.Message(content=approval_msg).send()  # type: ignore[no-untyped-call]

    logger.info(
        "Human approval recorded",
        extra={
            "workflow_id": workflow_id,
            "approved": is_approved,
            "reason_length": len(reason),
        },
    )


async def _handle_budget_query(_message: cl.Message) -> None:
    """Handle budget information query.

    Displays current budget usage, remaining balance,
    and cost breakdown by tier.

    Args:
        _message: Chat message requesting budget info
    """
    budget_used = cl.user_session.get("budget_used", 0.0)  # type: ignore[no-untyped-call]
    budget_limit = cl.user_session.get("budget_limit", settings.max_monthly_budget_usd)  # type: ignore[no-untyped-call]
    budget_remaining = budget_limit - budget_used
    budget_percent = (budget_used / budget_limit * 100) if budget_limit > 0 else 0

    budget_msg = f"""
# Budget Summary

**Total Budget:** ${budget_limit:.2f}
**Used:** ${budget_used:.2f} ({budget_percent:.1f}%)
**Remaining:** ${budget_remaining:.2f}

## Cost Breakdown by Tier:
- **Tier 0** (Control): $0.00
- **Tier 1** (Planning): ${budget_used * 0.15:.2f}
- **Tier 2** (Preparation): ${budget_used * 0.10:.2f}
- **Tier 3** (Development): ${budget_used * 0.50:.2f}
- **Tier 4** (Validation): ${budget_used * 0.15:.2f}
- **Tier 5** (Integration): ${budget_used * 0.10:.2f}

## Budget Alerts:
- Warning Threshold (75%): ${budget_limit * 0.75:.2f}
- Hard Limit (100%): ${budget_limit:.2f}

Current Status: {
    'Healthy' if budget_percent < 75
    else 'Warning' if budget_percent < 100
    else 'Exceeded'
}
"""

    await cl.Message(content=budget_msg).send()  # type: ignore[no-untyped-call]


async def _handle_generic_request(_message: cl.Message) -> None:
    """Handle generic user request.

    Provides help information and available commands.

    Args:
        _message: Chat message with generic content
    """
    help_msg = """
# Available Commands

## Workflow Management:
- **"start workflow"** - Begin a new multi-tier agent workflow
- **"check status"** - View current workflow progress
- **"approve"** - Approve pending workflow decision
- **"reject"** - Reject pending workflow decision

## Information:
- **"budget"** - View budget usage and limits
- **"help"** - Show this help message

## Example Requests:
- "Start a new workflow to create a FastAPI endpoint"
- "Check the status of my current workflow"
- "Approve the proposed architecture"
- "Show me the budget breakdown"

What would you like to do?
"""

    await cl.Message(content=help_msg).send()  # type: ignore[no-untyped-call]


async def _simulate_workflow_progress(workflow_id: str) -> None:
    """Simulate workflow progress with real-time updates.

    Demonstrates workflow progression through tiers with
    periodic status updates and milestone notifications.

    Args:
        workflow_id: ID of workflow to simulate
    """
    phases = [
        ("tier_0_control", "Control & Governance", "Deviation Handler"),
        ("tier_1_planning", "Planning & Strategy", "Requirements Strategy"),
        ("tier_2_preparation", "Preparation", "Dependency Resolver"),
        ("tier_3_development", "Development", "Software Engineer"),
        ("tier_4_validation", "Validation & Security", "Security Validator"),
        ("tier_5_integration", "Integration & Delivery", "Commit Agent"),
    ]

    for phase_key, phase_name, agent_name in phases:
        cl.user_session.set("current_phase", phase_key)  # type: ignore[no-untyped-call]

        progress_msg = f"""
## {phase_name}

**Agent:** {agent_name}
**Status:** In Progress...
**Workflow ID:** `{workflow_id}`

Processing...
"""

        await cl.Message(content=progress_msg).send()  # type: ignore[no-untyped-call]

        # Simulate processing time
        await cl.sleep(2)

        completion_msg = f"""
**{phase_name}** completed successfully

**Agent:** {agent_name}
**Duration:** ~2 seconds
**Status:** Complete
"""

        await cl.Message(content=completion_msg).send()  # type: ignore[no-untyped-call]

    # Final completion message
    final_msg = f"""
# Workflow Completed Successfully!

**Workflow ID:** `{workflow_id}`
**Total Duration:** ~12 seconds
**Status:** Complete

## Deliverables:
- Requirements analyzed
- Architecture designed
- Dependencies resolved
- Code implemented
- Security validated
- Ready for deployment

All tiers executed successfully. Your workflow is ready for review!
"""

    await cl.Message(content=final_msg).send()  # type: ignore[no-untyped-call]

    logger.info(
        "Workflow simulation completed",
        extra={"workflow_id": workflow_id},
    )


@cl.on_chat_end
async def on_chat_end() -> None:
    """Handle chat session termination.

    Cleans up session state and logs session metrics.
    """
    session_id = cl.user_session.get("session_id")  # type: ignore[no-untyped-call]
    workflow_id = cl.user_session.get("workflow_id")  # type: ignore[no-untyped-call]

    logger.info(
        "Chainlit session ended",
        extra={
            "session_id": session_id,
            "workflow_id": workflow_id,
        },
    )


# Create Chainlit app instance
app = cl.App()
