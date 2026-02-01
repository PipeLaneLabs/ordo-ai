"""PostgreSQL repository for workflow checkpoints and audit events.

Provides async database operations for:
- Checkpoint storage (workflow state snapshots)
- Workflow metadata (status, budget tracking)
- Audit events (agent executions, approvals, rejections)
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

import asyncpg  # type: ignore[import-untyped]

from src.config import Settings
from src.exceptions import CheckpointNotFoundError, DatabaseConnectionError
from src.orchestration.state import WorkflowState


class CheckpointRepository:
    """Async PostgreSQL repository for workflow persistence.

    Manages connection pooling and provides CRUD operations for:
    - Checkpoints (state snapshots)
    - Workflows (metadata)
    - Audit events (execution history)

    Attributes:
        pool: asyncpg connection pool
        min_connections: Minimum pool size (default: 5)
        max_connections: Maximum pool size (default: 20)
    """

    def __init__(
        self,
        settings: Settings,
        min_connections: int = 5,
        max_connections: int = 20,
    ) -> None:
        """Initialize repository with connection pool settings.

        Args:
            settings: Application settings with postgres_url
            min_connections: Minimum pool size
            max_connections: Maximum pool size
        """
        self.postgres_url = settings.postgres_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Establish connection pool to PostgreSQL.

        Raises:
            DatabaseConnectionError: On connection failures
        """
        try:
            self.pool = await asyncpg.create_pool(
                self.postgres_url,
                min_size=self.min_connections,
                max_size=self.max_connections,
                command_timeout=60,
            )
        except (asyncpg.PostgresError, OSError) as e:
            raise DatabaseConnectionError(
                database="postgresql",
                operation="connect",
                details={"error": str(e), "url": self.postgres_url[:30] + "..."},
            ) from e

    async def disconnect(self) -> None:
        """Close connection pool gracefully."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def save_checkpoint(
        self,
        workflow_id: str,
        state: WorkflowState,
        checkpoint_id: str | None = None,
    ) -> str:
        """Save workflow state checkpoint to PostgreSQL.

        Args:
            workflow_id: Unique workflow identifier
            state: Current workflow state
            checkpoint_id: Optional checkpoint ID (generates UUID if None)

        Returns:
            Checkpoint ID (UUID string)

        Raises:
            DatabaseConnectionError: On database errors
        """
        if not self.pool:
            raise DatabaseConnectionError(
                database="postgresql",
                operation="save_checkpoint",
                details={
                    "error": "Connection pool not initialized. Call connect() first."
                },
            )

        checkpoint_id = checkpoint_id or str(uuid4())
        state_version = state.get("state_version", 1)

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO checkpoints
                    (checkpoint_id, workflow_id, state_version, state, created_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    """,
                    checkpoint_id,
                    workflow_id,
                    state_version,
                    json.dumps(state),
                )
                return checkpoint_id

        except asyncpg.PostgresError as e:
            raise DatabaseConnectionError(
                database="postgresql",
                operation="save_checkpoint",
                details={
                    "error": str(e),
                    "workflow_id": workflow_id,
                    "checkpoint_id": checkpoint_id,
                },
            ) from e

    async def load_checkpoint(
        self,
        checkpoint_id: str,
    ) -> WorkflowState:
        """Load workflow state from checkpoint.

        Args:
            checkpoint_id: Checkpoint UUID

        Returns:
            WorkflowState dictionary

        Raises:
            CheckpointNotFoundError: If checkpoint doesn't exist
            DatabaseConnectionError: On database errors
        """
        if not self.pool:
            raise DatabaseConnectionError(
                database="postgresql",
                operation="load_checkpoint",
                details={
                    "error": "Connection pool not initialized. Call connect() first."
                },
            )

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT state FROM checkpoints
                    WHERE checkpoint_id = $1
                    """,
                    checkpoint_id,
                )

                if not row:
                    raise CheckpointNotFoundError(
                        checkpoint_id=checkpoint_id,
                        details={"operation": "load_checkpoint"},
                    )

                return cast(WorkflowState, json.loads(row["state"]))

        except asyncpg.PostgresError as e:
            raise DatabaseConnectionError(
                database="postgresql",
                operation="load_checkpoint",
                details={
                    "error": str(e),
                    "checkpoint_id": checkpoint_id,
                },
            ) from e

    async def list_checkpoints(
        self,
        workflow_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get checkpoint history for a workflow.

        Args:
            workflow_id: Workflow identifier
            limit: Maximum number of checkpoints to return (default: 10)

        Returns:
            List of checkpoint metadata (id, version, created_at)

        Raises:
            DatabaseConnectionError: On database errors
        """
        if not self.pool:
            raise DatabaseConnectionError(
                database="postgresql",
                operation="list_checkpoints",
                details={
                    "error": "Connection pool not initialized. Call connect() first."
                },
            )

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT checkpoint_id, state_version, created_at
                    FROM checkpoints
                    WHERE workflow_id = $1
                    ORDER BY state_version DESC
                    LIMIT $2
                    """,
                    workflow_id,
                    limit,
                )

                return [
                    {
                        "checkpoint_id": str(row["checkpoint_id"]),
                        "state_version": row["state_version"],
                        "created_at": row["created_at"].isoformat(),
                    }
                    for row in rows
                ]

        except asyncpg.PostgresError as e:
            raise DatabaseConnectionError(
                database="postgresql",
                operation="list_checkpoints",
                details={
                    "error": str(e),
                    "workflow_id": workflow_id,
                },
            ) from e

    async def cleanup_old_checkpoints(
        self,
        retention_hours: int = 48,
    ) -> int:
        """Delete checkpoints older than retention period.

        Args:
            retention_hours: Delete checkpoints older than this (default: 48 hours)

        Returns:
            Number of checkpoints deleted

        Raises:
            DatabaseConnectionError: On database errors
        """
        if not self.pool:
            raise DatabaseConnectionError(
                database="postgresql",
                operation="cleanup_old_checkpoints",
                details={
                    "error": "Connection pool not initialized. Call connect() first."
                },
            )

        cutoff_time = datetime.now(UTC) - timedelta(hours=retention_hours)

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM checkpoints
                    WHERE created_at < $1
                    """,
                    cutoff_time,
                )
                # Extract count from result string "DELETE N"
                count = int(result.split()[-1]) if result else 0
                return count

        except asyncpg.PostgresError as e:
            raise DatabaseConnectionError(
                database="postgresql",
                operation="cleanup_old_checkpoints",
                details={
                    "error": str(e),
                    "retention_hours": retention_hours,
                },
            ) from e

    async def save_workflow_metadata(
        self,
        workflow_id: str,
        user_request: str,
        status: str,
        current_phase: str | None = None,
        current_agent: str | None = None,
        budget_used_usd: float = 0.0,
        rejection_count: int = 0,
    ) -> None:
        """Insert or update workflow metadata.

        Args:
            workflow_id: Unique workflow identifier
            user_request: Original user request text
            status: Workflow status (RUNNING/WAITING_APPROVAL/COMPLETED/FAILED)
            current_phase: Current execution phase
            current_agent: Currently executing agent
            budget_used_usd: Total budget consumed
            rejection_count: Number of rejections

        Raises:
            DatabaseConnectionError: On database errors
        """
        if not self.pool:
            raise DatabaseConnectionError(
                database="postgresql",
                operation="save_workflow_metadata",
                details={
                    "error": "Connection pool not initialized. Call connect() first."
                },
            )

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO workflows (
                        workflow_id, user_request, status, current_phase,
                        current_agent, budget_used_usd, rejection_count,
                        created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                    ON CONFLICT (workflow_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        current_phase = EXCLUDED.current_phase,
                        current_agent = EXCLUDED.current_agent,
                        budget_used_usd = EXCLUDED.budget_used_usd,
                        rejection_count = EXCLUDED.rejection_count,
                        updated_at = NOW(),
                        completed_at = CASE WHEN EXCLUDED.status IN ('COMPLETED',
                            'FAILED') THEN NOW() ELSE workflows.completed_at END
                    """,
                    workflow_id,
                    user_request,
                    status,
                    current_phase,
                    current_agent,
                    budget_used_usd,
                    rejection_count,
                )

        except asyncpg.PostgresError as e:
            raise DatabaseConnectionError(
                database="postgresql",
                operation="save_workflow_metadata",
                details={
                    "error": str(e),
                    "workflow_id": workflow_id,
                },
            ) from e

    async def log_audit_event(
        self,
        workflow_id: str,
        event_type: str,
        agent_name: str,
        event_data: dict[str, Any] | None = None,
    ) -> str:
        """Log audit event for traceability.

        Args:
            workflow_id: Workflow identifier
            event_type: Event type (AGENT_START/AGENT_COMPLETE/REJECTION/APPROVAL)
            agent_name: Name of agent triggering event
            event_data: Optional additional event data

        Returns:
            Event ID (UUID string)

        Raises:
            DatabaseConnectionError: On database errors
        """
        if not self.pool:
            raise DatabaseConnectionError(
                database="postgresql",
                operation="log_audit_event",
                details={
                    "error": "Connection pool not initialized. Call connect() first."
                },
            )

        event_id = str(uuid4())

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_events (
                        event_id, workflow_id, event_type, agent_name,
                        details, timestamp
                    )
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    """,
                    event_id,
                    workflow_id,
                    event_type,
                    agent_name,
                    json.dumps(event_data or {}),
                )
                return event_id

        except asyncpg.PostgresError as e:
            raise DatabaseConnectionError(
                database="postgresql",
                operation="log_audit_event",
                details={
                    "error": str(e),
                    "workflow_id": workflow_id,
                    "event_type": event_type,
                },
            ) from e
