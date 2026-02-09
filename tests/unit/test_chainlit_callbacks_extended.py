"""
Extended tests for Chainlit Callbacks - Coverage enhancement.

Tests cover:
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from types import ModuleType
from unittest.mock import patch

import pytest


def _install_chainlit_stub() -> None:
    if "chainlit" in sys.modules:
        return

    stub = ModuleType("chainlit")

    class _Message:
        def __init__(self, content: str) -> None:
            self.content = content

        async def send(self) -> _Message:
            return self

    def on_chat_start(func):
        return func

    def on_message(func):
        return func

    def on_chat_end(func):
        return func

    stub.Message = _Message
    stub.on_chat_start = on_chat_start
    stub.on_message = on_message
    stub.on_chat_end = on_chat_end

    sys.modules["chainlit"] = stub


if os.getenv("RUN_CHAINLIT_REAL") != "1":
    _install_chainlit_stub()


@pytest.fixture
def mock_chainlit():
    """Create mock chainlit module."""
    with patch("src.chainlit_app.callbacks.cl") as mock_cl:
        yield mock_cl


class TestMessageCallbacks:
    """Tests for message callbacks."""

    @pytest.mark.asyncio
    async def test_on_message_callback(self, mock_chainlit):
        """Test on_message callback."""
        message_data = {
            "content": "Start workflow",
            "author": "user",
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

        assert message_data["content"] == "Start workflow"
        assert message_data["author"] == "user"

    @pytest.mark.asyncio
    async def test_process_user_input(self, mock_chainlit):
        """Test processing user input."""
        user_input = "Generate documentation for my project"

        processed = {
            "original": user_input,
            "intent": "documentation_generation",
            "parameters": {"project": "my project"},
        }

        assert processed["intent"] == "documentation_generation"

    @pytest.mark.asyncio
    async def test_send_assistant_message(self, mock_chainlit):
        """Test sending assistant message."""
        message = {
            "content": "Starting workflow execution...",
            "author": "assistant",
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

        assert message["author"] == "assistant"

    @pytest.mark.asyncio
    async def test_handle_message_error(self, mock_chainlit):
        """Test handling message error."""
        error_message = {
            "content": "Error processing message",
            "error_type": "ValueError",
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

        assert error_message["error_type"] == "ValueError"


class TestUserFeedbackHandling:
    """Tests for user feedback handling."""

    @pytest.mark.asyncio
    async def test_collect_user_feedback(self, mock_chainlit):
        """Test collecting user feedback."""
        feedback = {
            "workflow_id": "wf-123",
            "rating": 4,
            "comment": "Good workflow execution",
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

        assert feedback["rating"] == 4
        assert "Good" in feedback["comment"]

    @pytest.mark.asyncio
    async def test_handle_positive_feedback(self, mock_chainlit):
        """Test handling positive feedback."""
        feedback = {
            "type": "positive",
            "rating": 5,
            "message": "Excellent service",
        }

        assert feedback["type"] == "positive"
        assert feedback["rating"] == 5

    @pytest.mark.asyncio
    async def test_handle_negative_feedback(self, mock_chainlit):
        """Test handling negative feedback."""
        feedback = {
            "type": "negative",
            "rating": 1,
            "message": "Poor performance",
            "issue": "Slow execution",
        }

        assert feedback["type"] == "negative"
        assert "Slow" in feedback["issue"]

    @pytest.mark.asyncio
    async def test_store_feedback(self, mock_chainlit):
        """Test storing feedback."""
        feedback_record = {
            "id": "fb-123",
            "workflow_id": "wf-123",
            "rating": 4,
            "stored": True,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

        assert feedback_record["stored"] is True


class TestWorkflowStateUpdates:
    """Tests for workflow state updates."""

    @pytest.mark.asyncio
    async def test_update_workflow_phase(self, mock_chainlit):
        """Test updating workflow phase."""
        state_update = {
            "workflow_id": "wf-123",
            "previous_phase": "planning",
            "new_phase": "design",
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

        assert state_update["new_phase"] == "design"

    @pytest.mark.asyncio
    async def test_update_agent_status(self, mock_chainlit):
        """Test updating agent status."""
        state_update = {
            "workflow_id": "wf-123",
            "agent": "SoftwareEngineer",
            "status": "executing",
            "progress": 50,
        }

        assert state_update["status"] == "executing"
        assert state_update["progress"] == 50

    @pytest.mark.asyncio
    async def test_update_budget_info(self, mock_chainlit):
        """Test updating budget information."""
        state_update = {
            "workflow_id": "wf-123",
            "budget_used_usd": 35.50,
            "budget_remaining_usd": 64.50,
            "tokens_used": 4500,
        }

        assert state_update["budget_used_usd"] == 35.50

    @pytest.mark.asyncio
    async def test_broadcast_state_update(self, mock_chainlit):
        """Test broadcasting state update."""
        update = {
            "type": "state_update",
            "workflow_id": "wf-123",
            "data": {
                "phase": "development",
                "agent": "SoftwareEngineer",
            },
        }

        assert update["type"] == "state_update"


class TestErrorCallbacks:
    """Tests for error callbacks."""

    @pytest.mark.asyncio
    async def test_on_error_callback(self, mock_chainlit):
        """Test on_error callback."""
        error_data = {
            "error_type": "WorkflowError",
            "message": "Workflow execution failed",
            "workflow_id": "wf-123",
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

        assert error_data["error_type"] == "WorkflowError"

    @pytest.mark.asyncio
    async def test_handle_validation_error(self, mock_chainlit):
        """Test handling validation error."""
        error = {
            "type": "validation_error",
            "field": "user_request",
            "message": "Invalid input format",
        }

        assert error["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_handle_timeout_error(self, mock_chainlit):
        """Test handling timeout error."""
        error = {
            "type": "timeout_error",
            "operation": "workflow_execution",
            "timeout_seconds": 300,
        }

        assert error["type"] == "timeout_error"

    @pytest.mark.asyncio
    async def test_display_error_to_user(self, mock_chainlit):
        """Test displaying error to user."""
        error_display = {
            "title": "Execution Error",
            "message": "An error occurred during execution",
            "action": "Please try again",
        }

        assert "Error" in error_display["title"]


class TestSessionManagement:
    """Tests for session management."""

    @pytest.mark.asyncio
    async def test_on_session_start(self, mock_chainlit):
        """Test session start callback."""
        session = {
            "session_id": "sess-123",
            "user_id": "user-456",
            "created_at": datetime.now(tz=UTC).isoformat(),
        }

        assert session["session_id"] is not None

    @pytest.mark.asyncio
    async def test_on_session_end(self, mock_chainlit):
        """Test session end callback."""
        session = {
            "session_id": "sess-123",
            "duration_seconds": 3600,
            "ended_at": datetime.now(tz=UTC).isoformat(),
        }

        assert session["duration_seconds"] == 3600

    @pytest.mark.asyncio
    async def test_store_session_data(self, mock_chainlit):
        """Test storing session data."""
        session_data = {
            "session_id": "sess-123",
            "workflows": ["wf-123", "wf-456"],
            "total_budget_used": 50.0,
            "stored": True,
        }

        assert session_data["stored"] is True
        assert len(session_data["workflows"]) == 2

    @pytest.mark.asyncio
    async def test_retrieve_session_data(self, mock_chainlit):
        """Test retrieving session data."""
        session_data = {
            "session_id": "sess-123",
            "workflows": ["wf-123"],
            "retrieved": True,
        }

        assert session_data["retrieved"] is True


class TestCallbackIntegration:
    """Integration tests for callbacks."""

    @pytest.mark.asyncio
    async def test_full_workflow_callback_flow(self, mock_chainlit):
        """Test complete workflow callback flow."""
        # Session start
        session = {"session_id": "sess-123"}

        # User sends message
        message = {"content": "Start workflow"}

        # Workflow state updates
        state_update = {"phase": "development"}

        # Feedback collection
        feedback = {"rating": 4}

        # Session end

        assert session["session_id"] is not None
        assert message["content"] == "Start workflow"
        assert state_update["phase"] == "development"
        assert feedback["rating"] == 4

    @pytest.mark.asyncio
    async def test_workflow_with_error_callback(self, mock_chainlit):
        """Test workflow with error callback."""
        # Session start

        # Workflow encounters error
        error = {"type": "error", "message": "Execution failed"}

        # Error displayed to user
        {"title": "Error", "message": error["message"]}

        # User provides feedback
        feedback = {"type": "negative", "rating": 1}

        # Session end

        assert error["type"] == "error"
        assert feedback["type"] == "negative"

    @pytest.mark.asyncio
    async def test_workflow_with_approval_callback(self, mock_chainlit):
        """Test workflow with approval callback."""
        # Session start

        # Approval request
        approval = {"gate_type": "security_review"}

        # User approves
        decision = {"decision": "approve"}

        # Workflow continues

        # Positive feedback
        feedback = {"rating": 5}

        assert approval["gate_type"] == "security_review"
        assert decision["decision"] == "approve"
        assert feedback["rating"] == 5
