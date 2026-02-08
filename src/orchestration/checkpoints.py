"""LangGraph checkpoint manager with PostgreSQL persistence.

Implements LangGraph Checkpointer interface for workflow state persistence.
Manages checkpoint lifecycle: save, load, list, cleanup.
"""

from collections.abc import AsyncIterator
from typing import Any, cast

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

from src.config import Settings
from src.orchestration.state import WorkflowState
from src.storage.checkpoint_repository import CheckpointRepository


logger = structlog.get_logger()


class CheckpointManager(BaseCheckpointSaver):  # type: ignore
    """LangGraph checkpoint manager with PostgreSQL backend.

    Implements LangGraph Checkpointer interface for state persistence.
    Delegates storage operations to CheckpointRepository.

    Attributes:
        repository: CheckpointRepository instance
        retention_hours: Checkpoint retention period (default: 48 hours)
        max_checkpoints_per_workflow: Maximum checkpoints to retain (default: 10)
    """

    def __init__(
        self,
        settings: Settings,
        retention_hours: int = 48,
        max_checkpoints_per_workflow: int = 10,
    ) -> None:
        """Initialize checkpoint manager.

        Args:
            settings: Application settings
            retention_hours: Delete checkpoints older than this (default: 48)
            max_checkpoints_per_workflow: Max checkpoints per workflow (default: 10)
        """
        super().__init__()
        self.repository = CheckpointRepository(settings)
        self.retention_hours = retention_hours
        self.max_checkpoints_per_workflow = max_checkpoints_per_workflow

    async def connect(self) -> None:
        """Establish database connection pool."""
        await self.repository.connect()

    async def disconnect(self) -> None:
        """Close database connection pool."""
        await self.repository.disconnect()

    async def aget(
        self,
        config: RunnableConfig,
    ) -> Checkpoint | None:
        """Get checkpoint by config (LangGraph interface).

        Args:
            config: LangGraph config with checkpoint_id

        Returns:
            Checkpoint object or None if not found
        """
        checkpoint_id = config.get("checkpoint_id")
        if not checkpoint_id:
            return None

        try:
            state = await self.repository.load_checkpoint(str(checkpoint_id))
            return self._state_to_checkpoint(state, str(checkpoint_id))
        except Exception:
            # Checkpoint not found or error
            return None

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        _metadata: CheckpointMetadata,
        _new_versions: dict[str, Any],
    ) -> RunnableConfig:
        """Save checkpoint (LangGraph interface).

        Args:
            config: LangGraph config with workflow_id
            checkpoint: Checkpoint object to save
            metadata: Checkpoint metadata

        Returns:
            Updated config with checkpoint_id
        """
        workflow_id = config.get("workflow_id", "unknown")
        workflow_id_str = str(workflow_id)
        state = self._checkpoint_to_state(checkpoint)

        checkpoint_id = await self.repository.save_checkpoint(
            workflow_id=workflow_id_str,
            state=state,
        )

        # Update workflow metadata
        await self.repository.save_workflow_metadata(
            workflow_id=workflow_id_str,
            user_request=state.get("user_request", ""),
            status=state.get("current_phase", "RUNNING"),
            current_phase=state.get("current_phase"),
            current_agent=state.get("current_agent"),
            budget_used_usd=state.get("budget_used_usd", 0.0),
            rejection_count=state.get("rejection_count", 0),
        )

        # Log audit event
        await self.repository.log_audit_event(
            workflow_id=workflow_id_str,
            event_type="CHECKPOINT_SAVED",
            agent_name=state.get("current_agent", "system"),
            event_data={
                "checkpoint_id": checkpoint_id,
                "state_version": state.get("state_version", 1),
            },
        )

        # TypedDict doesn't officially support extra keys, but LangGraph uses them
        updated_config = cast(
            RunnableConfig, {**config, "checkpoint_id": checkpoint_id}
        )
        return updated_config

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,  # noqa: ARG002, A002
        before: RunnableConfig | None = None,  # noqa: ARG002
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """List checkpoints (LangGraph interface)."""
        if config is None:
            return
        workflow_id = config.get("configurable", {}).get("workflow_id") or config.get(
            "workflow_id"
        )
        if not workflow_id:
            return

        limit_val = limit or self.max_checkpoints_per_workflow
        checkpoints = await self.repository.list_checkpoints(
            workflow_id=str(workflow_id),
            limit=limit_val,
        )

        for checkpoint_meta in checkpoints:
            try:
                state = await self.repository.load_checkpoint(
                    checkpoint_meta["checkpoint_id"]
                )
                checkpoint = self._state_to_checkpoint(
                    state,
                    checkpoint_meta["checkpoint_id"],
                )

                # Construct CheckpointTuple
                # We need to construct a valid config for this checkpoint
                checkpoint_config: RunnableConfig = {
                    "configurable": {
                        "thread_id": workflow_id,
                        "checkpoint_id": checkpoint_meta["checkpoint_id"],
                        "workflow_id": workflow_id,
                    }
                }

                metadata_dict: CheckpointMetadata = {"source": "input", "step": -1, "writes": {}, "parents": {}}  # type: ignore[typeddict-unknown-key]
                yield CheckpointTuple(
                    config=checkpoint_config,
                    checkpoint=checkpoint,
                    metadata=metadata_dict,
                    parent_config=None,
                    pending_writes=[],
                )
            except Exception as e:
                # Skip corrupted checkpoints
                logger.warning("corrupted_checkpoint", error=str(e))
                continue

    async def cleanup_old_checkpoints(self) -> int:
        """Delete checkpoints older than retention period.

        Returns:
            Number of checkpoints deleted
        """
        return await self.repository.cleanup_old_checkpoints(
            retention_hours=self.retention_hours
        )

    def _state_to_checkpoint(
        self,
        state: WorkflowState,
        checkpoint_id: str,
    ) -> Checkpoint:
        """Convert WorkflowState to LangGraph Checkpoint.

        Args:
            state: Workflow state dictionary
            checkpoint_id: Checkpoint identifier

        Returns:
            LangGraph Checkpoint object
        """
        checkpoint_dict: dict[str, Any] = {
            "v": state.get("state_version", 1),
            "ts": checkpoint_id,
            "id": checkpoint_id,
            "channel_values": {"state": state},
            "channel_versions": {},
            "versions_seen": {},
        }
        return checkpoint_dict  # type: ignore[return-value]

    def _checkpoint_to_state(self, checkpoint: Checkpoint) -> WorkflowState:
        """Convert LangGraph Checkpoint to WorkflowState.

        Args:
            checkpoint: LangGraph Checkpoint object

        Returns:
            WorkflowState dictionary
        """
        state = cast(WorkflowState, checkpoint["channel_values"].get("state", {}))
        state["state_version"] = checkpoint["v"]
        return state
