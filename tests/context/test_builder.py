"""ContextBuilder 测试。"""

from datetime import UTC
from datetime import datetime

import pytest

from src.context import ContextBuilder
from src.context import ContextStrategyPipeline
from src.contracts.agent_runs import AgentMode
from src.contracts.agent_runs import AgentRun
from src.contracts.agent_runs import AgentRunStatus
from src.contracts.runtime import TextContentBlock
from src.contracts.sessions import SessionMessage
from src.contracts.sessions import SessionMessageRole
from src.core.config import AgentRuntimeConfig


class _FakeSessionManager:
    def __init__(self, messages: list[SessionMessage]) -> None:
        self.messages = messages
        self.calls: list[dict[str, object]] = []

    async def visible_history(
        self,
        *,
        session_id: str,
        through_sequence: int | None = None,
        limit: int | None = None,
    ) -> list[SessionMessage]:
        self.calls.append(
            {
                "session_id": session_id,
                "through_sequence": through_sequence,
                "limit": limit,
            }
        )
        messages = [
            message
            for message in self.messages
            if through_sequence is None or message.sequence <= through_sequence
        ]
        if limit is not None:
            messages = messages[-limit:]
        return messages


def _session_message(sequence: int) -> SessionMessage:
    now = datetime.now(UTC)
    return SessionMessage(
        message_id=f"message-{sequence}",
        session_id="session-1",
        sequence=sequence,
        role=SessionMessageRole.USER,
        content=[TextContentBlock(text=f"hello {sequence}")],
        created_at=now,
        updated_at=now,
    )


def _agent_run() -> AgentRun:
    now = datetime.now(UTC)
    return AgentRun(
        agent_run_id="run-1",
        session_id="session-1",
        input_message_id="message-10",
        status=AgentRunStatus.CREATED,
        mode=AgentMode.CHAT,
        active_pattern="single_turn",
        context_message_sequence=10,
        trace_id="trace-1",
        max_steps=12,
        timeout_seconds=120,
        retry_limit=1,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_builder_window_reads_recent_messages_within_watermark() -> None:
    """builder 按水位和 window 配置读取最近消息。"""
    manager = _FakeSessionManager([_session_message(sequence) for sequence in range(1, 21)])
    config = AgentRuntimeConfig(
        CONTEXT_WINDOW_MESSAGES=6,
        CONTEXT_SNIP_THRESHOLD_MESSAGES=6,
        CONTEXT_SNIP_HEAD_MESSAGES=1,
        CONTEXT_SNIP_TAIL_MESSAGES=1,
    )
    builder = ContextBuilder(
        session_manager=manager,  # type: ignore[arg-type]
        config=config,
        pipeline=ContextStrategyPipeline(),
    )

    bundle = await builder.build(_agent_run())

    assert manager.calls == [
        {"session_id": "session-1", "through_sequence": 10, "limit": 6}
    ]
    assert [item.sequence for item in bundle.session_messages] == [5, 6, 7, 8, 9, 10]
    assert bundle.tool_observations == []
    assert [message.content[0].text for message in bundle.to_model_messages()] == [
        "hello 5",
        "hello 6",
        "hello 7",
        "hello 8",
        "hello 9",
        "hello 10",
    ]


@pytest.mark.asyncio
async def test_builder_pipeline_can_compact_context() -> None:
    """builder 输出会经过策略管线处理。"""
    manager = _FakeSessionManager([_session_message(sequence) for sequence in range(1, 11)])
    config = AgentRuntimeConfig(
        CONTEXT_WINDOW_MESSAGES=10,
        CONTEXT_SNIP_THRESHOLD_MESSAGES=4,
        CONTEXT_SNIP_HEAD_MESSAGES=1,
        CONTEXT_SNIP_TAIL_MESSAGES=2,
    )

    bundle = await ContextBuilder(
        session_manager=manager,  # type: ignore[arg-type]
        config=config,
    ).build(_agent_run())

    assert [item.sequence for item in bundle.session_messages] == [1, 8, 9, 10]
