"""Unit tests for structured logging (structlog configuration)."""

import logging
from unittest.mock import MagicMock, patch

from src import __version__
from src.observability.logging import (
    add_app_context,
    bind_agent_context,
    bind_task_context,
    bind_workflow_context,
    configure_logging,
    get_logger,
    log_budget_status,
    log_llm_call,
)


class TestAddAppContext:
    """Test add_app_context processor."""

    def test_add_app_context_enriches_event_dict(self):
        """Test that add_app_context adds application context."""
        event_dict = {"event": "test_event"}

        result = add_app_context(None, None, event_dict)

        assert result["service"] == "agent-api"
        assert result["environment"] is not None
        assert result["version"] == __version__
        assert result["event"] == "test_event"

    def test_add_app_context_preserves_existing_fields(self):
        """Test that add_app_context preserves existing fields."""
        event_dict = {"event": "test_event", "custom_field": "custom_value"}

        result = add_app_context(None, None, event_dict)

        assert result["custom_field"] == "custom_value"
        assert result["service"] == "agent-api"


class TestConfigureLogging:
    """Test logging configuration."""

    def test_configure_logging_sets_up_structlog(self):
        """Test that configure_logging sets up structlog."""
        with (
            patch("src.observability.logging.logging.basicConfig"),
            patch("src.observability.logging.structlog.configure"),
        ):
            configure_logging()

            # Should not raise any errors

    def test_configure_logging_with_development_environment(self):
        """Test logging configuration in development environment."""
        with (
            patch("src.observability.logging.settings.environment", "development"),
            patch("src.observability.logging.logging.basicConfig"),
            patch("src.observability.logging.structlog.configure") as mock_configure,
        ):
            configure_logging()

            # Verify structlog.configure was called
            mock_configure.assert_called_once()

    def test_configure_logging_with_production_environment(self):
        """Test logging configuration in production environment."""
        with (
            patch("src.observability.logging.settings.environment", "production"),
            patch("src.observability.logging.logging.basicConfig"),
            patch("src.observability.logging.structlog.configure") as mock_configure,
        ):
            configure_logging()

            # Verify structlog.configure was called
            mock_configure.assert_called_once()

    def test_configure_logging_sets_log_level(self):
        """Test that configure_logging sets the correct log level."""
        with (
            patch("src.observability.logging.settings.log_level", "DEBUG"),
            patch("src.observability.logging.logging.basicConfig") as mock_basic_config,
            patch("src.observability.logging.structlog.configure"),
        ):
            configure_logging()

            # Verify basicConfig was called with DEBUG level
            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == logging.DEBUG


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger(__name__)

        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_get_logger_with_different_names(self):
        """Test get_logger with different module names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1 is not None
        assert logger2 is not None


class TestBindWorkflowContext:
    """Test workflow context binding."""

    def test_bind_workflow_context_sets_context_vars(self):
        """Test that bind_workflow_context sets context variables."""
        with (
            patch("src.observability.logging.structlog.contextvars.clear_contextvars"),
            patch(
                "src.observability.logging.structlog.contextvars.bind_contextvars"
            ) as mock_bind,
        ):
            bind_workflow_context("wf-001", "trace-abc123")

            mock_bind.assert_called_once_with(
                workflow_id="wf-001",
                trace_id="trace-abc123",
            )

    def test_bind_workflow_context_clears_previous_context(self):
        """Test that bind_workflow_context clears previous context."""
        with (
            patch(
                "src.observability.logging.structlog.contextvars.clear_contextvars"
            ) as mock_clear,
            patch("src.observability.logging.structlog.contextvars.bind_contextvars"),
        ):
            bind_workflow_context("wf-001", "trace-abc123")

            mock_clear.assert_called_once()


class TestBindAgentContext:
    """Test agent context binding."""

    def test_bind_agent_context_sets_context_vars(self):
        """Test that bind_agent_context sets context variables."""
        with patch(
            "src.observability.logging.structlog.contextvars.bind_contextvars"
        ) as mock_bind:
            bind_agent_context("software_engineer", 3)

            mock_bind.assert_called_once_with(
                agent_name="software_engineer",
                tier=3,
            )

    def test_bind_agent_context_with_different_agents(self):
        """Test bind_agent_context with different agent names."""
        with patch("src.observability.logging.structlog.contextvars.bind_contextvars"):
            # Should not raise errors
            bind_agent_context("quality_engineer", 3)
            bind_agent_context("security_validator", 4)
            bind_agent_context("static_analysis", 3)


class TestBindTaskContext:
    """Test task context binding."""

    def test_bind_task_context_sets_context_vars(self):
        """Test that bind_task_context sets context variables."""
        with patch(
            "src.observability.logging.structlog.contextvars.bind_contextvars"
        ) as mock_bind:
            bind_task_context("TASK-025", "Implement main.py", "src/main.py")

            mock_bind.assert_called_once_with(
                task_id="TASK-025",
                task_name="Implement main.py",
                file="src/main.py",
            )

    def test_bind_task_context_with_different_tasks(self):
        """Test bind_task_context with different task information."""
        with patch("src.observability.logging.structlog.contextvars.bind_contextvars"):
            # Should not raise errors
            bind_task_context("TASK-001", "Task 1", "file1.py")
            bind_task_context("TASK-002", "Task 2", "file2.py")


class TestLogLLMCall:
    """Test LLM call logging."""

    def test_log_llm_call_logs_all_metrics(self):
        """Test that log_llm_call logs all LLM metrics."""
        mock_logger = MagicMock()

        log_llm_call(
            mock_logger,
            provider="openrouter",
            model="deepseek/deepseek-chat",
            tokens_input=5400,
            tokens_output=1200,
            cost_usd=0.0012,
            latency_ms=3450,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "llm.call_completed"
        assert call_args[1]["llm"]["provider"] == "openrouter"
        assert call_args[1]["llm"]["model"] == "deepseek/deepseek-chat"
        assert call_args[1]["llm"]["tokens_input"] == 5400
        assert call_args[1]["llm"]["tokens_output"] == 1200
        assert call_args[1]["llm"]["cost_usd"] == 0.0012
        assert call_args[1]["llm"]["latency_ms"] == 3450

    def test_log_llm_call_with_different_providers(self):
        """Test log_llm_call with different LLM providers."""
        mock_logger = MagicMock()

        log_llm_call(
            mock_logger,
            provider="google",
            model="gemini-2.0-flash",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.0005,
            latency_ms=1200,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["llm"]["provider"] == "google"

    def test_log_llm_call_with_zero_cost(self):
        """Test log_llm_call with zero cost."""
        mock_logger = MagicMock()

        log_llm_call(
            mock_logger,
            provider="openrouter",
            model="test-model",
            tokens_input=100,
            tokens_output=50,
            cost_usd=0.0,
            latency_ms=500,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["llm"]["cost_usd"] == 0.0


class TestLogBudgetStatus:
    """Test budget status logging."""

    def test_log_budget_status_logs_all_metrics(self):
        """Test that log_budget_status logs all budget metrics."""
        mock_logger = MagicMock()

        log_budget_status(
            mock_logger,
            remaining_tokens=487600,
            remaining_budget_usd=18.45,
            budget_percent_used=7.75,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "budget.status"
        assert call_args[1]["budget"]["remaining_tokens"] == 487600
        assert call_args[1]["budget"]["remaining_budget_usd"] == 18.45
        assert call_args[1]["budget"]["budget_percent_used"] == 7.75

    def test_log_budget_status_with_high_usage(self):
        """Test log_budget_status with high budget usage."""
        mock_logger = MagicMock()

        log_budget_status(
            mock_logger,
            remaining_tokens=50000,
            remaining_budget_usd=2.0,
            budget_percent_used=95.0,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["budget"]["budget_percent_used"] == 95.0

    def test_log_budget_status_with_zero_remaining(self):
        """Test log_budget_status with zero remaining budget."""
        mock_logger = MagicMock()

        log_budget_status(
            mock_logger,
            remaining_tokens=0,
            remaining_budget_usd=0.0,
            budget_percent_used=100.0,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["budget"]["remaining_tokens"] == 0
        assert call_args[1]["budget"]["remaining_budget_usd"] == 0.0


class TestLoggingEdgeCases:
    """Test edge cases and error conditions."""

    def test_bind_workflow_context_with_special_characters(self):
        """Test bind_workflow_context with special characters in IDs."""
        with (
            patch("src.observability.logging.structlog.contextvars.clear_contextvars"),
            patch(
                "src.observability.logging.structlog.contextvars.bind_contextvars"
            ) as mock_bind,
        ):
            bind_workflow_context("wf-2026-01-26-abc123", "trace-xyz-789")

            mock_bind.assert_called_once()

    def test_bind_task_context_with_long_names(self):
        """Test bind_task_context with long task names."""
        with patch("src.observability.logging.structlog.contextvars.bind_contextvars"):
            long_name = "A" * 500
            bind_task_context("TASK-001", long_name, "file.py")

    def test_log_llm_call_with_large_token_counts(self):
        """Test log_llm_call with large token counts."""
        mock_logger = MagicMock()

        log_llm_call(
            mock_logger,
            provider="openrouter",
            model="test-model",
            tokens_input=1000000,
            tokens_output=500000,
            cost_usd=100.0,
            latency_ms=60000,
        )

        mock_logger.info.assert_called_once()

    def test_log_budget_status_with_fractional_values(self):
        """Test log_budget_status with fractional values."""
        mock_logger = MagicMock()

        log_budget_status(
            mock_logger,
            remaining_tokens=123456,
            remaining_budget_usd=12.3456,
            budget_percent_used=45.6789,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["budget"]["remaining_budget_usd"] == 12.3456
        assert call_args[1]["budget"]["budget_percent_used"] == 45.6789


class TestLoggingIntegration:
    """Test logging integration scenarios."""

    def test_workflow_context_propagation(self):
        """Test that workflow context propagates through logger calls."""
        with (
            patch("src.observability.logging.structlog.contextvars.clear_contextvars"),
            patch("src.observability.logging.structlog.contextvars.bind_contextvars"),
        ):
            bind_workflow_context("wf-001", "trace-123")
            logger = get_logger(__name__)

            # Logger should be available
            assert logger is not None

    def test_multiple_context_bindings(self):
        """Test multiple context bindings in sequence."""
        with (
            patch("src.observability.logging.structlog.contextvars.clear_contextvars"),
            patch("src.observability.logging.structlog.contextvars.bind_contextvars"),
        ):
            bind_workflow_context("wf-001", "trace-123")
            bind_agent_context("software_engineer", 3)
            bind_task_context("TASK-025", "Implement feature", "src/main.py")

            # Should not raise errors


class TestAdditionalLoggingHelpers:
    """Tests for remaining logging helpers."""

    def test_log_error_includes_context(self):
        """Test log_error passes error dict and context."""
        mock_logger = MagicMock()

        from src.observability.logging import log_error

        log_error(
            mock_logger,
            error_type="ValueError",
            message="Bad input",
            file="src/file.py",
            line=10,
            context={"detail": "x"},
        )

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "error.occurred"
        assert call_args[1]["error"]["type"] == "ValueError"
        assert call_args[1]["error"]["file"] == "src/file.py"

    def test_log_agent_execution_with_rejection(self):
        """Test log_agent_execution with rejection reason."""
        mock_logger = MagicMock()

        from src.observability.logging import log_agent_execution

        log_agent_execution(
            mock_logger,
            agent_name="quality_engineer",
            tier=3,
            status="rejected",
            duration_seconds=12.3,
            rejection_reason="Coverage low",
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "agent.execution_completed"
        assert call_args[1]["rejection_reason"] == "Coverage low"

    def test_log_checkpoint_saved(self):
        """Test log_checkpoint_saved helper."""
        mock_logger = MagicMock()

        from src.observability.logging import log_checkpoint_saved

        log_checkpoint_saved(
            mock_logger,
            checkpoint_id="ckpt-1",
            workflow_id="wf-1",
            phase="development",
            duration_seconds=0.5,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "checkpoint.saved"
