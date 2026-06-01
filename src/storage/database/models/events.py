"""RuntimeEvent 的 ORM 映射。"""

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

from src.contracts.runtime import RuntimeActorType
from src.storage.database import PkModel
from src.storage.database import TimestampedModel


class RuntimeEventRecord(PkModel, TimestampedModel):
    """runtime_events 表 ORM 记录。"""

    __tablename__ = "runtime_events"
    __table_args__ = (
        UniqueConstraint("agent_run_id", "sequence", name="uq_runtime_events_run_sequence"),
        Index("idx_runtime_events_run_sequence", "agent_run_id", "sequence"),
        Index("idx_runtime_events_trace_id", "trace_id"),
    )

    agent_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_run_steps.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    span_id: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_span_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default=RuntimeActorType.RUNTIME)
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


__all__ = ["RuntimeEventRecord"]
