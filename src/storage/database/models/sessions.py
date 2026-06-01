"""Session 与 SessionMessage 的 ORM 映射。"""

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

from src.contracts.sessions import SessionMessageRole
from src.contracts.sessions import SessionStatus
from src.storage.database import PkModel
from src.storage.database import TimestampedModel


class SessionRecord(PkModel, TimestampedModel):
    """sessions 表 ORM 记录。"""

    __tablename__ = "sessions"
    __table_args__ = (Index("idx_sessions_status_updated_at", "status", "updated_at"),)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default=SessionStatus.ACTIVE)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    last_message_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SessionMessageRecord(PkModel, TimestampedModel):
    """session_messages 表 ORM 记录。"""

    __tablename__ = "session_messages"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence", name="uq_session_messages_session_sequence"),
        Index("idx_session_messages_session_sequence", "session_id", "sequence"),
    )

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=SessionMessageRole.USER)
    content: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )


__all__ = ["SessionMessageRecord", "SessionRecord"]
