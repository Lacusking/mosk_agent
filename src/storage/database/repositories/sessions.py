"""Session 与消息历史持久化访问。"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import Select
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contracts.runtime import ModelContentBlock
from src.contracts.sessions import Session
from src.contracts.sessions import SessionMessage
from src.contracts.sessions import SessionMessageRole
from src.contracts.sessions import SessionStatus
from src.core.utils import generate_uuid7
from src.storage.database.models.sessions import SessionMessageRecord
from src.storage.database.models.sessions import SessionRecord
from src.storage.database.time import aware_utc_from_db

_CONTENT_ADAPTER: TypeAdapter[list[ModelContentBlock]] = TypeAdapter(list[ModelContentBlock])


def _uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


def _new_uuid7() -> UUID:
    return UUID(generate_uuid7())


def _content_to_json(content: Sequence[ModelContentBlock]) -> list[dict[str, Any]]:
    return [block.model_dump(mode="json") for block in content]


def _record_to_session(record: SessionRecord) -> Session:
    return Session(
        session_id=str(record.id),
        status=SessionStatus(record.status),
        title=record.title,
        metadata=record.metadata_,
        last_message_sequence=record.last_message_sequence,
        created_at=aware_utc_from_db(record.created_at),
        updated_at=aware_utc_from_db(record.updated_at),
    )


def _record_to_message(record: SessionMessageRecord) -> SessionMessage:
    return SessionMessage(
        message_id=str(record.id),
        session_id=str(record.session_id),
        agent_run_id=str(record.agent_run_id) if record.agent_run_id else None,
        sequence=record.sequence,
        role=SessionMessageRole(record.role),
        content=_CONTENT_ADAPTER.validate_python(record.content),
        metadata=record.metadata_,
        created_at=aware_utc_from_db(record.created_at),
        updated_at=aware_utc_from_db(record.updated_at),
    )


class SessionRepository:
    """封装 Session 与可见消息历史的 SQLAlchemy 操作。"""

    def __init__(self, db: AsyncSession) -> None:
        """初始化 repository。

        Args:
            db: 当前请求或事务中的异步数据库会话。
        """
        self._db = db

    async def create_session(
        self,
        *,
        session_id: str | UUID | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """创建会话。

        Args:
            session_id: 可选外部指定 session id。
            title: 可选展示标题。
            metadata: 可审计的安全元数据。

        Returns:
            创建后的 Session 契约对象。
        """
        record = SessionRecord(
            id=_uuid(session_id) if session_id else _new_uuid7(),
            title=title,
            metadata_=metadata or {},
        )
        self._db.add(record)
        await self._db.flush()
        await self._db.refresh(record)
        return _record_to_session(record)

    async def get_session(self, session_id: str | UUID) -> Session | None:
        """按 id 获取会话。

        Args:
            session_id: 会话 id。

        Returns:
            存在时返回 Session，否则返回 None。
        """
        record = await self._db.get(SessionRecord, _uuid(session_id))
        return _record_to_session(record) if record else None

    async def append_message(
        self,
        *,
        session_id: str | UUID,
        role: SessionMessageRole,
        content: Sequence[ModelContentBlock],
        message_id: str | UUID | None = None,
        agent_run_id: str | UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SessionMessage:
        """向会话追加一条可见消息并分配递增 sequence。

        Args:
            session_id: 会话 id。
            role: 可见消息角色。
            content: 消息内容块。
            message_id: 可选外部指定 message id。
            agent_run_id: 关联的 AgentRun id。
            metadata: 安全元数据。

        Returns:
            新增的 SessionMessage 契约对象。

        Raises:
            LookupError: 会话不存在。
        """
        session_uuid = _uuid(session_id)
        session_record = await self._db.get(SessionRecord, session_uuid, with_for_update=True)
        if session_record is None:
            raise LookupError("session not found")

        next_sequence = session_record.last_message_sequence + 1
        session_record.last_message_sequence = next_sequence
        record = SessionMessageRecord(
            id=_uuid(message_id) if message_id else _new_uuid7(),
            session_id=session_uuid,
            agent_run_id=_uuid(agent_run_id) if agent_run_id else None,
            sequence=next_sequence,
            role=role.value,
            content=_content_to_json(content),
            metadata_=metadata or {},
        )
        self._db.add(record)
        await self._db.flush()
        await self._db.refresh(record)
        return _record_to_message(record)

    async def list_messages(
        self,
        session_id: str | UUID,
        *,
        through_sequence: int | None = None,
    ) -> list[SessionMessage]:
        """按 sequence 升序读取会话可见消息。

        Args:
            session_id: 会话 id。
            through_sequence: 可选上下文水位；存在时只读取该序号及之前消息。

        Returns:
            有序 SessionMessage 列表。
        """
        statement: Select[tuple[SessionMessageRecord]] = select(SessionMessageRecord).where(
            SessionMessageRecord.session_id == _uuid(session_id)
        )
        if through_sequence is not None:
            statement = statement.where(SessionMessageRecord.sequence <= through_sequence)
        statement = statement.order_by(SessionMessageRecord.sequence.asc())
        result = await self._db.execute(statement)
        return [_record_to_message(record) for record in result.scalars().all()]


__all__ = ["SessionRepository"]
