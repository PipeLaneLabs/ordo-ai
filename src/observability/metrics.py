"""
Prometheus Metrics

Define and instrument Prometheus metrics for monitoring the agent ecosystem.
Implements RED metrics, workflow metrics, cost tracking, and infrastructure metrics.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram


# ============================================================================
# RED Metrics (Request-focused)
# ============================================================================

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_errors_total = Counter(
    "http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "status", "error_type"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# ============================================================================
# Workflow-Specific Metrics
# ============================================================================

workflow_duration_seconds = Histogram(
    "workflow_duration_seconds",
    "Workflow execution time in seconds",
    ["workflow_id", "status"],
    buckets=[60, 300, 900, 1800, 3600, 7200, 14400],  # 1min to 4hrs
)

agent_execution_duration = Histogram(
    "agent_execution_duration_seconds",
    "Agent execution time in seconds",
    ["agent_name", "tier", "status"],
    buckets=[1, 5, 10, 30, 60, 300, 600],  # 1s to 10min
)

agent_rejections_total = Counter(
    "agent_rejections_total",
    "Total agent rejections",
    ["agent_name", "rejected_by", "reason"],
)

workflow_rejection_count = Gauge(
    "workflow_rejection_count",
    "Current rejection depth for workflow",
    ["workflow_id"],
)

# ============================================================================
# Checkpoint Metrics
# ============================================================================

checkpoints_created_total = Counter(
    "checkpoints_created_total",
    "Total checkpoints created",
    ["workflow_id"],
)

checkpoint_save_duration = Histogram(
    "checkpoint_save_duration_seconds",
    "Checkpoint save latency",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)

# ============================================================================
# Cost & Budget Metrics
# ============================================================================

llm_tokens_consumed_total = Counter(
    "llm_tokens_consumed_total",
    "Total LLM tokens consumed",
    ["provider", "model", "agent_name", "token_type"],  # token_type: input/output
)

llm_cost_usd_total = Counter(
    "llm_cost_usd_total",
    "Total LLM cost in USD",
    ["provider", "model", "agent_name"],
)

budget_remaining_tokens = Gauge(
    "budget_remaining_tokens",
    "Remaining token budget",
    ["workflow_id"],
)

budget_percent_used = Gauge(
    "budget_percent_used",
    "Budget usage percentage",
    ["workflow_id"],
)

# ============================================================================
# Infrastructure Metrics
# ============================================================================

db_connections_active = Gauge(
    "db_connections_active",
    "Active database connections",
    ["database"],
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["operation"],  # select, insert, update
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

cache_hits_total = Counter(
    "cache_hits_total",
    "Cache hit count",
    ["cache_key_prefix"],
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Cache miss count",
    ["cache_key_prefix"],
)

artifacts_stored_bytes_total = Counter(
    "artifacts_stored_bytes_total",
    "Total artifact storage in bytes",
    ["artifact_type"],  # code, report, checkpoint
)

# ============================================================================
# Service Level Indicators (SLIs)
# ============================================================================

workflows_started_total = Counter(
    "workflows_started_total",
    "Total workflows started",
)

workflows_completed_total = Counter(
    "workflows_completed_total",
    "Total workflows completed",
    ["status"],  # success, failed, timeout
)

workflows_within_budget_total = Counter(
    "workflows_within_budget_total",
    "Total workflows completed within budget",
)

# ============================================================================
# Human Approval Gate Metrics
# ============================================================================

human_approvals_requested_total = Counter(
    "human_approvals_requested_total",
    "Total human approvals requested",
    ["tier", "gate_type"],
)

human_approvals_granted_total = Counter(
    "human_approvals_granted_total",
    "Total human approvals granted",
    ["tier", "gate_type"],
)

human_approvals_rejected_total = Counter(
    "human_approvals_rejected_total",
    "Total human approvals rejected",
    ["tier", "gate_type"],
)

human_approval_wait_time_seconds = Histogram(
    "human_approval_wait_time_seconds",
    "Time waiting for human approval",
    ["tier", "gate_type"],
    buckets=[60, 300, 900, 1800, 3600, 7200],  # 1min to 2hrs
)

# ============================================================================
# Agent-Specific Metrics
# ============================================================================

software_engineer_files_generated_total = Counter(
    "software_engineer_files_generated_total",
    "Total files generated by Software Engineer",
    ["file_type"],  # py, js, ts, etc.
)

software_engineer_lines_of_code_total = Counter(
    "software_engineer_lines_of_code_total",
    "Total lines of code generated",
    ["file_type"],
)

static_analysis_issues_found_total = Counter(
    "static_analysis_issues_found_total",
    "Total static analysis issues found",
    ["severity", "tool"],  # severity: error, warning, info; tool: ruff, mypy, black
)

quality_engineer_tests_generated_total = Counter(
    "quality_engineer_tests_generated_total",
    "Total tests generated by Quality Engineer",
    ["test_type"],  # unit, integration, e2e
)

quality_engineer_coverage_percent = Gauge(
    "quality_engineer_coverage_percent",
    "Test coverage percentage",
    ["workflow_id"],
)

security_validator_vulnerabilities_found_total = Counter(
    "security_validator_vulnerabilities_found_total",
    "Total security vulnerabilities found",
    ["severity", "vulnerability_type"],
)

# ============================================================================
# Deviation Handler Metrics
# ============================================================================

deviation_handler_iterations_total = Counter(
    "deviation_handler_iterations_total",
    "Total deviation handler iterations",
    ["workflow_id"],
)

deviation_handler_max_iterations_reached_total = Counter(
    "deviation_handler_max_iterations_reached_total",
    "Total workflows reaching max deviation iterations",
)

# ============================================================================
# LLM Provider Metrics
# ============================================================================

llm_api_calls_total = Counter(
    "llm_api_calls_total",
    "Total LLM API calls",
    ["provider", "model", "status"],  # status: success, error, timeout
)

llm_api_latency_seconds = Histogram(
    "llm_api_latency_seconds",
    "LLM API call latency",
    ["provider", "model"],
    buckets=[1, 5, 10, 30, 60, 120, 300],  # 1s to 5min
)

llm_api_errors_total = Counter(
    "llm_api_errors_total",
    "Total LLM API errors",
    ["provider", "model", "error_type"],
)

llm_fallback_triggered_total = Counter(
    "llm_fallback_triggered_total",
    "Total LLM fallback triggers",
    ["primary_provider", "fallback_provider"],
)

# ============================================================================
# Storage Metrics
# ============================================================================

minio_upload_duration_seconds = Histogram(
    "minio_upload_duration_seconds",
    "MinIO upload duration",
    ["artifact_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

minio_download_duration_seconds = Histogram(
    "minio_download_duration_seconds",
    "MinIO download duration",
    ["artifact_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

redis_operation_duration_seconds = Histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration",
    ["operation"],  # get, set, delete, incr
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
)

# ============================================================================
# Rate Limiting Metrics
# ============================================================================

rate_limit_exceeded_total = Counter(
    "rate_limit_exceeded_total",
    "Total rate limit violations",
    ["user_id", "endpoint"],
)

rate_limit_current_usage = Gauge(
    "rate_limit_current_usage",
    "Current rate limit usage",
    ["user_id", "endpoint"],
)
