"""Unit tests for Chainlit application.

Tests for Chainlit UI components including message handling,
workflow state management, and user interactions.

NOTE: Skipping due to Pydantic/Chainlit compatibility issue.
See: https://errors.pydantic.dev/2.12/u/class-not-fully-defined
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.orchestration.state import WorkflowState, create_initial_state


def _install_chainlit_stub() -> None:  # noqa: C901
    if "chainlit" in sys.modules:
        return

    stub: Any = ModuleType("chainlit")

    class _UserSession:
        def __init__(self) -> None:
            self._data: dict[str, object] = {}

        def set(self, key: str, value: object) -> None:
            self._data[key] = value

        def get(self, key: str, default: object | None = None) -> object | None:
            return self._data.get(key, default)

    class _Message:
        def __init__(self, content: str) -> None:
            self.content = content

        async def send(self) -> _Message:
            return self

    class _AskUserMessage:
        def __init__(self, content: str, timeout: int | None = None) -> None:
            self.content = content
            self.timeout = timeout

        async def send(self) -> _AskUserMessage:
            return self

    def on_chat_start(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    def on_message(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    def on_chat_end(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    async def sleep(_seconds: float) -> None:
        return None

    stub.user_session = _UserSession()
    stub.Message = _Message
    stub.AskUserMessage = _AskUserMessage
    stub.on_chat_start = on_chat_start
    stub.on_message = on_message
    stub.on_chat_end = on_chat_end
    stub.sleep = sleep

    sys.modules["chainlit"] = stub


if os.getenv("RUN_CHAINLIT_REAL") != "1":
    _install_chainlit_stub()

_handle_approval: Any
_handle_budget_query: Any
_handle_check_status: Any
_handle_generic_request: Any
_handle_start_workflow: Any
on_chat_start: Any
on_message: Any
ChainlitCallback: Any
create_chainlit_callbacks: Any

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
    _handle_approval = None
    _handle_budget_query = None
    _handle_check_status = None
    _handle_generic_request = None
    _handle_start_workflow = None
    on_chat_start = None
    on_message = None
    ChainlitCallback = None
    create_chainlit_callbacks = None


def _make_state() -> WorkflowState:
    state = create_initial_state("test", "test request", "test")
    state["current_phase"] = "planning"
    state["current_task"] = "test"
    state["current_agent"] = "test"
    return state


class TestChainlitApp:
    """Test suite for Chainlit application."""

    @pytest.mark.asyncio
    async def test_on_chat_start_initializes_session(self) -> None:
        """Test that on_chat_start initializes session state."""

        class _FakeMessage:
            def __init__(self, content: str) -> None:
                self.content = content

            async def send(self) -> _FakeMessage:
                return self

        with patch("chainlit.user_session") as mock_session:
            mock_session.set = MagicMock()

            with patch("chainlit.Message", _FakeMessage):
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
            state = _make_state()
            await callback.on_node_start("tier_1_planning", state)
            mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_node_end_sends_completion_message(self) -> None:
        """Test that on_node_end sends completion message."""
        callback = ChainlitCallback("test_workflow", "test_user")

        with patch("chainlit.Message") as mock_msg:
            mock_msg.return_value.send = AsyncMock()
            state = _make_state()
            await callback.on_node_end("tier_1_planning", state, {"status": "ok"})
            mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_rejection_sends_rejection_message(self) -> None:
        """Test that on_rejection sends rejection message."""
        callback = ChainlitCallback("test_workflow", "test_user")

        with patch("chainlit.Message") as mock_msg:
            mock_msg.return_value.send = AsyncMock()
            state = _make_state()
            await callback.on_rejection("tier_4_validator", "Invalid output", state)
            mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_approval_sends_approval_message(self) -> None:
        """Test that on_approval sends approval message."""
        callback = ChainlitCallback("test_workflow", "test_user")

        with patch("chainlit.Message") as mock_msg:
            mock_msg.return_value.send = AsyncMock()
            state = _make_state()
            await callback.on_approval("tier_4_validator", state)
            mock_msg.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_human_gate_prompts_user(self) -> None:
        """Test that on_human_gate prompts for user decision."""
        callback = ChainlitCallback("test_workflow", "test_user")

        with patch("chainlit.Message") as mock_msg:
            mock_msg.return_value.send = AsyncMock()
            state = _make_state()
            await callback.on_human_gate(
                "approval_gate",
                state,
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
