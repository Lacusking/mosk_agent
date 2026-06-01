"""agent runtime sessions and events

Revision ID: 20260528_0001
Revises:
Create Date: 2026-05-28 00:01:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260528_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _utc_now() -> sa.TextClause:
    return sa.text("timezone('UTC', now())")


def upgrade() -> None:
    """创建 Session、AgentRun、step 与 runtime event 表。"""
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("last_message_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=_utc_now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=_utc_now()),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_sessions_status"),
        sa.CheckConstraint("last_message_sequence >= 0", name="ck_sessions_last_message_sequence"),
    )
    op.create_index("idx_sessions_status_updated_at", "sessions", ["status", "updated_at"])

    op.create_table(
        "session_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=_utc_now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=_utc_now()),
        sa.CheckConstraint("sequence >= 1", name="ck_session_messages_sequence"),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_session_messages_role"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "sequence", name="uq_session_messages_session_sequence"),
    )
    op.create_index(
        "idx_session_messages_session_sequence",
        "session_messages",
        ["session_id", "sequence"],
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("requested_pattern", sa.String(length=64), nullable=True),
        sa.Column("active_pattern", sa.String(length=64), nullable=False),
        sa.Column("context_message_sequence", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("finish_reason", sa.String(length=64), nullable=True),
        sa.Column("error_type", sa.String(length=128), nullable=True),
        sa.Column("max_steps", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Float(), nullable=False),
        sa.Column("retry_limit", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=_utc_now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=_utc_now()),
        sa.Column("started_at", sa.TIMESTAMP(timezone=False), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=False), nullable=True),
        sa.CheckConstraint(
            "status IN ('created', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_agent_runs_status",
        ),
        sa.CheckConstraint("mode IN ('chat', 'plan', 'build', 'review')", name="ck_agent_runs_mode"),
        sa.CheckConstraint("context_message_sequence >= 1", name="ck_agent_runs_context_sequence"),
        sa.CheckConstraint("max_steps > 0", name="ck_agent_runs_max_steps"),
        sa.CheckConstraint("timeout_seconds > 0", name="ck_agent_runs_timeout_seconds"),
        sa.CheckConstraint("retry_limit >= 0", name="ck_agent_runs_retry_limit"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["input_message_id"], ["session_messages.id"]),
    )
    op.create_index("idx_agent_runs_session_status", "agent_runs", ["session_id", "status"])
    op.create_index("idx_agent_runs_trace_id", "agent_runs", ["trace_id"])
    op.create_index(
        "uq_agent_runs_active_session",
        "agent_runs",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('created', 'running')"),
    )

    op.create_foreign_key(
        "fk_session_messages_agent_run_id_agent_runs",
        "session_messages",
        "agent_runs",
        ["agent_run_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "agent_run_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("pattern", sa.String(length=64), nullable=False),
        sa.Column("invocation_id", sa.String(length=64), nullable=True),
        sa.Column(
            "safe_input",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "safe_output",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_type", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=_utc_now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=_utc_now()),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=False), nullable=True),
        sa.CheckConstraint("sequence >= 1", name="ck_agent_run_steps_sequence"),
        sa.CheckConstraint(
            "kind IN ('model', 'tool', 'transition', 'complete', 'fail')",
            name="ck_agent_run_steps_kind",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'cancelled')",
            name="ck_agent_run_steps_status",
        ),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("agent_run_id", "sequence", name="uq_agent_run_steps_run_sequence"),
    )
    op.create_index(
        "idx_agent_run_steps_run_sequence",
        "agent_run_steps",
        ["agent_run_id", "sequence"],
    )

    op.create_table(
        "runtime_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("span_id", sa.String(length=64), nullable=False),
        sa.Column("parent_span_id", sa.String(length=64), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=_utc_now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=False), nullable=False, server_default=_utc_now()),
        sa.CheckConstraint("event_version >= 1", name="ck_runtime_events_event_version"),
        sa.CheckConstraint("sequence >= 1", name="ck_runtime_events_sequence"),
        sa.CheckConstraint("actor_type IN ('runtime', 'system', 'user')", name="ck_runtime_events_actor_type"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["agent_run_steps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("agent_run_id", "sequence", name="uq_runtime_events_run_sequence"),
    )
    op.create_index("idx_runtime_events_run_sequence", "runtime_events", ["agent_run_id", "sequence"])
    op.create_index("idx_runtime_events_trace_id", "runtime_events", ["trace_id"])


def downgrade() -> None:
    """删除 Agent runtime 持久化表与索引。"""
    op.drop_index("idx_runtime_events_trace_id", table_name="runtime_events")
    op.drop_index("idx_runtime_events_run_sequence", table_name="runtime_events")
    op.drop_table("runtime_events")

    op.drop_index("idx_agent_run_steps_run_sequence", table_name="agent_run_steps")
    op.drop_table("agent_run_steps")

    op.drop_constraint(
        "fk_session_messages_agent_run_id_agent_runs",
        "session_messages",
        type_="foreignkey",
    )
    op.drop_index("uq_agent_runs_active_session", table_name="agent_runs")
    op.drop_index("idx_agent_runs_trace_id", table_name="agent_runs")
    op.drop_index("idx_agent_runs_session_status", table_name="agent_runs")
    op.drop_table("agent_runs")

    op.drop_index("idx_session_messages_session_sequence", table_name="session_messages")
    op.drop_table("session_messages")

    op.drop_index("idx_sessions_status_updated_at", table_name="sessions")
    op.drop_table("sessions")
