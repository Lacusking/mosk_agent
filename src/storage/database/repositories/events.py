"""RuntimeEvent 事实事件存储。"""

from typing import Any
from uuid import UUID

from sqlalchemy import Select
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.utils import generate_uuid7
from src.contracts.runtime import RuntimeActorType
from src.contracts.runtime import RuntimeEvent
from src.contracts.runtime import RuntimeEventPayload
from src.contracts.runtime import RuntimeEventType
from src.storage.database.models.events import RuntimeEventRecord


def _uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


def _new_uuid7() -> UUID:
    return UUID(generate_uuid7())


def _record_to_event(record: RuntimeEventRecord) -> RuntimeEvent:
    return RuntimeEvent.model_validate(
        {
            "event_id": str(record.id),
            "event_type": record.event_type,
            "event_version": record.event_version,
            "agent_run_id": str(record.agent_run_id),
            "step_id": str(record.step_id) if record.step_id else None,
            "session_id": str(record.session_id) if record.session_id else None,
            "trace_id": record.trace_id,
            "span_id": record.span_id,
            "parent_span_id": record.parent_span_id,
            "actor_type": record.actor_type,
            "actor_id": record.actor_id,
            "payload": record.payload,
            "created_at": record.created_at,
        }
    )


class RuntimeEventRepository:
    """提供 runtime_events 追加与 timeline 查询。"""

    def __init__(self, db: AsyncSession) -> None:
        """初始化 repository。

        Args:
            db: 当前请求或事务中的异步数据库会话。
        """
        self._db = db

    async def append(
        self,
        *,
        agent_run_id: str | UUID,
        event_type: RuntimeEventType,
        payload: RuntimeEventPayload,
        trace_id: str,
        span_id: str,
        event_id: str | UUID | None = None,
        step_id: str | UUID | None = None,
        session_id: str | UUID | None = None,
        parent_span_id: str | None = None,
        actor_type: RuntimeActorType = RuntimeActorType.RUNTIME,
        actor_id: str | None = None,
        event_version: int = 1,
    ) -> RuntimeEvent:
        """追加一条运行事实事件。

        Args:
            agent_run_id: AgentRun id。
            event_type: 事件类型。
            payload: 类型化安全 payload。
            trace_id: trace id。
            span_id: span id。
            event_id: 可选外部指定事件 id。
            step_id: 可选关联 step id。
            session_id: 可选关联 session id。
            parent_span_id: 可选父 span id。
            actor_type: 事件 actor 类型。
            actor_id: 可选 actor id。
            event_version: 事件版本。

        Returns:
            已追加的 RuntimeEvent。
        """
        run_uuid = _uuid(agent_run_id)
        sequence_result = await self._db.execute(
            select(func.coalesce(func.max(RuntimeEventRecord.sequence), 0)).where(
                RuntimeEventRecord.agent_run_id == run_uuid
            )
        )
        sequence = int(sequence_result.scalar_one()) + 1
        record = RuntimeEventRecord(
            id=_uuid(event_id) if event_id else _new_uuid7(),
            agent_run_id=run_uuid,
            step_id=_uuid(step_id) if step_id else None,
            session_id=_uuid(session_id) if session_id else None,
            event_type=event_type.value,
            event_version=event_version,
            sequence=sequence,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            actor_type=actor_type.value,
            actor_id=actor_id,
            payload=payload.model_dump(mode="json"),
        )
        self._db.add(record)
        await self._db.flush()
        await self._db.refresh(record)
        return _record_to_event(record)

    async def list_for_run(self, agent_run_id: str | UUID) -> list[RuntimeEvent]:
        """按 sequence 升序读取 AgentRun 事件时间线。

        Args:
            agent_run_id: AgentRun id。

        Returns:
            有序 RuntimeEvent 列表。
        """
        statement: Select[tuple[RuntimeEventRecord]] = (
            select(RuntimeEventRecord)
            .where(RuntimeEventRecord.agent_run_id == _uuid(agent_run_id))
            .order_by(RuntimeEventRecord.sequence.asc())
        )
        result = await self._db.execute(statement)
        return [_record_to_event(record) for record in result.scalars().all()]

    @staticmethod
    def safe_payload_text(payload: dict[str, Any]) -> str:
        """生成不含完整敏感正文的 payload 诊断文本。

        Args:
            payload: 已进入事件表的 payload。

        Returns:
            用于日志诊断的字符串。
        """
        return str(payload)


__all__ = ["RuntimeEventRepository"]
