"""Unit tests for Chainlit application.

Tests for Chainlit UI components including message handling,
workflow state management, and user interactions.

NOTE: Skipping due to Pydantic/Chainlit compatibility issue.
See: https://errors.pydantic.dev/2.12/u/class-not-fully-defined
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Skip entire module due to Pydantic/Chainlit compatibility issue
pytestmark = pytest.mark.skip(
    reason="Chainlit/Pydantic compatibility issue - CodeSettings not fully defined"
)

# Conditional imports to prevent collection errors
try:
    from src.chainlit_app.app import (
        _handle_approval,
        _handle_budget_query,
        _handle_check_status,
        _handle_generic_request,
        _handle_start_workflow,
        on_chat_start,
        on_message,
    )
    from src.chainlit_app.callbacks import ChainlitCallback, create_chainlit_callbacks
except Exception:
    # If imports fail, define dummy values to prevent collection errors
    _handle_approval = None
    _handle_budget_query = None
    _handle_check_status = None
    _handle_generic_request = None
    _handle_start_workflow = None
    on_chat_start = None
    on_message = None
    ChainlitCallback = None
    create_chainlit_callbacks = None


class TestChainlitApp:
    """Test suite for Chainlit application."""

    @pytest.mark.asyncio
    async def test_on_chat_start_initializes_session(self) -> None:
        """Test that on_chat_start initializes session state."""
        with patch("chainlit.user_session") as mock_session:
            mock_session.set = MagicMock()

            await on_chat_start()

            # Verify session initialization
            assert mock_session.set.call_count >= 4
            calls = [call[0] for call in mock_session.set.call_args_list]
            assert any("session_id" in str(call) for call in calls)
            assert any("workflow_id" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_on_message_routes_start_command(self) -> None:
        """Test that on_message routes 'start' command correctly."""
        mock_message = MagicMock()
        mock_message.content = "start workflow"

        with patch("chainlit.user_session") as mock_session:
            mock_session.get = MagicMock(return_value="test_session")
            with patch(
                "src.chainlit_app.app._handle_start_workflow",
                new_callable=AsyncMock,
            ) as mock_handler:
                await on_message(mock_message)
                mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_message_routes_status_command(self) -> None:
        """Test that on_message routes 'status' command correctly."""
        mock_message = MagicMock()
        mock_message.content = "check status"

        with patch("chainlit.user_session") as mock_session:
            mock_session.get = MagicMock(return_value="test_session")
            with patch(
                "src.chainlit_app.app._handle_check_status",
                new_callable=AsyncMock,
            ) as mock_handler:
                await on_message(mock_message)
                mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_message_routes_approval_command(self) -> None:
        """Test that on_message routes 'approve' command correctly."""
        mock_message = MagicMock()
        mock_message.content = "approve"

        with patch("chainlit.user_session") as mock_session:
            mock_session.get = MagicMock(return_value="test_session")
            with patch(
                "src.chainlit_app.app._handle_approval",
                new_callable=AsyncMock,
            ) as mock_handler:
                await on_message(mock_message)
                mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_message_routes_budget_command(self) -> None:
        """Test that on_message routes 'budget' command correctly."""
        mock_message = MagicMock()
        mock_message.content = "show budget"

        with patch("chainlit.user_session") as mock_session:
            mock_session.get = MagicMock(return_value="test_session")
            with patch(
                "src.chainlit_app.app._handle_budget_query",
                new_callable=AsyncMock,
            ) as mock_handler:
                await on_message(mock_message)
                mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_start_workflow_creates_workflow_id(self) -> None:
        """Test that _handle_start_workflow creates workflow ID."""
        mock_message = MagicMock()

        with patch("chainlit.user_session") as mock_session:
            mock_session.get = MagicMock(return_value="test_session")
            mock_session.set = MagicMock()
            with patch("chainlit.AskUserMessage") as mock_ask:
                mock_response = AsyncMock()
                mock_response.content = "Create a test endpoint"
                mock_ask.return_value.send = AsyncMock(return_value=mock_response)
                with patch("chainlit.Message") as mock_msg:
                    mock_msg.return_value.send = AsyncMock()
                    with patch(
                        "src.chainlit_app.app._simulate_workflow_progress",
                        new_callable=AsyncMock,
                    ):
                        await _handle_start_workflow(mock_message)

                        # Verify workflow_id was set
                        calls = [call[0][0] for call in mock_session.set.call_args_list]
                        assert "workflow_id" in calls

    @pytest.mark.asyncio
    async def test_handle_check_status_without_workflow(self) -> None:
        """Test that _handle_check_status handles missing workflow."""
        mock_message = MagicMock()

        with patch("chainlit.user_session") as mock_session:
            mock_session.get = MagicMock(return_value=None)
            with patch("chainlit.Message") as mock_msg:
                mock_msg.return_value.send = AsyncMock()
                await _handle_check_status(mock_message)
                mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_approval_records_decision(self) -> None:
        """Test that _handle_approval records approval decision."""
        mock_message = MagicMock()
        mock_message.content = "approve - looks good"

        with patch("chainlit.user_session") as mock_session:
            mock_session.get = MagicMock(return_value="test_workflow_id")
            with patch("chainlit.Message") as mock_msg:
                mock_msg.return_value.send = AsyncMock()
                await _handle_approval(mock_message)
                mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_budget_query_displays_budget(self) -> None:
        """Test that _handle_budget_query displays budget info."""
        mock_message = MagicMock()

        with patch("chainlit.user_session") as mock_session:
            mock_session.get = MagicMock(side_effect=[0.0, 20.0])
            with patch("chainlit.Message") as mock_msg:
                mock_msg.return_value.send = AsyncMock()
                await _handle_budget_query(mock_message)
                mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_generic_request_shows_help(self) -> None:
        """Test that _handle_generic_request shows help."""
        mock_message = MagicMock()
        mock_message.content = "what can I do?"

        with patch("chainlit.Message") as mock_msg:
            mock_msg.return_value.send = AsyncMock()
            await _handle_generic_request(mock_message)
            mock_msg.assert_called_once()


class TestChainlitCallbacks:
    """Test suite for LangGraph callbacks."""

    def test_chainlit_callback_initialization(self) -> None:
        """Test ChainlitCallback initialization."""
        callback = ChainlitCallback("test_workflow", "test_user")

        assert callback.workflow_id == "test_workflow"
        assert callback.user_id == "test_user"
        assert callback.message_queue == []

    @pytest.mark.asyncio
    async def test_on_node_start_sends_message(self) -> None:
        """Test that on_node_start sends status message."""
        callback = ChainlitCallback("test_workflow", "test_user")

        with patch("chainlit.Message") as mock_msg:
            mock_msg.return_value.send = AsyncMock()
            await callback.on_node_start(
                "tier_1_planning",
                {  # type: ignore[arg-type]
                    "workflow_id": "test",
                    "user_request": "test",
                    "trace_id": "test",
                    "current_phase": "test",
                    "current_task": "test",
                    "current_agent": "test",
                    "rejection_count": 0,
                    "state_version": 1,
                    "requirements": "",
                    "architecture": "",
                    "tasks": "",
                    "dependencies": "",
                    "infrastructure": "",
                    "observability": "",
                    "code_files": {},
                    "test_files": {},
                    "partial_artifacts": {},
                    "validation_report": "",
                    "deviation_log": "",
                    "compliance_log": "",
                    "quality_report": "",
                    "security_report": "",
                    "acceptance_report": "",
                    "budget_used_tokens": 0,
                    "budget_used_usd": 0.0,
                    "budget_remaining_tokens": 0,
                    "budget_remaining_usd": 0.0,
                    "agent_token_usage": {},
                    "quality_gates_passed": [],
                    "blocking_issues": [],
                    "awaiting_human_approval": False,
                    "approval_gate": None,
                    "approval_timeout": None,
                    "routing_decision": None,
                    "escalation_flag": False,
                    "created_at": "2026-01-30T08:56:51.284Z",
                    "updated_at": "2026-01-30T08:56:51.284Z",
                },
            )
            mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_node_end_sends_completion_message(self) -> None:
        """Test that on_node_end sends completion message."""
        callback = ChainlitCallback("test_workflow", "test_user")

        with patch("chainlit.Message") as mock_msg:
            mock_msg.return_value.send = AsyncMock()
            await callback.on_node_end("tier_1_planning", {}, {"status": "ok"})
            mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_rejection_sends_rejection_message(self) -> None:
        """Test that on_rejection sends rejection message."""
        callback = ChainlitCallback("test_workflow", "test_user")

        with patch("chainlit.Message") as mock_msg:
            mock_msg.return_value.send = AsyncMock()
            await callback.on_rejection("tier_4_validator", "Invalid output", {})
            mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_approval_sends_approval_message(self) -> None:
        """Test that on_approval sends approval message."""
        callback = ChainlitCallback("test_workflow", "test_user")

        with patch("chainlit.Message") as mock_msg:
            mock_msg.return_value.send = AsyncMock()
            await callback.on_approval("tier_4_validator", {})
            mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_human_gate_prompts_user(self) -> None:
        """Test that on_human_gate prompts for user decision."""
        callback = ChainlitCallback("test_workflow", "test_user")

        with patch("chainlit.Message") as mock_msg:
            mock_msg.return_value.send = AsyncMock()
            await callback.on_human_gate(
                "approval_gate",
                {},
                "Approve architecture design?",
            )
            mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_budget_warning_sends_alert(self) -> None:
        """Test that on_budget_warning sends alert."""
        callback = ChainlitCallback("test_workflow", "test_user")

        with patch("chainlit.Message") as mock_msg:
            mock_msg.return_value.send = AsyncMock()
            await callback.on_budget_warning(15.0, 20.0, 75.0)
            mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_budget_exceeded_sends_critical_alert(self) -> None:
        """Test that on_budget_exceeded sends critical alert."""
        callback = ChainlitCallback("test_workflow", "test_user")

        with patch("chainlit.Message") as mock_msg:
            mock_msg.return_value.send = AsyncMock()
            await callback.on_budget_exceeded(21.0, 20.0)
            mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_error_sends_error_message(self) -> None:
        """Test that on_error sends error message."""
        callback = ChainlitCallback("test_workflow", "test_user")

        with patch("chainlit.Message") as mock_msg:
            mock_msg.return_value.send = AsyncMock()
            await callback.on_error(
                "WorkflowError",
                "Failed to execute tier",
                "tier_3_engineer",
            )
            mock_msg.assert_called_once()

    def test_extract_tier_name_from_node_name(self) -> None:
        """Test tier name extraction from node name."""
        callback = ChainlitCallback("test_workflow", "test_user")

        assert "Tier 0" in callback._extract_tier_name("tier_0_control")
        assert "Tier 1" in callback._extract_tier_name("tier_1_planning")
        assert "Tier 3" in callback._extract_tier_name("tier_3_development")

    def test_format_output_from_dict(self) -> None:
        """Test output formatting from dictionary."""
        callback = ChainlitCallback("test_workflow", "test_user")

        output = {"files_created": ["file1.py", "file2.py"]}
        formatted = callback._format_output(output)
        assert "2 files created" in formatted

    def test_format_output_from_string(self) -> None:
        """Test output formatting from string."""
        callback = ChainlitCallback("test_workflow", "test_user")

        output = "Workflow completed successfully"
        formatted = callback._format_output(output)
        assert "Workflow completed" in formatted

    def test_create_chainlit_callbacks_returns_dict(self) -> None:
        """Test that create_chainlit_callbacks returns callback dict."""
        callbacks = create_chainlit_callbacks("test_workflow", "test_user")

        assert isinstance(callbacks, dict)
        assert "on_node_start" in callbacks
        assert "on_node_end" in callbacks
        assert "on_rejection" in callbacks
        assert "on_approval" in callbacks
        assert "on_human_gate" in callbacks
        assert "on_budget_warning" in callbacks
        assert "on_budget_exceeded" in callbacks
        assert "on_error" in callbacks
