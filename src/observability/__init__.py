"""
Observability Module

Provides structured logging and metrics instrumentation for the agent ecosystem.
"""

from src.observability.logging import configure_logging, get_logger
from src.observability.metrics import (
    agent_execution_duration,
    agent_rejections_total,
    budget_percent_used,
    budget_remaining_tokens,
    checkpoint_save_duration,
    checkpoints_created_total,
    http_errors_total,
    http_request_duration_seconds,
    http_requests_total,
    llm_cost_usd_total,
    llm_tokens_consumed_total,
    workflow_duration_seconds,
    workflow_rejection_count,
)


__all__ = [
    "agent_execution_duration",
    "agent_rejections_total",
    "budget_percent_used",
    "budget_remaining_tokens",
    "checkpoint_save_duration",
    "checkpoints_created_total",
    "configure_logging",
    "get_logger",
    "http_errors_total",
    "http_request_duration_seconds",
    "http_requests_total",
    "llm_cost_usd_total",
    "llm_tokens_consumed_total",
    "workflow_duration_seconds",
    "workflow_rejection_count",
]
