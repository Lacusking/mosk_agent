"""AgentRun 与 AgentRunStep 的 ORM 映射。"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.contracts.agent_runs import AgentRunStatus
from src.contracts.agent_runs import AgentRunStepKind
from src.contracts.agent_runs import AgentRunStepStatus
from src.storage.database import PkModel
from src.storage.database import TimestampedModel


class AgentRunRecord(PkModel, TimestampedModel):
    """agent_runs 表 ORM 记录。"""

    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("idx_agent_runs_session_status", "session_id", "status"),
        Index("idx_agent_runs_trace_id", "trace_id"),
    )

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    input_message_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_messages.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=AgentRunStatus.CREATED)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_pattern: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active_pattern: Mapped[str] = mapped_column(String(64), nullable=False)
    context_message_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    finish_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    max_steps: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_seconds: Mapped[float] = mapped_column(nullable=False)
    retry_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class AgentRunStepRecord(PkModel, TimestampedModel):
    """agent_run_steps 表 ORM 记录。"""

    __tablename__ = "agent_run_steps"
    __table_args__ = (
        UniqueConstraint("agent_run_id", "sequence", name="uq_agent_run_steps_run_sequence"),
        Index("idx_agent_run_steps_run_sequence", "agent_run_id", "sequence"),
    )

    agent_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default=AgentRunStepKind.MODEL)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AgentRunStepStatus.RUNNING,
    )
    pattern: Mapped[str] = mapped_column(String(64), nullable=False)
    invocation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    safe_input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    safe_output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)


__all__ = ["AgentRunRecord", "AgentRunStepRecord"]
