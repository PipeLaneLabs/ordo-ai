"""Integration tests for CheckpointManager with LangGraph integration."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.config import Settings
from src.orchestration.checkpoints import CheckpointManager
from src.orchestration.state import WorkflowState


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings."""
    return Settings(
        environment="test",
        log_level="DEBUG",
        postgres_url="postgresql://test:test@localhost/test",
        redis_url="redis://localhost:6379/0",
        minio_endpoint="localhost:9000",
        openrouter_api_key="test-api-key-12345",
        google_api_key="test-api-key-12345",
        jwt_secret_key="test-secret-key-min-32-chars-long-123456",
        human_approval_timeout=300,
        total_budget_tokens=100000,
        max_monthly_budget_usd=10.0,
    )


@pytest.fixture
def sample_workflow_state() -> WorkflowState:
    """Create sample workflow state for testing."""
    return {
        "workflow_id": "test-workflow-456",
        "user_request": "Test checkpoint functionality",
        "current_phase": "testing",
        "current_task": "checkpoint_test",
        "current_agent": "CheckpointManager",
        "rejection_count": 0,
        "state_version": 1,
        "requirements": "",
        "architecture": "",
        "tasks": "",
        "code_files": {},
        "test_files": {},
        "partial_artifacts": {},
        "validation_report": "",
        "quality_report": "",
        "security_report": "",
        "budget_used_tokens": 100,
        "budget_used_usd": 0.01,
        "budget_remaining_tokens": 99900,
        "budget_remaining_usd": 9.99,
        "quality_gates_passed": [],
        "blocking_issues": [],
        "awaiting_human_approval": False,
        "approval_gate": "",
        "approval_timeout": "",
        "routing_decision": {},
        "escalation_flag": False,
        "trace_id": "test-trace-456",
        "dependencies": "",
        "infrastructure": "",
        "observability": "",
        "deviation_log": "",
        "compliance_log": "",
        "acceptance_report": "",
        "agent_token_usage": {},
        "created_at": "2026-01-23T19:00:00+13:00",
        "updated_at": "2026-01-23T19:00:00+13:00",
    }


class TestCheckpointManagerInitialization:
    """Test CheckpointManager initialization."""

    def test_initialization_default_params(self, mock_settings: Settings) -> None:
        """Test initialization with default parameters."""
        # Act
        manager = CheckpointManager(settings=mock_settings)

        # Assert
        assert manager.retention_hours == 48
        assert manager.max_checkpoints_per_workflow == 10
        assert manager.repository is not None

    def test_initialization_custom_params(self, mock_settings: Settings) -> None:
        """Test initialization with custom parameters."""
        # Act
        manager = CheckpointManager(
            settings=mock_settings,
            retention_hours=72,
            max_checkpoints_per_workflow=20,
        )

        # Assert
        assert manager.retention_hours == 72
        assert manager.max_checkpoints_per_workflow == 20


class TestCheckpointManagerConnection:
    """Test CheckpointManager database connection."""

    @pytest.mark.asyncio
    async def test_connect(self, mock_settings: Settings) -> None:
        """Test connect() delegates to repository."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        manager.repository.connect = AsyncMock()

        # Act
        await manager.connect()

        # Assert
        manager.repository.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_settings: Settings) -> None:
        """Test disconnect() delegates to repository."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        manager.repository.disconnect = AsyncMock()

        # Act
        await manager.disconnect()

        # Assert
        manager.repository.disconnect.assert_called_once()


class TestCheckpointManagerAput:
    """Test CheckpointManager.aput() for saving checkpoints."""

    @pytest.mark.asyncio
    async def test_aput_saves_checkpoint(
        self,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
    ) -> None:
        """Test aput() saves checkpoint to repository."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        manager.repository.save_checkpoint = AsyncMock(return_value="checkpoint-123")
        manager.repository.save_workflow_metadata = AsyncMock()
        manager.repository.log_audit_event = AsyncMock()

        config = {"workflow_id": "test-workflow-456"}
        checkpoint = {
            "v": 1,
            "ts": "checkpoint-123",
            "id": "checkpoint-123",
            "channel_values": {"state": sample_workflow_state},
            "channel_versions": {},
            "versions_seen": {},
            "pending_sends": [],
        }
        metadata = {"source": "test"}

        # Act
        result_config = await manager.aput(config, checkpoint, metadata, {})

        # Assert
        manager.repository.save_checkpoint.assert_called_once()
        assert result_config["checkpoint_id"] == "checkpoint-123"

    @pytest.mark.asyncio
    async def test_aput_saves_workflow_metadata(
        self,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
    ) -> None:
        """Test aput() saves workflow metadata."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        manager.repository.save_checkpoint = AsyncMock(return_value="checkpoint-123")
        manager.repository.save_workflow_metadata = AsyncMock()
        manager.repository.log_audit_event = AsyncMock()

        config = {"workflow_id": "test-workflow-456"}
        checkpoint = {
            "v": 1,
            "ts": "checkpoint-123",
            "id": "checkpoint-123",
            "channel_values": {"state": sample_workflow_state},
            "channel_versions": {},
            "versions_seen": {},
            "pending_sends": [],
        }
        metadata = {"source": "test"}

        # Act
        await manager.aput(config, checkpoint, metadata, {})

        # Assert
        manager.repository.save_workflow_metadata.assert_called_once()
        call_kwargs = manager.repository.save_workflow_metadata.call_args.kwargs
        assert call_kwargs["workflow_id"] == "test-workflow-456"
        assert call_kwargs["user_request"] == "Test checkpoint functionality"
        assert call_kwargs["budget_used_usd"] == 0.01

    @pytest.mark.asyncio
    async def test_aput_logs_audit_event(
        self,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
    ) -> None:
        """Test aput() logs audit event."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        manager.repository.save_checkpoint = AsyncMock(return_value="checkpoint-123")
        manager.repository.save_workflow_metadata = AsyncMock()
        manager.repository.log_audit_event = AsyncMock()

        config = {"workflow_id": "test-workflow-456"}
        checkpoint = {
            "v": 1,
            "ts": "checkpoint-123",
            "id": "checkpoint-123",
            "channel_values": {"state": sample_workflow_state},
            "channel_versions": {},
            "versions_seen": {},
            "pending_sends": [],
        }
        metadata = {"source": "test"}

        # Act
        await manager.aput(config, checkpoint, metadata, {})

        # Assert
        manager.repository.log_audit_event.assert_called_once()
        call_kwargs = manager.repository.log_audit_event.call_args.kwargs
        assert call_kwargs["event_type"] == "CHECKPOINT_SAVED"
        assert call_kwargs["agent_name"] == "CheckpointManager"


class TestCheckpointManagerAget:
    """Test CheckpointManager.aget() for loading checkpoints."""

    @pytest.mark.asyncio
    async def test_aget_loads_checkpoint(
        self,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
    ) -> None:
        """Test aget() loads checkpoint from repository."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        manager.repository.load_checkpoint = AsyncMock(
            return_value=sample_workflow_state
        )

        config = {"checkpoint_id": "checkpoint-123"}

        # Act
        checkpoint = await manager.aget(config)

        # Assert
        manager.repository.load_checkpoint.assert_called_once_with("checkpoint-123")
        assert checkpoint is not None
        assert checkpoint["channel_values"]["state"] == sample_workflow_state

    @pytest.mark.asyncio
    async def test_aget_returns_none_for_missing_checkpoint(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test aget() returns None when checkpoint_id is missing."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        config = {}

        # Act
        checkpoint = await manager.aget(config)

        # Assert
        assert checkpoint is None

    @pytest.mark.asyncio
    async def test_aget_handles_repository_error(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test aget() returns None on repository error."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        manager.repository.load_checkpoint = AsyncMock(
            side_effect=Exception("Database error")
        )

        config = {"checkpoint_id": "checkpoint-123"}

        # Act
        checkpoint = await manager.aget(config)

        # Assert
        assert checkpoint is None


class TestCheckpointManagerAlist:
    """Test CheckpointManager.alist() for listing checkpoints."""

    @pytest.mark.asyncio
    async def test_alist_returns_checkpoints(
        self,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
    ) -> None:
        """Test alist() returns checkpoint list."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        manager.repository.list_checkpoints = AsyncMock(
            return_value=[
                {
                    "checkpoint_id": "checkpoint-1",
                    "state_version": 1,
                    "created_at": "2026-01-23T19:00:00+13:00",
                },
                {
                    "checkpoint_id": "checkpoint-2",
                    "state_version": 2,
                    "created_at": "2026-01-23T19:01:00+13:00",
                },
            ]
        )
        manager.repository.load_checkpoint = AsyncMock(
            return_value=sample_workflow_state
        )

        config = {"configurable": {"workflow_id": "test-workflow-456"}}

        # Act
        checkpoints = []
        async for checkpoint_tuple in manager.alist(config):
            checkpoints.append(checkpoint_tuple)

        # Assert
        assert len(checkpoints) == 2
        manager.repository.list_checkpoints.assert_called_once()

    @pytest.mark.asyncio
    async def test_alist_respects_limit(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test alist() respects limit parameter."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        manager.repository.list_checkpoints = AsyncMock(return_value=[])

        config = {"workflow_id": "test-workflow-456"}

        # Act
        checkpoints = []
        async for checkpoint_tuple in manager.alist(config, _limit=5):
            checkpoints.append(checkpoint_tuple)

        # Assert
        call_kwargs = manager.repository.list_checkpoints.call_args.kwargs
        assert call_kwargs["limit"] == 5

    @pytest.mark.asyncio
    async def test_alist_handles_missing_workflow_id(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test alist() returns empty for missing workflow_id."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        config = {}

        # Act
        checkpoints = []
        async for checkpoint_tuple in manager.alist(config):
            checkpoints.append(checkpoint_tuple)

        # Assert
        assert len(checkpoints) == 0


class TestCheckpointManagerCleanup:
    """Test CheckpointManager.cleanup_old_checkpoints()."""

    @pytest.mark.asyncio
    async def test_cleanup_old_checkpoints(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test cleanup_old_checkpoints() delegates to repository."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        manager.repository.cleanup_old_checkpoints = AsyncMock(return_value=5)

        # Act
        deleted_count = await manager.cleanup_old_checkpoints()

        # Assert
        assert deleted_count == 5
        manager.repository.cleanup_old_checkpoints.assert_called_once_with(
            retention_hours=48
        )


class TestCheckpointManagerStateConversion:
    """Test CheckpointManager state <-> checkpoint conversion."""

    def test_state_to_checkpoint_conversion(
        self,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
    ) -> None:
        """Test _state_to_checkpoint() creates valid checkpoint."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        checkpoint_id = str(uuid4())

        # Act
        checkpoint = manager._state_to_checkpoint(sample_workflow_state, checkpoint_id)

        # Assert
        assert checkpoint["v"] == 1
        assert checkpoint["id"] == checkpoint_id
        assert checkpoint["ts"] == checkpoint_id
        assert checkpoint["channel_values"]["state"] == sample_workflow_state

    def test_checkpoint_to_state_conversion(
        self,
        mock_settings: Settings,
        sample_workflow_state: WorkflowState,
    ) -> None:
        """Test _checkpoint_to_state() extracts state."""
        # Arrange
        manager = CheckpointManager(settings=mock_settings)
        checkpoint = {
            "v": 2,
            "ts": "checkpoint-123",
            "id": "checkpoint-123",
            "channel_values": {"state": sample_workflow_state},
            "channel_versions": {},
            "versions_seen": {},
            "pending_sends": [],
        }

        # Act
        state = manager._checkpoint_to_state(checkpoint)

        # Assert
        assert state["workflow_id"] == "test-workflow-456"
        assert state["state_version"] == 2
        assert state["user_request"] == "Test checkpoint functionality"
