"""Initial schema creation for multi-tier agent ecosystem.

Revision ID: 001
Revises:
Create Date: 2026-01-30 10:40:00.000000

This migration creates the initial database schema including:
- checkpoints table for workflow state persistence
- workflows table for workflow metadata
- audit_events table for audit logging
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""
    # Create checkpoints table
    op.create_table(
        "checkpoints",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("workflow_id", sa.String(36), nullable=False, index=True),
        sa.Column("checkpoint_id", sa.String(36), nullable=False),
        sa.Column("state", postgresql.JSON, nullable=False),
        sa.Column("metadata", postgresql.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "workflow_id", "checkpoint_id", name="uq_workflow_checkpoint"
        ),
    )

    # Create workflows table
    op.create_table(
        "workflows",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("phase", sa.String(50), nullable=True),
        sa.Column("current_agent", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Index("idx_workflow_status", "status"),
        sa.Index("idx_workflow_created", "created_at"),
    )

    # Create audit_events table
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("workflow_id", sa.String(36), nullable=False, index=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("actor", sa.String(255), nullable=True),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("details", postgresql.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Index("idx_audit_workflow", "workflow_id"),
        sa.Index("idx_audit_event_type", "event_type"),
        sa.Index("idx_audit_created", "created_at"),
    )

    # Create foreign key constraints
    op.create_foreign_key(
        "fk_checkpoints_workflow",
        "checkpoints",
        "workflows",
        ["workflow_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_audit_events_workflow",
        "audit_events",
        "workflows",
        ["workflow_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Drop initial database schema."""
    # Drop foreign keys
    op.drop_constraint("fk_audit_events_workflow", "audit_events", type_="foreignkey")
    op.drop_constraint("fk_checkpoints_workflow", "checkpoints", type_="foreignkey")

    # Drop tables
    op.drop_table("audit_events")
    op.drop_table("workflows")
    op.drop_table("checkpoints")
