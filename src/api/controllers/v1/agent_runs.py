"""AgentRun API 路由。"""

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi import Request
from starlette.responses import StreamingResponse

from src.agent_runs import AgentRunManager
from src.api.controllers.dep.auth import InternalAuth
from src.api.controllers.dep.db_session import CurrentSessionTransaction
from src.api.response import response_base
from src.contracts.agent_runs import AgentRun
from src.contracts.agent_runs import AgentRunEventsResponse
from src.contracts.agent_runs import AgentRunResponse
from src.contracts.agent_runs import AgentRunStreamEvent
from src.contracts.agent_runs import CreateAgentRunRequest
from src.contracts.runtime import PatternSelectedPayload
from src.contracts.runtime import RuntimeEventType
from src.core.config import settings
from src.exceptions import NotFoundError
from src.patterns import PatternSelection
from src.patterns import PatternSelector
from src.patterns import default_pattern_registry
from src.runtime import AgentRunExecutionResult
from src.runtime import AgentRuntimeKernel
from src.runtime import CancellationRegistry
from src.runtime import CancellationTrigger
from src.runtime import build_mock_model_invoker
from src.runtime import format_sse
from src.sessions import SessionManager
from src.storage.database.repositories.agent_runs import AgentRunRepository
from src.storage.database.repositories.events import RuntimeEventRepository
from src.storage.database.repositories.sessions import SessionRepository
from src.tools import MockToolActionExecutor

router = APIRouter(dependencies=[InternalAuth])
_cancellations = CancellationRegistry()


@router.post("/agent-runs", response_model=None)
async def create_agent_run(
    request: CreateAgentRunRequest,
    http_request: Request,
    db: CurrentSessionTransaction,
) -> dict | StreamingResponse:
    """创建并执行 AgentRun。

    Args:
        request: 创建并执行 AgentRun 的请求。
        http_request: FastAPI 请求对象，用于 SSE 断连检测。
        db: 事务数据库会话。

    Returns:
        普通统一响应或 SSE response。
    """
    session_manager = SessionManager(SessionRepository(db))
    await session_manager.require_session(request.session_id)
    patterns = default_pattern_registry()
    selection = PatternSelector(
        registry=patterns,
        config=settings.agent_runtime,
    ).select(mode=request.mode, requested_pattern=request.requested_pattern)
    input_message = await session_manager.append_user_text(
        session_id=request.session_id,
        text=request.input,
    )
    run_manager = AgentRunManager(
        repository=AgentRunRepository(db),
        config=settings.agent_runtime,
    )
    agent_run = await run_manager.create_run(
        session_id=request.session_id,
        input_message_id=input_message.message_id,
        mode=request.mode,
        requested_pattern=request.requested_pattern,
        active_pattern=selection.pattern,
        context_message_sequence=input_message.sequence,
    )
    await _append_pattern_selected(db, agent_run, selection)
    kernel = _build_kernel(
        db=db,
        patterns=patterns,
        run_manager=run_manager,
        session_manager=session_manager,
    )
    token = _cancellations.get_or_create(agent_run.agent_run_id)
    if request.stream:
        return StreamingResponse(
            _sse_events(
                kernel=kernel,
                agent_run=agent_run,
                http_request=http_request,
                token=token,
            ),
            media_type="text/event-stream",
        )

    result = await kernel.execute(agent_run, cancellation_token=token)
    _cancellations.remove(agent_run.agent_run_id)
    return response_base.success(data=AgentRunResponse(agent_run=result.agent_run)).model_dump()


@router.get("/agent-runs/{agent_run_id}")
async def get_agent_run(agent_run_id: str, db: CurrentSessionTransaction) -> dict:
    """读取 AgentRun 状态。

    Args:
        agent_run_id: AgentRun id。
        db: 事务数据库会话。

    Returns:
        统一响应结构。
    """
    repository = AgentRunRepository(db)
    agent_run = await repository.get_run(agent_run_id)
    if agent_run is None:
        raise NotFoundError(msg="AgentRun 不存在", data={"agent_run_id": agent_run_id})
    return response_base.success(data=AgentRunResponse(agent_run=agent_run)).model_dump()


@router.get("/agent-runs/{agent_run_id}/events")
async def get_agent_run_events(agent_run_id: str, db: CurrentSessionTransaction) -> dict:
    """读取 AgentRun 事件时间线。

    Args:
        agent_run_id: AgentRun id。
        db: 事务数据库会话。

    Returns:
        统一响应结构。
    """
    repository = AgentRunRepository(db)
    if await repository.get_run(agent_run_id) is None:
        raise NotFoundError(msg="AgentRun 不存在", data={"agent_run_id": agent_run_id})
    events = await RuntimeEventRepository(db).list_for_run(agent_run_id)
    return response_base.success(
        data=AgentRunEventsResponse(
            agent_run_id=agent_run_id,
            events=[event.model_dump(mode="json") for event in events],
        )
    ).model_dump()


@router.post("/agent-runs/{agent_run_id}/cancel")
async def cancel_agent_run(agent_run_id: str, db: CurrentSessionTransaction) -> dict:
    """取消 AgentRun。

    Args:
        agent_run_id: AgentRun id。
        db: 事务数据库会话。

    Returns:
        统一响应结构。
    """
    _cancellations.cancel(agent_run_id, CancellationTrigger.EXPLICIT)
    manager = AgentRunManager(
        repository=AgentRunRepository(db),
        config=settings.agent_runtime,
    )
    agent_run = await manager.cancel_run(agent_run_id)
    if agent_run is None:
        raise NotFoundError(msg="AgentRun 不存在或已终态", data={"agent_run_id": agent_run_id})
    return response_base.success(data=AgentRunResponse(agent_run=agent_run)).model_dump()


def _build_kernel(
    *,
    db: CurrentSessionTransaction,
    patterns,
    run_manager: AgentRunManager,
    session_manager: SessionManager,
) -> AgentRuntimeKernel:
    """构造 AgentRuntimeKernel。

    Args:
        db: 数据库会话。
        patterns: pattern 注册表。
        run_manager: AgentRun manager。
        session_manager: Session manager。

    Returns:
        runtime kernel。
    """
    return AgentRuntimeKernel(
        patterns=patterns,
        run_manager=run_manager,
        session_manager=session_manager,
        event_repository=RuntimeEventRepository(db),
        model_invoker=build_mock_model_invoker(),
        tool_executor=MockToolActionExecutor(),
        config=settings.agent_runtime,
    )


async def _append_pattern_selected(
    db: CurrentSessionTransaction,
    agent_run: AgentRun,
    selection: PatternSelection,
) -> None:
    """写入 pattern selected 事件。

    Args:
        db: 数据库会话。
        agent_run: 已创建 run。
        selection: selector 结果。
    """
    await RuntimeEventRepository(db).append(
        agent_run_id=agent_run.agent_run_id,
        session_id=agent_run.session_id,
        event_type=RuntimeEventType.PATTERN_SELECTED,
        trace_id=agent_run.trace_id,
        span_id=agent_run.agent_run_id,
        payload=PatternSelectedPayload(
            agent_run_id=agent_run.agent_run_id,
            pattern=selection.pattern,
            selection_source=selection.source.value,
            mode=agent_run.mode.value,
        ),
    )


async def _sse_events(
    *,
    kernel: AgentRuntimeKernel,
    agent_run: AgentRun,
    http_request: Request,
    token,
) -> AsyncIterator[str]:
    """将 kernel 事件格式化为 SSE。

    Args:
        kernel: runtime kernel。
        agent_run: 已创建 run。
        http_request: FastAPI 请求对象。
        token: 取消令牌。

    Yields:
        SSE 文本片段。
    """
    try:
        async for event in kernel.stream(agent_run, cancellation_token=token):
            if await http_request.is_disconnected():
                token.cancel(CancellationTrigger.SSE_DISCONNECT)
            if isinstance(event, AgentRunExecutionResult):
                _cancellations.remove(agent_run.agent_run_id)
                continue
            yield format_sse(event)
    except asyncio.CancelledError:
        token.cancel(CancellationTrigger.SSE_DISCONNECT)
        raise


__all__ = ["router"]
