"""
Structured Logging

structlog configuration with JSON output and trace IDs.
Provides consistent logging across all agents and services.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.typing import EventDict, Processor

from src.config import settings


def add_app_context(
    _logger: logging.Logger, _method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add application-level context to all log entries.

    Args:
        _logger: Logger instance (unused, required by structlog)
        _method_name: Method name being called (unused, required by structlog)
        event_dict: Event dictionary to enrich

    Returns:
        Enriched event dictionary
    """
    event_dict["service"] = "agent-api"
    event_dict["environment"] = settings.environment
    event_dict["version"] = "0.1.0-alpha"
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog for the application.

    Sets up structured logging with:
    - JSON output in production
    - Human-readable console output in development
    - Trace ID and workflow ID propagation
    - Log level filtering based on environment

    Example:
        >>> from src.observability.logging import configure_logging
        >>> configure_logging()
        >>> logger = structlog.get_logger(__name__)
        >>> logger.info("application.started", port=8000)
    """
    # Determine log level
    log_level = getattr(logging, settings.log_level)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Shared processors for all environments
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_app_context,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # Environment-specific processors
    if settings.environment == "production":
        # Production: JSON output for log aggregation
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Human-readable console output
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger

    Example:
        >>> from src.observability.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("task.started", task_id="TASK-001")
    """
    return structlog.get_logger(name)  # type: ignore[no-any-return]


def bind_workflow_context(workflow_id: str, trace_id: str) -> None:
    """
    Bind workflow context to all subsequent log entries.

    Args:
        workflow_id: Workflow identifier
        trace_id: Distributed trace identifier

    Example:
        >>> from src.observability.logging import bind_workflow_context
        >>> bind_workflow_context("wf-001", "trace-abc123")
        >>> logger.info("workflow.started")  # Includes workflow_id and trace_id
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        workflow_id=workflow_id,
        trace_id=trace_id,
    )


def bind_agent_context(agent_name: str, tier: int) -> None:
    """
    Bind agent context to all subsequent log entries.

    Args:
        agent_name: Agent name (e.g., "software_engineer")
        tier: Agent tier (0-5)

    Example:
        >>> from src.observability.logging import bind_agent_context
        >>> bind_agent_context("software_engineer", 3)
        >>> logger.info("agent.started")  # Includes agent_name and tier
    """
    structlog.contextvars.bind_contextvars(
        agent_name=agent_name,
        tier=tier,
    )


def bind_task_context(task_id: str, task_name: str, file: str) -> None:
    """
    Bind task context to all subsequent log entries.

    Args:
        task_id: Task identifier (e.g., "TASK-025")
        task_name: Human-readable task name
        file: File being modified

    Example:
        >>> from src.observability.logging import bind_task_context
        >>> bind_task_context("TASK-025", "Implement main.py", "src/main.py")
        >>> logger.info("task.started")  # Includes task details
    """
    structlog.contextvars.bind_contextvars(
        task_id=task_id,
        task_name=task_name,
        file=file,
    )


def log_llm_call(
    logger: structlog.stdlib.BoundLogger,
    provider: str,
    model: str,
    tokens_input: int,
    tokens_output: int,
    cost_usd: float,
    latency_ms: int,
) -> None:
    """
    Log LLM API call with cost and performance metrics.

    Args:
        logger: Logger instance
        provider: LLM provider (e.g., "openrouter", "google")
        model: Model name
        tokens_input: Input tokens consumed
        tokens_output: Output tokens generated
        cost_usd: Cost in USD
        latency_ms: API call latency in milliseconds

    Example:
        >>> from src.observability.logging import get_logger, log_llm_call
        >>> logger = get_logger(__name__)
        >>> log_llm_call(
        ...     logger,
        ...     provider="openrouter",
        ...     model="deepseek/deepseek-chat",
        ...     tokens_input=5400,
        ...     tokens_output=1200,
        ...     cost_usd=0.0012,
        ...     latency_ms=3450
        ... )
    """
    logger.info(
        "llm.call_completed",
        llm={
            "provider": provider,
            "model": model,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
        },
    )


def log_budget_status(
    logger: structlog.stdlib.BoundLogger,
    remaining_tokens: int,
    remaining_budget_usd: float,
    budget_percent_used: float,
) -> None:
    """
    Log current budget status.

    Args:
        logger: Logger instance
        remaining_tokens: Remaining token budget
        remaining_budget_usd: Remaining budget in USD
        budget_percent_used: Percentage of budget used

    Example:
        >>> from src.observability.logging import get_logger, log_budget_status
        >>> logger = get_logger(__name__)
        >>> log_budget_status(
        ...     logger,
        ...     remaining_tokens=487600,
        ...     remaining_budget_usd=18.45,
        ...     budget_percent_used=7.75
        ... )
    """
    logger.info(
        "budget.status",
        budget={
            "remaining_tokens": remaining_tokens,
            "remaining_budget_usd": remaining_budget_usd,
            "budget_percent_used": budget_percent_used,
        },
    )


def log_error(
    logger: structlog.stdlib.BoundLogger,
    error_type: str,
    message: str,
    file: str | None = None,
    line: int | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Log error with structured context.

    Args:
        logger: Logger instance
        error_type: Error type/class name
        message: Error message
        file: File where error occurred (optional)
        line: Line number where error occurred (optional)
        context: Additional error context (optional)

    Example:
        >>> from src.observability.logging import get_logger, log_error
        >>> logger = get_logger(__name__)
        >>> log_error(
        ...     logger,
        ...     error_type="ValidationError",
        ...     message="Test coverage below threshold",
        ...     file="src/api/routes.py",
        ...     line=45,
        ...     context={"coverage": 68, "threshold": 70}
        ... )
    """
    error_dict: dict[str, Any] = {
        "type": error_type,
        "message": message,
    }

    if file:
        error_dict["file"] = file
    if line:
        error_dict["line"] = line

    logger.error(
        "error.occurred",
        error=error_dict,
        context=context or {},
    )


def log_agent_execution(
    logger: structlog.stdlib.BoundLogger,
    agent_name: str,
    tier: int,
    status: str,
    duration_seconds: float,
    rejection_reason: str | None = None,
) -> None:
    """
    Log agent execution completion.

    Args:
        logger: Logger instance
        agent_name: Agent name
        tier: Agent tier
        status: Execution status (completed, rejected, failed)
        duration_seconds: Execution duration
        rejection_reason: Reason for rejection (if applicable)

    Example:
        >>> from src.observability.logging import get_logger, log_agent_execution
        >>> logger = get_logger(__name__)
        >>> log_agent_execution(
        ...     logger,
        ...     agent_name="software_engineer",
        ...     tier=3,
        ...     status="rejected",
        ...     duration_seconds=45.2,
        ...     rejection_reason="Test coverage 68% < 70%"
        ... )
    """
    log_data: dict[str, Any] = {
        "agent": {
            "name": agent_name,
            "tier": tier,
        },
        "status": status,
        "duration_seconds": duration_seconds,
    }

    if rejection_reason:
        log_data["rejection_reason"] = rejection_reason

    logger.info("agent.execution_completed", **log_data)


def log_checkpoint_saved(
    logger: structlog.stdlib.BoundLogger,
    checkpoint_id: str,
    workflow_id: str,
    phase: str,
    duration_seconds: float,
) -> None:
    """
    Log checkpoint save operation.

    Args:
        logger: Logger instance
        checkpoint_id: Checkpoint identifier
        workflow_id: Workflow identifier
        phase: Current workflow phase
        duration_seconds: Save operation duration

    Example:
        >>> from src.observability.logging import get_logger, log_checkpoint_saved
        >>> logger = get_logger(__name__)
        >>> log_checkpoint_saved(
        ...     logger,
        ...     checkpoint_id="chk-67890",
        ...     workflow_id="wf-001",
        ...     phase="development",
        ...     duration_seconds=0.45
        ... )
    """
    logger.info(
        "checkpoint.saved",
        checkpoint_id=checkpoint_id,
        workflow_id=workflow_id,
        phase=phase,
        duration_seconds=duration_seconds,
    )
