"""AgentRun 与 step 的持久化访问。"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.contracts.agent_runs import AgentMode
from src.contracts.agent_runs import AgentRun
from src.contracts.agent_runs import AgentRunFinishReason
from src.contracts.agent_runs import AgentRunStatus
from src.contracts.agent_runs import AgentRunStep
from src.contracts.agent_runs import AgentRunStepKind
from src.contracts.agent_runs import AgentRunStepStatus
from src.core.utils import generate_uuid7
from src.core.utils import utc_now
from src.storage.database.models.agent_runs import AgentRunRecord
from src.storage.database.models.agent_runs import AgentRunStepRecord

ACTIVE_RUN_STATUSES = frozenset({AgentRunStatus.CREATED.value, AgentRunStatus.RUNNING.value})
TERMINAL_RUN_STATUSES = frozenset(
    {
        AgentRunStatus.COMPLETED.value,
        AgentRunStatus.FAILED.value,
        AgentRunStatus.CANCELLED.value,
    }
)

_ALLOWED_RUN_TRANSITIONS: dict[AgentRunStatus, frozenset[AgentRunStatus]] = {
    AgentRunStatus.CREATED: frozenset(
        {
            AgentRunStatus.RUNNING,
            AgentRunStatus.COMPLETED,
            AgentRunStatus.FAILED,
            AgentRunStatus.CANCELLED,
        }
    ),
    AgentRunStatus.RUNNING: frozenset(
        {
            AgentRunStatus.COMPLETED,
            AgentRunStatus.FAILED,
            AgentRunStatus.CANCELLED,
        }
    ),
    AgentRunStatus.COMPLETED: frozenset(),
    AgentRunStatus.FAILED: frozenset(),
    AgentRunStatus.CANCELLED: frozenset(),
}


def _uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


def _new_uuid7() -> UUID:
    return UUID(generate_uuid7())


def _ensure_run_transition(current: AgentRunStatus, target: AgentRunStatus) -> None:
    """校验 AgentRun 持久化状态转换。

    Args:
        current: 当前状态。
        target: 目标状态。

    Raises:
        ValueError: 状态转换非法。
    """
    if target not in _ALLOWED_RUN_TRANSITIONS[current]:
        raise ValueError(f"非法 AgentRun 状态转换: {current.value} -> {target.value}")


def _record_to_run(record: AgentRunRecord) -> AgentRun:
    return AgentRun(
        agent_run_id=str(record.id),
        session_id=str(record.session_id),
        input_message_id=str(record.input_message_id),
        status=AgentRunStatus(record.status),
        mode=AgentMode(record.mode),
        requested_pattern=record.requested_pattern,
        active_pattern=record.active_pattern,
        context_message_sequence=record.context_message_sequence,
        trace_id=record.trace_id,
        finish_reason=(
            AgentRunFinishReason(record.finish_reason) if record.finish_reason else None
        ),
        error_type=record.error_type,
        max_steps=record.max_steps,
        timeout_seconds=record.timeout_seconds,
        retry_limit=record.retry_limit,
        created_at=record.created_at,
        updated_at=record.updated_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
    )


def _record_to_step(record: AgentRunStepRecord) -> AgentRunStep:
    return AgentRunStep(
        step_id=str(record.id),
        agent_run_id=str(record.agent_run_id),
        sequence=record.sequence,
        kind=AgentRunStepKind(record.kind),
        status=AgentRunStepStatus(record.status),
        pattern=record.pattern,
        invocation_id=record.invocation_id,
        safe_input=record.safe_input,
        safe_output=record.safe_output,
        error_type=record.error_type,
        created_at=record.created_at,
        updated_at=record.updated_at,
        completed_at=record.completed_at,
    )


class AgentRunRepository:
    """封装 AgentRun 与 step 的 SQLAlchemy 操作。"""

    def __init__(self, db: AsyncSession) -> None:
        """初始化 repository。

        Args:
            db: 当前请求或事务中的异步数据库会话。
        """
        self._db = db

    async def create_run(
        self,
        *,
        session_id: str | UUID,
        input_message_id: str | UUID,
        mode: AgentMode,
        active_pattern: str,
        context_message_sequence: int,
        trace_id: str,
        max_steps: int,
        timeout_seconds: float,
        retry_limit: int,
        agent_run_id: str | UUID | None = None,
        requested_pattern: str | None = None,
        status: AgentRunStatus = AgentRunStatus.CREATED,
        started_at: datetime | None = None,
    ) -> AgentRun:
        """创建 AgentRun 记录。

        Args:
            session_id: 所属 Session id。
            input_message_id: 触发本次运行的用户消息 id。
            mode: 请求 mode。
            active_pattern: 选定 pattern 快照。
            context_message_sequence: 本次运行的上下文水位。
            trace_id: 诊断 trace id。
            max_steps: 最大 step 数。
            timeout_seconds: 运行超时秒数。
            retry_limit: 模型调用重试次数。
            agent_run_id: 可选外部指定 run id。
            requested_pattern: 用户显式请求的 pattern。
            status: 初始状态。
            started_at: 开始时间。

        Returns:
            创建后的 AgentRun 契约对象。
        """
        record = AgentRunRecord(
            id=_uuid(agent_run_id) if agent_run_id else _new_uuid7(),
            session_id=_uuid(session_id),
            input_message_id=_uuid(input_message_id),
            status=status.value,
            mode=mode.value,
            requested_pattern=requested_pattern,
            active_pattern=active_pattern,
            context_message_sequence=context_message_sequence,
            trace_id=trace_id,
            max_steps=max_steps,
            timeout_seconds=timeout_seconds,
            retry_limit=retry_limit,
            started_at=started_at,
        )
        self._db.add(record)
        await self._db.flush()
        await self._db.refresh(record)
        return _record_to_run(record)

    async def get_run(self, agent_run_id: str | UUID, *, for_update: bool = False) -> AgentRun | None:
        """按 id 获取 AgentRun。

        Args:
            agent_run_id: AgentRun id。
            for_update: 是否锁定记录用于状态转换。

        Returns:
            存在时返回 AgentRun，否则返回 None。
        """
        statement = select(AgentRunRecord).where(AgentRunRecord.id == _uuid(agent_run_id))
        if for_update:
            statement = statement.with_for_update()
        result = await self._db.execute(statement)
        record = result.scalar_one_or_none()
        return _record_to_run(record) if record else None

    async def has_active_run(self, session_id: str | UUID) -> bool:
        """检查指定 Session 是否已有活动 AgentRun。

        Args:
            session_id: Session id。

        Returns:
            存在 created/running run 时返回 True。
        """
        statement = select(AgentRunRecord.id).where(
            AgentRunRecord.session_id == _uuid(session_id),
            AgentRunRecord.status.in_(ACTIVE_RUN_STATUSES),
        )
        result = await self._db.execute(statement)
        return result.first() is not None

    async def transition_run(
        self,
        *,
        agent_run_id: str | UUID,
        status: AgentRunStatus,
        finish_reason: AgentRunFinishReason | None = None,
        error_type: str | None = None,
        completed_at: datetime | None = None,
    ) -> AgentRun | None:
        """将活动 AgentRun 转换为新状态。

        Args:
            agent_run_id: AgentRun id。
            status: 目标状态。
            finish_reason: 终态原因。
            error_type: 失败分类。
            completed_at: 终态时间。

        Returns:
            更新后的 AgentRun；不存在或已终态则返回 None。
        """
        record = await self._load_run_record(agent_run_id, for_update=True)
        if record is None or record.status in TERMINAL_RUN_STATUSES:
            return None
        _ensure_run_transition(AgentRunStatus(record.status), status)
        record.status = status.value
        if status == AgentRunStatus.RUNNING and record.started_at is None:
            record.started_at = utc_now().replace(tzinfo=None)
        if status in {
            AgentRunStatus.COMPLETED,
            AgentRunStatus.FAILED,
            AgentRunStatus.CANCELLED,
        }:
            record.finish_reason = finish_reason.value if finish_reason else None
            record.error_type = error_type
            record.completed_at = completed_at or utc_now().replace(tzinfo=None)
        await self._db.flush()
        await self._db.refresh(record)
        return _record_to_run(record)

    async def create_step(
        self,
        *,
        agent_run_id: str | UUID,
        kind: AgentRunStepKind,
        pattern: str,
        invocation_id: str | None = None,
        safe_input: dict[str, Any] | None = None,
        step_id: str | UUID | None = None,
    ) -> AgentRunStep:
        """为 AgentRun 创建下一条 step。

        Args:
            agent_run_id: AgentRun id。
            kind: step 类型。
            pattern: 当前 pattern。
            invocation_id: 可选模型 invocation id。
            safe_input: 脱敏后的输入摘要。
            step_id: 可选外部指定 step id。

        Returns:
            创建后的 AgentRunStep 契约对象。
        """
        run_uuid = _uuid(agent_run_id)
        sequence_result = await self._db.execute(
            select(func.coalesce(func.max(AgentRunStepRecord.sequence), 0)).where(
                AgentRunStepRecord.agent_run_id == run_uuid
            )
        )
        sequence = int(sequence_result.scalar_one()) + 1
        record = AgentRunStepRecord(
            id=_uuid(step_id) if step_id else _new_uuid7(),
            agent_run_id=run_uuid,
            sequence=sequence,
            kind=kind.value,
            status=AgentRunStepStatus.RUNNING.value,
            pattern=pattern,
            invocation_id=invocation_id,
            safe_input=safe_input or {},
            safe_output={},
        )
        self._db.add(record)
        await self._db.flush()
        await self._db.refresh(record)
        return _record_to_step(record)

    async def complete_step(
        self,
        *,
        step_id: str | UUID,
        status: AgentRunStepStatus,
        safe_output: dict[str, Any] | None = None,
        error_type: str | None = None,
    ) -> AgentRunStep | None:
        """提交 step 终态。

        Args:
            step_id: step id。
            status: step 终态。
            safe_output: 脱敏输出摘要。
            error_type: 失败分类。

        Returns:
            更新后的 step；不存在时返回 None。
        """
        record = await self._db.get(AgentRunStepRecord, _uuid(step_id), with_for_update=True)
        if record is None:
            return None
        record.status = status.value
        record.safe_output = safe_output or {}
        record.error_type = error_type
        record.completed_at = utc_now().replace(tzinfo=None)
        await self._db.flush()
        await self._db.refresh(record)
        return _record_to_step(record)

    async def list_steps(self, agent_run_id: str | UUID) -> list[AgentRunStep]:
        """按 sequence 升序读取 run steps。

        Args:
            agent_run_id: AgentRun id。

        Returns:
            有序 AgentRunStep 列表。
        """
        statement: Select[tuple[AgentRunStepRecord]] = (
            select(AgentRunStepRecord)
            .where(AgentRunStepRecord.agent_run_id == _uuid(agent_run_id))
            .order_by(AgentRunStepRecord.sequence.asc())
        )
        result = await self._db.execute(statement)
        return [_record_to_step(record) for record in result.scalars().all()]

    async def set_active_pattern(
        self,
        *,
        agent_run_id: str | UUID,
        active_pattern: str,
    ) -> AgentRun | None:
        """更新 AgentRun 当前 active pattern。

        Args:
            agent_run_id: AgentRun id。
            active_pattern: 新的 active pattern。

        Returns:
            更新后的 AgentRun；不存在或已终态则返回 None。
        """
        record = await self._load_run_record(agent_run_id, for_update=True)
        if record is None or record.status in TERMINAL_RUN_STATUSES:
            return None
        record.active_pattern = active_pattern
        await self._db.flush()
        await self._db.refresh(record)
        return _record_to_run(record)

    async def _load_run_record(
        self,
        agent_run_id: str | UUID,
        *,
        for_update: bool,
    ) -> AgentRunRecord | None:
        statement = select(AgentRunRecord).where(AgentRunRecord.id == _uuid(agent_run_id))
        if for_update:
            statement = statement.with_for_update()
        result = await self._db.execute(statement)
        return result.scalar_one_or_none()


__all__ = ["ACTIVE_RUN_STATUSES", "AgentRunRepository", "TERMINAL_RUN_STATUSES"]
