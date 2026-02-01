"""Unit tests for CheckpointRepository - PostgreSQL checkpoint persistence."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.exceptions import CheckpointNotFoundError, DatabaseConnectionError
from src.storage.checkpoint_repository import CheckpointRepository


class TestCheckpointRepository:
    """Test suite for CheckpointRepository."""

    @pytest_asyncio.fixture
    async def repository(self):
        """Create repository instance with mocked connection pool."""
        with patch("src.config.settings") as mock_settings:
            mock_settings.postgres_host = "localhost"
            mock_settings.postgres_port = 5432
            mock_settings.postgres_db = "test_db"
            mock_settings.postgres_user = "test_user"
            mock_settings.postgres_url = (
                "postgresql://test_user:test_pass@localhost:5432/test_db"
            )

            repo = CheckpointRepository(settings=mock_settings)

            # Mock the connection pool with proper async context manager
            mock_pool = MagicMock()
            mock_pool.close = AsyncMock()  # Mock async close method
            repo.pool = mock_pool

            yield repo

            # Cleanup
            if repo.pool:
                await repo.disconnect()

    def _mock_pool_acquire(self, mock_conn):
        """Helper to create proper async context manager mock for pool.acquire()."""
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        return mock_context

    @pytest.mark.asyncio
    async def test_save_checkpoint_success(self, repository):
        """Test successful checkpoint save."""
        mock_conn = AsyncMock()
        repository.pool.acquire = MagicMock(
            return_value=self._mock_pool_acquire(mock_conn)
        )

        workflow_state = {
            "workflow_id": "wf-123",
            "user_request": "Test request",
            "state_version": 1,
            "current_phase": "development",
        }

        # Test auto-generated checkpoint ID (UUID)
        checkpoint_id = await repository.save_checkpoint(
            workflow_id="wf-123", state=workflow_state
        )

        # Verify it's a valid UUID-like string
        assert len(checkpoint_id) == 36  # UUID format
        assert checkpoint_id.count("-") == 4  # UUID has 4 dashes
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_checkpoint_database_error(self, repository):
        """Test checkpoint save with database error."""
        import asyncpg

        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = asyncpg.PostgresError("Connection lost")
        repository.pool.acquire = MagicMock(
            return_value=self._mock_pool_acquire(mock_conn)
        )

        workflow_state = {"workflow_id": "wf-123", "state_version": 1}

        with pytest.raises(DatabaseConnectionError) as exc_info:
            await repository.save_checkpoint(workflow_id="wf-123", state=workflow_state)

        assert "save_checkpoint" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_load_checkpoint_success(self, repository):
        """Test successful checkpoint load."""
        mock_conn = AsyncMock()
        mock_row = {
            "state": json.dumps(
                {
                    "workflow_id": "wf-123",
                    "user_request": "Test",
                    "state_version": 1,
                }
            ),
            "checkpoint_id": "ckpt-123",
            "created_at": datetime.now(UTC),
        }
        mock_conn.fetchrow.return_value = mock_row
        repository.pool.acquire = MagicMock(
            return_value=self._mock_pool_acquire(mock_conn)
        )

        state = await repository.load_checkpoint("ckpt-123")

        assert state["workflow_id"] == "wf-123"
        assert state["user_request"] == "Test"
        mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_checkpoint_not_found(self, repository):
        """Test loading non-existent checkpoint."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None  # No checkpoint found
        repository.pool.acquire = MagicMock(
            return_value=self._mock_pool_acquire(mock_conn)
        )

        with pytest.raises(CheckpointNotFoundError) as exc_info:
            await repository.load_checkpoint("ckpt-nonexistent")

        assert "ckpt-nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_checkpoints_success(self, repository):
        """Test listing checkpoints for workflow."""
        mock_conn = AsyncMock()
        mock_rows = [
            {
                "checkpoint_id": "ckpt-1",
                "state_version": 1,
                "created_at": datetime.now(UTC),
            },
            {
                "checkpoint_id": "ckpt-2",
                "state_version": 2,
                "created_at": datetime.now(UTC),
            },
        ]
        mock_conn.fetch.return_value = mock_rows
        repository.pool.acquire = MagicMock(
            return_value=self._mock_pool_acquire(mock_conn)
        )

        checkpoints = await repository.list_checkpoints("wf-123", limit=10)

        assert len(checkpoints) == 2
        assert checkpoints[0]["checkpoint_id"] == "ckpt-1"
        assert checkpoints[1]["checkpoint_id"] == "ckpt-2"

    @pytest.mark.asyncio
    async def test_list_checkpoints_empty(self, repository):
        """Test listing checkpoints when none exist."""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []
        repository.pool.acquire = MagicMock(
            return_value=self._mock_pool_acquire(mock_conn)
        )

        checkpoints = await repository.list_checkpoints("wf-nonexistent")

        assert checkpoints == []

    @pytest.mark.asyncio
    async def test_cleanup_old_checkpoints(self, repository):
        """Test cleanup of old checkpoints."""
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 5"  # 5 rows deleted
        repository.pool.acquire = MagicMock(
            return_value=self._mock_pool_acquire(mock_conn)
        )

        deleted_count = await repository.cleanup_old_checkpoints(retention_hours=48)

        assert deleted_count == 5
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_workflow_metadata(self, repository):
        """Test saving workflow metadata."""
        mock_conn = AsyncMock()
        repository.pool.acquire = MagicMock(
            return_value=self._mock_pool_acquire(mock_conn)
        )

        await repository.save_workflow_metadata(
            workflow_id="wf-123",
            user_request="Test request",
            status="RUNNING",
            current_phase="development",
            current_agent="software_engineer",
        )

        mock_conn.execute.assert_called_once()
        # Verify JSON serialization
        call_args = mock_conn.execute.call_args[0]
        assert "wf-123" in call_args

    @pytest.mark.asyncio
    async def test_log_audit_event(self, repository):
        """Test audit event logging."""
        mock_conn = AsyncMock()
        repository.pool.acquire = MagicMock(
            return_value=self._mock_pool_acquire(mock_conn)
        )

        await repository.log_audit_event(
            workflow_id="wf-123",
            event_type="checkpoint_created",
            agent_name="software_engineer",
            event_data={"checkpoint_id": "ckpt-123", "version": 1},
        )

        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_success(self, repository):
        """Test successful database connection."""
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            await repository.connect()

            assert repository.pool == mock_pool
            mock_create_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, repository):
        """Test database connection failure."""
        import asyncpg

        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_create_pool.side_effect = asyncpg.PostgresError("Connection refused")

            with pytest.raises(DatabaseConnectionError) as exc_info:
                await repository.connect()

            assert "connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_disconnect(self, repository):
        """Test database disconnection."""
        mock_pool = AsyncMock()
        repository.pool = mock_pool

        await repository.disconnect()

        mock_pool.close.assert_called_once()
        assert repository.pool is None
