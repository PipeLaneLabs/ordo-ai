"""Unit tests for Chainlit app with a fake Chainlit module."""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


class _FakeUserSession:
    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def set(self, key: str, value: object) -> None:
        self._data[key] = value

    def get(self, key: str, default: object | None = None) -> object | None:
        return self._data.get(key, default)


class _FakeMessage:
    def __init__(self, content: str, store: list[str]) -> None:
        self.content = content
        self._store = store

    async def send(self) -> _FakeMessage:
        self._store.append(self.content)
        return self


def _make_fake_chainlit() -> SimpleNamespace:
    sent_messages: list[str] = []
    sleep_calls: list[float] = []
    ask_response = {"value": "Build a sample API"}

    class _AskUserMessage:
        def __init__(self, content: str, timeout: int | None = None) -> None:
            self.content = ask_response["value"]
            self.timeout = timeout

        async def send(self) -> _AskUserMessage | None:
            if self.content is None:
                return None
            return self

    async def sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    def on_chat_start(func):
        return func

    def on_message(func):
        return func

    def on_chat_end(func):
        return func

    return SimpleNamespace(
        user_session=_FakeUserSession(),
        Message=lambda content: _FakeMessage(content, sent_messages),
        AskUserMessage=_AskUserMessage,
        on_chat_start=on_chat_start,
        on_message=on_message,
        on_chat_end=on_chat_end,
        sleep=sleep,
        sent_messages=sent_messages,
        sleep_calls=sleep_calls,
        ask_response=ask_response,
    )


def _import_app(fake_cl: SimpleNamespace) -> object:
    sys.modules.pop("src.chainlit_app.app", None)
    sys.modules["chainlit"] = fake_cl
    return importlib.import_module("src.chainlit_app.app")


@pytest.mark.asyncio
async def test_on_chat_start_sends_welcome() -> None:
    fake_cl = _make_fake_chainlit()
    app = _import_app(fake_cl)

    await app.on_chat_start()

    assert fake_cl.user_session.get("session_id") is not None
    assert len(fake_cl.sent_messages) == 1
    assert "Welcome" in fake_cl.sent_messages[0]


@pytest.mark.asyncio
async def test_on_message_routes_start() -> None:
    fake_cl = _make_fake_chainlit()
    app = _import_app(fake_cl)

    fake_cl.user_session.set("session_id", "sess-1")
    message = SimpleNamespace(content="start workflow")

    with patch.object(app, "_handle_start_workflow", new=AsyncMock()) as handler:
        await app.on_message(message)

    handler.assert_called_once()


@pytest.mark.asyncio
async def test_handle_start_workflow_cancelled() -> None:
    fake_cl = _make_fake_chainlit()
    fake_cl.ask_response["value"] = None
    app = _import_app(fake_cl)

    await app._handle_start_workflow(SimpleNamespace(content="start"))

    assert "Workflow cancelled" in "".join(fake_cl.sent_messages)


@pytest.mark.asyncio
async def test_handle_start_workflow_success_sets_workflow_id() -> None:
    fake_cl = _make_fake_chainlit()
    app = _import_app(fake_cl)

    with patch.object(app, "_simulate_workflow_progress", new=AsyncMock()):
        await app._handle_start_workflow(SimpleNamespace(content="start"))

    workflow_id = fake_cl.user_session.get("workflow_id")
    assert workflow_id is not None


@pytest.mark.asyncio
async def test_handle_check_status_no_workflow() -> None:
    fake_cl = _make_fake_chainlit()
    app = _import_app(fake_cl)

    await app._handle_check_status(SimpleNamespace(content="status"))

    assert "No active workflow" in "".join(fake_cl.sent_messages)


@pytest.mark.asyncio
async def test_handle_budget_query_sends_summary() -> None:
    fake_cl = _make_fake_chainlit()
    app = _import_app(fake_cl)

    fake_cl.user_session.set("budget_used", 10.0)
    fake_cl.user_session.set("budget_limit", 40.0)

    await app._handle_budget_query(SimpleNamespace(content="budget"))

    assert "Budget Summary" in "".join(fake_cl.sent_messages)


@pytest.mark.asyncio
async def test_handle_approval_records_decision() -> None:
    fake_cl = _make_fake_chainlit()
    app = _import_app(fake_cl)

    fake_cl.user_session.set("workflow_id", "wf-1")

    await app._handle_approval(SimpleNamespace(content="approve"))

    assert "Approval Recorded" in "".join(fake_cl.sent_messages)


@pytest.mark.asyncio
async def test_handle_generic_request_shows_help() -> None:
    fake_cl = _make_fake_chainlit()
    app = _import_app(fake_cl)

    await app._handle_generic_request(SimpleNamespace(content="help"))

    assert "Available Commands" in "".join(fake_cl.sent_messages)


@pytest.mark.asyncio
async def test_simulate_workflow_progress_runs() -> None:
    fake_cl = _make_fake_chainlit()
    app = _import_app(fake_cl)

    await app._simulate_workflow_progress("wf-123")

    assert fake_cl.user_session.get("current_phase") == "tier_5_integration"
    assert len(fake_cl.sent_messages) >= 2
    assert fake_cl.sleep_calls


@pytest.mark.asyncio
async def test_on_chat_end_runs() -> None:
    fake_cl = _make_fake_chainlit()
    app = _import_app(fake_cl)

    fake_cl.user_session.set("session_id", "sess-1")
    fake_cl.user_session.set("workflow_id", "wf-1")

    await app.on_chat_end()
