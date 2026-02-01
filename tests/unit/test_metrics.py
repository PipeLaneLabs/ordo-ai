"""Unit tests for Prometheus metrics."""

from prometheus_client import Counter, Gauge, Histogram

from src.observability import metrics


class TestMetricsDefinition:
    """Test that all metrics are properly defined."""

    def test_http_requests_total_is_counter(self):
        """Test that http_requests_total is a Counter."""
        assert isinstance(metrics.http_requests_total, Counter)

    def test_http_errors_total_is_counter(self):
        """Test that http_errors_total is a Counter."""
        assert isinstance(metrics.http_errors_total, Counter)

    def test_http_request_duration_seconds_is_histogram(self):
        """Test that http_request_duration_seconds is a Histogram."""
        assert isinstance(metrics.http_request_duration_seconds, Histogram)

    def test_workflow_duration_seconds_is_histogram(self):
        """Test that workflow_duration_seconds is a Histogram."""
        assert isinstance(metrics.workflow_duration_seconds, Histogram)

    def test_agent_execution_duration_is_histogram(self):
        """Test that agent_execution_duration is a Histogram."""
        assert isinstance(metrics.agent_execution_duration, Histogram)

    def test_agent_rejections_total_is_counter(self):
        """Test that agent_rejections_total is a Counter."""
        assert isinstance(metrics.agent_rejections_total, Counter)

    def test_workflow_rejection_count_is_gauge(self):
        """Test that workflow_rejection_count is a Gauge."""
        assert isinstance(metrics.workflow_rejection_count, Gauge)

    def test_checkpoints_created_total_is_counter(self):
        """Test that checkpoints_created_total is a Counter."""
        assert isinstance(metrics.checkpoints_created_total, Counter)

    def test_checkpoint_save_duration_is_histogram(self):
        """Test that checkpoint_save_duration is a Histogram."""
        assert isinstance(metrics.checkpoint_save_duration, Histogram)

    def test_llm_tokens_consumed_total_is_counter(self):
        """Test that llm_tokens_consumed_total is a Counter."""
        assert isinstance(metrics.llm_tokens_consumed_total, Counter)

    def test_llm_cost_usd_total_is_counter(self):
        """Test that llm_cost_usd_total is a Counter."""
        assert isinstance(metrics.llm_cost_usd_total, Counter)

    def test_budget_remaining_tokens_is_gauge(self):
        """Test that budget_remaining_tokens is a Gauge."""
        assert isinstance(metrics.budget_remaining_tokens, Gauge)

    def test_budget_percent_used_is_gauge(self):
        """Test that budget_percent_used is a Gauge."""
        assert isinstance(metrics.budget_percent_used, Gauge)

    def test_db_connections_active_is_gauge(self):
        """Test that db_connections_active is a Gauge."""
        assert isinstance(metrics.db_connections_active, Gauge)

    def test_db_query_duration_seconds_is_histogram(self):
        """Test that db_query_duration_seconds is a Histogram."""
        assert isinstance(metrics.db_query_duration_seconds, Histogram)

    def test_cache_hits_total_is_counter(self):
        """Test that cache_hits_total is a Counter."""
        assert isinstance(metrics.cache_hits_total, Counter)

    def test_cache_misses_total_is_counter(self):
        """Test that cache_misses_total is a Counter."""
        assert isinstance(metrics.cache_misses_total, Counter)

    def test_artifacts_stored_bytes_total_is_counter(self):
        """Test that artifacts_stored_bytes_total is a Counter."""
        assert isinstance(metrics.artifacts_stored_bytes_total, Counter)

    def test_workflows_started_total_is_counter(self):
        """Test that workflows_started_total is a Counter."""
        assert isinstance(metrics.workflows_started_total, Counter)

    def test_workflows_completed_total_is_counter(self):
        """Test that workflows_completed_total is a Counter."""
        assert isinstance(metrics.workflows_completed_total, Counter)

    def test_workflows_within_budget_total_is_counter(self):
        """Test that workflows_within_budget_total is a Counter."""
        assert isinstance(metrics.workflows_within_budget_total, Counter)

    def test_human_approvals_requested_total_is_counter(self):
        """Test that human_approvals_requested_total is a Counter."""
        assert isinstance(metrics.human_approvals_requested_total, Counter)

    def test_human_approvals_granted_total_is_counter(self):
        """Test that human_approvals_granted_total is a Counter."""
        assert isinstance(metrics.human_approvals_granted_total, Counter)

    def test_human_approvals_rejected_total_is_counter(self):
        """Test that human_approvals_rejected_total is a Counter."""
        assert isinstance(metrics.human_approvals_rejected_total, Counter)

    def test_human_approval_wait_time_seconds_is_histogram(self):
        """Test that human_approval_wait_time_seconds is a Histogram."""
        assert isinstance(metrics.human_approval_wait_time_seconds, Histogram)

    def test_software_engineer_files_generated_total_is_counter(self):
        """Test that software_engineer_files_generated_total is a Counter."""
        assert isinstance(metrics.software_engineer_files_generated_total, Counter)

    def test_software_engineer_lines_of_code_total_is_counter(self):
        """Test that software_engineer_lines_of_code_total is a Counter."""
        assert isinstance(metrics.software_engineer_lines_of_code_total, Counter)

    def test_static_analysis_issues_found_total_is_counter(self):
        """Test that static_analysis_issues_found_total is a Counter."""
        assert isinstance(metrics.static_analysis_issues_found_total, Counter)

    def test_quality_engineer_tests_generated_total_is_counter(self):
        """Test that quality_engineer_tests_generated_total is a Counter."""
        assert isinstance(metrics.quality_engineer_tests_generated_total, Counter)

    def test_quality_engineer_coverage_percent_is_gauge(self):
        """Test that quality_engineer_coverage_percent is a Gauge."""
        assert isinstance(metrics.quality_engineer_coverage_percent, Gauge)

    def test_security_validator_vulnerabilities_found_total_is_counter(self):
        """Test that security_validator_vulnerabilities_found_total is a Counter."""
        assert isinstance(
            metrics.security_validator_vulnerabilities_found_total, Counter
        )

    def test_deviation_handler_iterations_total_is_counter(self):
        """Test that deviation_handler_iterations_total is a Counter."""
        assert isinstance(metrics.deviation_handler_iterations_total, Counter)

    def test_deviation_handler_max_iterations_reached_total_is_counter(self):
        """Test that deviation_handler_max_iterations_reached_total is a Counter."""
        assert isinstance(
            metrics.deviation_handler_max_iterations_reached_total, Counter
        )

    def test_llm_api_calls_total_is_counter(self):
        """Test that llm_api_calls_total is a Counter."""
        assert isinstance(metrics.llm_api_calls_total, Counter)

    def test_llm_api_latency_seconds_is_histogram(self):
        """Test that llm_api_latency_seconds is a Histogram."""
        assert isinstance(metrics.llm_api_latency_seconds, Histogram)

    def test_llm_api_errors_total_is_counter(self):
        """Test that llm_api_errors_total is a Counter."""
        assert isinstance(metrics.llm_api_errors_total, Counter)

    def test_llm_fallback_triggered_total_is_counter(self):
        """Test that llm_fallback_triggered_total is a Counter."""
        assert isinstance(metrics.llm_fallback_triggered_total, Counter)


class TestREDMetrics:
    """Test RED (Request, Error, Duration) metrics."""

    def test_http_requests_total_has_labels(self):
        """Test that http_requests_total has correct labels."""
        # Verify metric can be incremented with labels
        metrics.http_requests_total.labels(
            method="GET", endpoint="/api/workflows", status="200"
        ).inc()

    def test_http_errors_total_has_labels(self):
        """Test that http_errors_total has correct labels."""
        metrics.http_errors_total.labels(
            method="POST",
            endpoint="/api/workflows",
            status="500",
            error_type="InternalError",
        ).inc()

    def test_http_request_duration_seconds_has_labels(self):
        """Test that http_request_duration_seconds has correct labels."""
        metrics.http_request_duration_seconds.labels(
            method="GET", endpoint="/api/workflows"
        ).observe(0.5)


class TestWorkflowMetrics:
    """Test workflow-specific metrics."""

    def test_workflow_duration_seconds_has_labels(self):
        """Test that workflow_duration_seconds has correct labels."""
        metrics.workflow_duration_seconds.labels(
            workflow_id="wf-001", status="success"
        ).observe(120)

    def test_agent_execution_duration_has_labels(self):
        """Test that agent_execution_duration has correct labels."""
        metrics.agent_execution_duration.labels(
            agent_name="software_engineer", tier="3", status="success"
        ).observe(45)

    def test_agent_rejections_total_has_labels(self):
        """Test that agent_rejections_total has correct labels."""
        metrics.agent_rejections_total.labels(
            agent_name="software_engineer",
            rejected_by="quality_engineer",
            reason="coverage_below_threshold",
        ).inc()

    def test_workflow_rejection_count_has_labels(self):
        """Test that workflow_rejection_count has correct labels."""
        metrics.workflow_rejection_count.labels(workflow_id="wf-001").set(2)


class TestCheckpointMetrics:
    """Test checkpoint metrics."""

    def test_checkpoints_created_total_has_labels(self):
        """Test that checkpoints_created_total has correct labels."""
        metrics.checkpoints_created_total.labels(workflow_id="wf-001").inc()

    def test_checkpoint_save_duration_observe(self):
        """Test that checkpoint_save_duration can observe values."""
        metrics.checkpoint_save_duration.observe(0.5)


class TestCostMetrics:
    """Test cost and budget metrics."""

    def test_llm_tokens_consumed_total_has_labels(self):
        """Test that llm_tokens_consumed_total has correct labels."""
        metrics.llm_tokens_consumed_total.labels(
            provider="openrouter",
            model="deepseek/deepseek-chat",
            agent_name="software_engineer",
            token_type="input",
        ).inc(5400)

    def test_llm_cost_usd_total_has_labels(self):
        """Test that llm_cost_usd_total has correct labels."""
        metrics.llm_cost_usd_total.labels(
            provider="openrouter",
            model="deepseek/deepseek-chat",
            agent_name="software_engineer",
        ).inc(0.0012)

    def test_budget_remaining_tokens_has_labels(self):
        """Test that budget_remaining_tokens has correct labels."""
        metrics.budget_remaining_tokens.labels(workflow_id="wf-001").set(487600)

    def test_budget_percent_used_has_labels(self):
        """Test that budget_percent_used has correct labels."""
        metrics.budget_percent_used.labels(workflow_id="wf-001").set(7.75)


class TestInfrastructureMetrics:
    """Test infrastructure metrics."""

    def test_db_connections_active_has_labels(self):
        """Test that db_connections_active has correct labels."""
        metrics.db_connections_active.labels(database="postgres").set(5)

    def test_db_query_duration_seconds_has_labels(self):
        """Test that db_query_duration_seconds has correct labels."""
        metrics.db_query_duration_seconds.labels(operation="select").observe(0.05)

    def test_cache_hits_total_has_labels(self):
        """Test that cache_hits_total has correct labels."""
        metrics.cache_hits_total.labels(cache_key_prefix="session").inc()

    def test_cache_misses_total_has_labels(self):
        """Test that cache_misses_total has correct labels."""
        metrics.cache_misses_total.labels(cache_key_prefix="session").inc()

    def test_artifacts_stored_bytes_total_has_labels(self):
        """Test that artifacts_stored_bytes_total has correct labels."""
        metrics.artifacts_stored_bytes_total.labels(artifact_type="code").inc(1024)


class TestSLIMetrics:
    """Test Service Level Indicator metrics."""

    def test_workflows_started_total_increment(self):
        """Test that workflows_started_total can be incremented."""
        metrics.workflows_started_total.inc()

    def test_workflows_completed_total_has_labels(self):
        """Test that workflows_completed_total has correct labels."""
        metrics.workflows_completed_total.labels(status="success").inc()

    def test_workflows_within_budget_total_increment(self):
        """Test that workflows_within_budget_total can be incremented."""
        metrics.workflows_within_budget_total.inc()


class TestHumanApprovalMetrics:
    """Test human approval gate metrics."""

    def test_human_approvals_requested_total_has_labels(self):
        """Test that human_approvals_requested_total has correct labels."""
        metrics.human_approvals_requested_total.labels(
            tier="4", gate_type="final_approval"
        ).inc()

    def test_human_approvals_granted_total_has_labels(self):
        """Test that human_approvals_granted_total has correct labels."""
        metrics.human_approvals_granted_total.labels(
            tier="4", gate_type="final_approval"
        ).inc()

    def test_human_approvals_rejected_total_has_labels(self):
        """Test that human_approvals_rejected_total has correct labels."""
        metrics.human_approvals_rejected_total.labels(
            tier="4", gate_type="final_approval"
        ).inc()

    def test_human_approval_wait_time_seconds_has_labels(self):
        """Test that human_approval_wait_time_seconds has correct labels."""
        metrics.human_approval_wait_time_seconds.labels(
            tier="4", gate_type="final_approval"
        ).observe(1800)


class TestAgentMetrics:
    """Test agent-specific metrics."""

    def test_software_engineer_files_generated_total_has_labels(self):
        """Test that software_engineer_files_generated_total has correct labels."""
        metrics.software_engineer_files_generated_total.labels(file_type="py").inc()

    def test_software_engineer_lines_of_code_total_has_labels(self):
        """Test that software_engineer_lines_of_code_total has correct labels."""
        metrics.software_engineer_lines_of_code_total.labels(file_type="py").inc(150)

    def test_static_analysis_issues_found_total_has_labels(self):
        """Test that static_analysis_issues_found_total has correct labels."""
        metrics.static_analysis_issues_found_total.labels(
            severity="error", tool="ruff"
        ).inc()

    def test_quality_engineer_tests_generated_total_has_labels(self):
        """Test that quality_engineer_tests_generated_total has correct labels."""
        metrics.quality_engineer_tests_generated_total.labels(test_type="unit").inc()

    def test_quality_engineer_coverage_percent_has_labels(self):
        """Test that quality_engineer_coverage_percent has correct labels."""
        metrics.quality_engineer_coverage_percent.labels(workflow_id="wf-001").set(85.5)

    def test_security_validator_vulnerabilities_found_total_has_labels(self):
        """Test that security_validator_vulnerabilities_found_total has correct labels."""
        metrics.security_validator_vulnerabilities_found_total.labels(
            severity="HIGH", vulnerability_type="sql_injection"
        ).inc()


class TestDeviationHandlerMetrics:
    """Test deviation handler metrics."""

    def test_deviation_handler_iterations_total_has_labels(self):
        """Test that deviation_handler_iterations_total has correct labels."""
        metrics.deviation_handler_iterations_total.labels(workflow_id="wf-001").inc()

    def test_deviation_handler_max_iterations_reached_total_increment(self):
        """Test that deviation_handler_max_iterations_reached_total can be incremented."""
        metrics.deviation_handler_max_iterations_reached_total.inc()


class TestLLMProviderMetrics:
    """Test LLM provider metrics."""

    def test_llm_api_calls_total_has_labels(self):
        """Test that llm_api_calls_total has correct labels."""
        metrics.llm_api_calls_total.labels(
            provider="openrouter", model="deepseek/deepseek-chat", status="success"
        ).inc()

    def test_llm_api_latency_seconds_has_labels(self):
        """Test that llm_api_latency_seconds has correct labels."""
        metrics.llm_api_latency_seconds.labels(
            provider="openrouter", model="deepseek/deepseek-chat"
        ).observe(3.45)

    def test_llm_api_errors_total_has_labels(self):
        """Test that llm_api_errors_total has correct labels."""
        metrics.llm_api_errors_total.labels(
            provider="openrouter",
            model="deepseek/deepseek-chat",
            error_type="rate_limit",
        ).inc()

    def test_llm_fallback_triggered_total_has_labels(self):
        """Test that llm_fallback_triggered_total has correct labels."""
        metrics.llm_fallback_triggered_total.labels(
            primary_provider="openrouter", fallback_provider="google"
        ).inc()


class TestMetricsEdgeCases:
    """Test edge cases and error conditions."""

    def test_counter_increment_multiple_times(self):
        """Test that counters can be incremented multiple times."""
        counter = Counter("test_counter", "Test counter")
        counter.inc()
        counter.inc()
        counter.inc(5)

    def test_gauge_set_different_values(self):
        """Test that gauges can be set to different values."""
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(10)
        gauge.set(20)
        gauge.set(0)

    def test_histogram_observe_various_values(self):
        """Test that histograms can observe various values."""
        histogram = Histogram("test_histogram", "Test histogram")
        histogram.observe(0.1)
        histogram.observe(1.0)
        histogram.observe(10.0)
        histogram.observe(100.0)

    def test_metrics_with_many_labels(self):
        """Test metrics with many label combinations."""
        for i in range(10):
            metrics.http_requests_total.labels(
                method="GET", endpoint=f"/api/endpoint{i}", status="200"
            ).inc()

    def test_metrics_with_special_characters_in_labels(self):
        """Test metrics with special characters in label values."""
        metrics.agent_rejections_total.labels(
            agent_name="software_engineer",
            rejected_by="quality_engineer",
            reason="coverage_below_70_percent",
        ).inc()
