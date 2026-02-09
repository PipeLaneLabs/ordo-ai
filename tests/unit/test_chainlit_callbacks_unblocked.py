"""Unit tests for Chainlit callbacks with a fake Chainlit module."""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

import pytest


class _FakeMessage:
    def __init__(self, content: str, store: list[str]) -> None:
        self.content = content
        self._store = store

    async def send(self) -> _FakeMessage:
        self._store.append(self.content)
        return self


def _make_fake_chainlit() -> SimpleNamespace:
    sent_messages: list[str] = []

    def on_chat_start(func):
        return func

    def on_message(func):
        return func

    def on_chat_end(func):
        return func

    return SimpleNamespace(
        Message=lambda content: _FakeMessage(content, sent_messages),
        on_chat_start=on_chat_start,
        on_message=on_message,
        on_chat_end=on_chat_end,
        sent_messages=sent_messages,
    )


def _import_callbacks(fake_cl: SimpleNamespace) -> object:
    sys.modules.pop("src.chainlit_app.callbacks", None)
    sys.modules["chainlit"] = fake_cl
    return importlib.import_module("src.chainlit_app.callbacks")


def _sample_state() -> dict:
    return {
        "workflow_id": "wf-1",
        "user_request": "Do work",
        "trace_id": "wf-1",
        "current_phase": "planning",
        "current_task": "task",
        "current_agent": "Agent",
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
    }


@pytest.mark.asyncio
async def test_callbacks_send_messages() -> None:
    fake_cl = _make_fake_chainlit()
    callbacks = _import_callbacks(fake_cl)

    callback = callbacks.ChainlitCallback("wf-1", "user-1")

    await callback.on_node_start("tier_1_planning", _sample_state())
    await callback.on_node_end("tier_1_planning", _sample_state(), {"status": "ok"})
    await callback.on_rejection("tier_3_quality", "Tests failed", _sample_state())
    await callback.on_approval("tier_4_security", _sample_state())
    await callback.on_human_gate("gate-1", _sample_state(), "Approve deployment")
    await callback.on_budget_warning(10.0, 20.0, 50.0)
    await callback.on_budget_exceeded(25.0, 20.0)
    await callback.on_error("ValueError", "Bad input", node_name="tier_2")

    assert fake_cl.sent_messages


def test_extract_tier_name_and_format_output() -> None:
    fake_cl = _make_fake_chainlit()
    callbacks = _import_callbacks(fake_cl)

    callback = callbacks.ChainlitCallback("wf-1", "user-1")

    assert "Tier 2" in callback._extract_tier_name("tier_2_planner")
    assert callback._format_output({"files_created": ["a", "b"]}) == "2 files created"
    assert callback._format_output({"report": "ok"}) == "Report generated"
    assert callback._format_output({"status": "done"}) == "done"
    assert callback._format_output("Some output").startswith("Some")
    assert callback._format_output({"other": 1}) == "Completed"


def test_create_callbacks_factory() -> None:
    fake_cl = _make_fake_chainlit()
    callbacks = _import_callbacks(fake_cl)

    handlers = callbacks.create_chainlit_callbacks("wf-1", "user-1")

    assert "on_node_start" in handlers
    assert callable(handlers["on_node_start"])
