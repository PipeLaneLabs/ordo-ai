"""Unit tests for CheckpointManager (LangGraph checkpointer)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Settings
from src.orchestration.checkpoints import CheckpointManager


@pytest.fixture()
def mock_settings():
    """Create minimal settings mock."""
    settings = MagicMock(spec=Settings)
    return settings


@pytest.fixture()
def repository_mock():
    """Create repository mock with async methods."""
    repo = MagicMock()
    repo.connect = AsyncMock()
    repo.disconnect = AsyncMock()
    repo.load_checkpoint = AsyncMock()
    repo.save_checkpoint = AsyncMock(return_value="ckpt-123")
    repo.save_workflow_metadata = AsyncMock()
    repo.log_audit_event = AsyncMock()
    repo.list_checkpoints = AsyncMock()
    repo.cleanup_old_checkpoints = AsyncMock(return_value=2)
    return repo


@pytest.fixture()
def manager(mock_settings, repository_mock):
    """Create CheckpointManager with mocked repository."""
    with patch(
        "src.orchestration.checkpoints.CheckpointRepository",
        return_value=repository_mock,
    ):
        return CheckpointManager(settings=mock_settings, retention_hours=12)


@pytest.mark.asyncio
async def test_aget_returns_none_without_checkpoint_id(manager, repository_mock):
    """Return None when config lacks checkpoint_id."""
    result = await manager.aget({})

    assert result is None
    repository_mock.load_checkpoint.assert_not_called()


@pytest.mark.asyncio
async def test_aget_returns_checkpoint(manager, repository_mock):
    """Return checkpoint when repository has data."""
    state = {
        "workflow_id": "wf-1",
        "state_version": 3,
        "current_phase": "planning",
    }
    repository_mock.load_checkpoint.return_value = state

    result = await manager.aget({"checkpoint_id": "ckpt-1"})

    assert result is not None
    assert result["id"] == "ckpt-1"
    assert result["v"] == 3
    assert result["channel_values"]["state"]["workflow_id"] == "wf-1"


@pytest.mark.asyncio
async def test_aput_saves_checkpoint_and_metadata(manager, repository_mock):
    """Save checkpoint, metadata, and audit event."""
    state = {
        "workflow_id": "wf-1",
        "user_request": "Do work",
        "current_phase": "planning",
        "current_agent": "AgentX",
        "budget_used_usd": 1.5,
        "rejection_count": 0,
    }
    checkpoint = {"v": 2, "channel_values": {"state": state}}

    updated = await manager.aput({"workflow_id": "wf-1"}, checkpoint, {}, {})

    assert updated["checkpoint_id"] == "ckpt-123"
    repository_mock.save_checkpoint.assert_called_once()
    repository_mock.save_workflow_metadata.assert_called_once()
    repository_mock.log_audit_event.assert_called_once()


@pytest.mark.asyncio
async def test_alist_yields_checkpoints_and_skips_corrupt(manager, repository_mock):
    """Yield valid checkpoints and skip corrupted entries."""
    repository_mock.list_checkpoints.return_value = [
        {"checkpoint_id": "ckpt-1"},
        {"checkpoint_id": "ckpt-2"},
    ]
    repository_mock.load_checkpoint.side_effect = [
        {"workflow_id": "wf-1", "state_version": 1},
        RuntimeError("bad checkpoint"),
    ]

    with patch("src.orchestration.checkpoints.logger.warning") as mock_warn:
        results = [
            item async for item in manager.alist({"workflow_id": "wf-1"}, limit=5)
        ]

    assert len(results) == 1
    assert results[0].checkpoint["id"] == "ckpt-1"
    mock_warn.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_old_checkpoints(manager, repository_mock):
    """Cleanup returns repository count."""
    result = await manager.cleanup_old_checkpoints()

    assert result == 2
    repository_mock.cleanup_old_checkpoints.assert_called_once_with(retention_hours=12)
