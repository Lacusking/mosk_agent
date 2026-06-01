"""AgentRun SSE 输出构造。"""

import json

from src.contracts.agent_runs import AgentMode
from src.contracts.agent_runs import AgentRunFinishReason
from src.contracts.agent_runs import AgentRunStreamEvent
from src.contracts.agent_runs import OutputTextDeltaStreamPayload
from src.contracts.agent_runs import RunStartedStreamPayload
from src.contracts.agent_runs import RunTerminalStreamPayload


def run_started_event(
    *,
    agent_run_id: str,
    session_id: str,
    mode: AgentMode,
    pattern: str,
    trace_id: str,
) -> AgentRunStreamEvent:
    """构造 run.started 事件。

    Args:
        agent_run_id: AgentRun id。
        session_id: Session id。
        mode: 请求 mode。
        pattern: 已选 pattern。
        trace_id: trace id。

    Returns:
        AgentRunStreamEvent。
    """
    return AgentRunStreamEvent(
        event="run.started",
        payload=RunStartedStreamPayload(
            agent_run_id=agent_run_id,
            session_id=session_id,
            mode=mode,
            pattern=pattern,
            trace_id=trace_id,
        ),
    )


def output_text_delta_event(
    *,
    agent_run_id: str,
    sequence: int,
    delta: str,
) -> AgentRunStreamEvent:
    """构造 output.text.delta 事件。

    Args:
        agent_run_id: AgentRun id。
        sequence: 输出增量序号。
        delta: 文本增量。

    Returns:
        AgentRunStreamEvent。
    """
    return AgentRunStreamEvent(
        event="output.text.delta",
        payload=OutputTextDeltaStreamPayload(
            agent_run_id=agent_run_id,
            sequence=sequence,
            delta=delta,
        ),
    )


def terminal_event(
    *,
    agent_run_id: str,
    status: str,
    finish_reason: AgentRunFinishReason | None = None,
    error_type: str | None = None,
) -> AgentRunStreamEvent:
    """构造 run 终态 SSE 事件。

    Args:
        agent_run_id: AgentRun id。
        status: completed / failed / cancelled。
        finish_reason: 终止原因。
        error_type: 失败类型。

    Returns:
        AgentRunStreamEvent。
    """
    return AgentRunStreamEvent(
        event=f"run.{status}",
        payload=RunTerminalStreamPayload(
            agent_run_id=agent_run_id,
            status=status,  # type: ignore[arg-type]
            finish_reason=finish_reason,
            error_type=error_type,
        ),
    )


def format_sse(event: AgentRunStreamEvent) -> str:
    """格式化为 text/event-stream 片段。

    Args:
        event: AgentRun stream 事件。

    Returns:
        SSE 文本片段。
    """
    data = event.payload.model_dump(mode="json", exclude_none=True)
    return f"event: {event.event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


__all__ = ["format_sse", "output_text_delta_event", "run_started_event", "terminal_event"]
