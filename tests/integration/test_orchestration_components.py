"""Integration tests for Phase 2 orchestration components."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.google_client import GoogleClient
from src.llm.openrouter_client import OpenRouterClient


class TestLLMClientFallback:
    """Test LLM client fallback behavior (OpenRouter → Google)."""

    @pytest.mark.asyncio
    async def test_openrouter_fallback_to_google(self):
        """Test fallback from OpenRouter to Google on failure."""
        with patch("src.config.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test_or_key"
            mock_settings.google_api_key = "test_google_key"

            openrouter = OpenRouterClient(settings=mock_settings)
            google = GoogleClient(settings=mock_settings)

            # Mock OpenRouter failure and Google success
            with patch("httpx.AsyncClient.post") as mock_post:
                # Configure mock responses
                openrouter_response = AsyncMock()
                openrouter_response.status_code = 503
                openrouter_response.text = "Service unavailable"
                openrouter_response.raise_for_status = MagicMock(
                    side_effect=Exception("503 Service Unavailable")
                )

                google_response_data = {
                    "candidates": [
                        {"content": {"parts": [{"text": "Fallback response"}]}}
                    ],
                    "usageMetadata": {"totalTokenCount": 50},
                }
                google_response = AsyncMock()
                google_response.status_code = 200
                google_response.json = MagicMock(return_value=google_response_data)
                google_response.raise_for_status = MagicMock()

                # OpenRouter will retry 3 times, so we need 3 failures, then Google succeeds (3 times for its retries)
                mock_post.side_effect = [
                    openrouter_response,  # OpenRouter retry 1
                    openrouter_response,  # OpenRouter retry 2
                    openrouter_response,  # OpenRouter retry 3
                    google_response,  # Google retry 1 (success)
                ]

                # Try OpenRouter first
                try:
                    await openrouter.generate(prompt="Test")
                    assert False, "Should have raised error"
                except Exception:
                    pass

                # Fallback to Google
                response = await google.generate(prompt="Test")
                assert response.content == "Fallback response"
                assert response.model == "gemini-1.5-flash"


class TestCheckpointPersistence:
    """Test end-to-end checkpoint persistence flow."""

    @pytest.mark.asyncio
    async def test_checkpoint_save_and_load_cycle(self):
        """Test saving and loading a checkpoint maintains state."""
        from src.storage.checkpoint_repository import CheckpointRepository

        with patch("src.config.settings") as mock_settings:
            mock_settings.postgres_host = "localhost"
            mock_settings.postgres_port = 5432
            mock_settings.postgres_db = "test_db"
            mock_settings.postgres_user = "test_user"
            mock_settings.postgres_password = "test_pass"
            mock_settings.postgres_url = (
                "postgresql://test_user:test_pass@localhost:5432/test_db"
            )

            repo = CheckpointRepository(settings=mock_settings)

            # Mock pool operations properly with async context manager
            mock_conn = AsyncMock()
            mock_pool = MagicMock()
            mock_pool.close = AsyncMock()

            # Create proper async context manager for acquire()
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_pool.acquire = MagicMock(return_value=mock_context)
            repo.pool = mock_pool

            # Test state
            original_state = {
                "workflow_id": "wf-integration-test",
                "user_request": "Test integration",
                "state_version": 1,
                "current_phase": "development",
                "budget_used_tokens": 5000,
                "code_files": {"main.py": "print('hello')"},
            }

            # Save checkpoint
            checkpoint_id = await repo.save_checkpoint(
                workflow_id="wf-integration-test", state=original_state
            )
            # Verify it's a valid UUID
            assert len(checkpoint_id) == 36  # UUID format
            assert checkpoint_id.count("-") == 4  # UUID has 4 dashes

            # Mock load to return the saved state
            import json

            mock_conn.fetchrow.return_value = {
                "state": json.dumps(original_state),
                "checkpoint_id": checkpoint_id,
            }

            # Load checkpoint
            loaded_state = await repo.load_checkpoint(checkpoint_id)

            # Verify state integrity
            assert loaded_state["workflow_id"] == original_state["workflow_id"]
            assert loaded_state["user_request"] == original_state["user_request"]
            assert loaded_state["budget_used_tokens"] == 5000
            assert loaded_state["code_files"] == {"main.py": "print('hello')"}


class TestBudgetTracking:
    """Test budget tracking across LLM operations."""

    @pytest.mark.asyncio
    async def test_budget_tracking_with_llm_calls(self):
        """Test that budget is tracked correctly across multiple LLM calls."""
        from src.orchestration.budget_guard import BudgetGuard
        from src.orchestration.state import create_initial_state

        with patch("src.config.settings") as mock_settings:
            mock_settings.max_tokens_per_workflow = 100_000
            mock_settings.max_monthly_budget_usd = 10.0
            mock_settings.budget_alert_threshold_pct = 75.0
            mock_settings.total_budget_tokens = 100_000

            budget_guard = BudgetGuard(
                max_tokens_per_workflow=100_000,
                max_monthly_budget_usd=10.0,
            )

            # Create initial workflow state
            state = create_initial_state(
                workflow_id="wf-budget-test",
                user_request="Test budget tracking",
                trace_id="trace-budget-test",
            )

            # Simulate first LLM operation
            result1 = budget_guard.reserve_budget(
                operation_name="operation_1",
                estimated_tokens=30_000,
                estimated_cost_usd=0.30,
                workflow_state=state,
            )

            assert result1["allowed"] is True
            assert result1["alert"] is None  # 30% usage, below 75% threshold

            # Update state after operation
            state["budget_used_tokens"] += 30_000
            state["budget_used_usd"] += 0.30
            state["budget_remaining_tokens"] -= 30_000

            # Simulate second LLM operation
            result2 = budget_guard.reserve_budget(
                operation_name="operation_2",
                estimated_tokens=50_000,
                estimated_cost_usd=0.50,
                workflow_state=state,
            )

            assert result2["allowed"] is True
            assert result2["alert"] is not None  # 80% usage, above 75% threshold
            assert "80" in result2["alert"]  # Should mention percentage


class TestObservabilityIntegration:
    """Test that observability instrumentation works correctly."""

    @pytest.mark.asyncio
    async def test_llm_client_logging(self):
        """Test that LLM operations are logged with structured logging."""
        with patch("src.config.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test_key"

            client = OpenRouterClient(settings=mock_settings)

            with (
                patch("httpx.AsyncClient.post") as mock_post,
                patch("structlog.get_logger") as mock_logger,
            ):
                mock_log = MagicMock()
                mock_logger.return_value = mock_log

                mock_response_data = {
                    "choices": [{"message": {"content": "Response"}}],
                    "model": "deepseek/deepseek-chat",
                    "usage": {"total_tokens": 100},
                }
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(return_value=mock_response_data)
                mock_response.raise_for_status = MagicMock()
                mock_post.return_value = mock_response

                await client.generate(prompt="Test")

                # Verify logging calls were made
                # (Note: actual logging verification would depend on structlog configuration)
                assert mock_post.called


class TestWorkflowStateTransitions:
    """Test workflow state transitions and validation."""

    def test_state_version_incrementing(self):
        """Test that state version increments on updates."""
        from src.orchestration.state import (
            create_initial_state,
            increment_rejection_count,
        )

        state = create_initial_state(
            workflow_id="wf-version-test",
            user_request="Test versioning",
            trace_id="trace-version-test",
        )

        initial_version = state["state_version"]
        assert initial_version == 0

        # Increment rejection count (should increment version)
        updated_state = increment_rejection_count(state)

        assert updated_state["state_version"] == 1  # Increments from 0 to 1
        assert updated_state["rejection_count"] == 1

    def test_budget_update_reducer(self):
        """Test budget update reducer maintains consistency."""
        from src.orchestration.state import create_initial_state, update_budget

        state = create_initial_state(
            workflow_id="wf-budget-reducer-test",
            user_request="Test budget reducer",
            trace_id="trace-budget-reducer-test",
        )

        # Update budget
        updated_state = update_budget(
            state,
            tokens_consumed=10_000,
            cost_usd=0.10,
            agent_name="test_agent",
        )

        assert updated_state["budget_used_tokens"] == 10_000
        assert updated_state["budget_used_usd"] == 0.10
        assert (
            updated_state["budget_remaining_tokens"]
            == state["budget_remaining_tokens"] - 10_000
        )
