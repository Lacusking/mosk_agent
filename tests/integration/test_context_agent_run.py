"""上下文装配与 AgentRun 集成测试。"""

from datetime import UTC
from datetime import datetime

import pytest

from src.context import ContextBuilder
from src.contracts.agent_runs import AgentMode
from src.contracts.agent_runs import AgentRun
from src.contracts.agent_runs import AgentRunFinishReason
from src.contracts.agent_runs import AgentRunStatus
from src.contracts.agent_runs import AgentRunStep
from src.contracts.agent_runs import AgentRunStepKind
from src.contracts.agent_runs import AgentRunStepStatus
from src.contracts.patterns import CompleteAction
from src.contracts.patterns import PatternRuntimeState
from src.contracts.runtime import TextContentBlock
from src.contracts.sessions import SessionMessage
from src.contracts.sessions import SessionMessageRole
from src.core.config import AgentRuntimeConfig
from src.runtime import AgentRunExecutionResult
from src.runtime import AgentRuntimeKernel


def _now() -> datetime:
    return datetime.now(UTC)


def _agent_run() -> AgentRun:
    now = _now()
    return AgentRun(
        agent_run_id="run-1",
        session_id="session-1",
        input_message_id="message-10",
        status=AgentRunStatus.CREATED,
        mode=AgentMode.CHAT,
        active_pattern="single_turn",
        context_message_sequence=10,
        trace_id="trace-1",
        max_steps=6,
        timeout_seconds=120,
        retry_limit=1,
        created_at=now,
        updated_at=now,
    )


def _session_message(sequence: int) -> SessionMessage:
    now = _now()
    return SessionMessage(
        message_id=f"message-{sequence}",
        session_id="session-1",
        sequence=sequence,
        role=SessionMessageRole.USER if sequence % 2 else SessionMessageRole.ASSISTANT,
        content=[TextContentBlock(text=f"message {sequence}")],
        created_at=now,
        updated_at=now,
    )


class _SessionManager:
    def __init__(self) -> None:
        self.messages = [_session_message(sequence) for sequence in range(1, 13)]
        self.final_messages: list[str] = []

    async def visible_history(
        self,
        *,
        session_id: str,
        through_sequence: int | None = None,
        limit: int | None = None,
    ) -> list[SessionMessage]:
        messages = [
            message
            for message in self.messages
            if through_sequence is None or message.sequence <= through_sequence
        ]
        if limit is not None:
            messages = messages[-limit:]
        return messages

    async def append_final_assistant_text(
        self,
        *,
        session_id: str,
        agent_run_id: str,
        text: str,
    ) -> None:
        self.final_messages.append(text)


class _RunManager:
    def __init__(self) -> None:
        self.step_sequence = 0

    async def mark_running(self, agent_run_id: str) -> AgentRun | None:
        return _agent_run().model_copy(update={"status": AgentRunStatus.RUNNING})

    async def create_step(
        self,
        *,
        agent_run_id: str,
        kind: AgentRunStepKind,
        pattern: str,
        invocation_id: str | None = None,
        safe_input: dict[str, object] | None = None,
    ) -> AgentRunStep:
        self.step_sequence += 1
        now = _now()
        return AgentRunStep(
            step_id=f"step-{self.step_sequence}",
            agent_run_id=agent_run_id,
            sequence=self.step_sequence,
            kind=kind,
            status=AgentRunStepStatus.RUNNING,
            pattern=pattern,
            invocation_id=invocation_id,
            safe_input=safe_input or {},
            created_at=now,
            updated_at=now,
        )

    async def complete_step(
        self,
        *,
        step_id: str,
        safe_output: dict[str, object] | None = None,
    ) -> None:
        return None

    async def fail_step(
        self,
        *,
        step_id: str,
        error_type: str,
        safe_output: dict[str, object] | None = None,
    ) -> None:
        return None

    async def complete_run(
        self,
        agent_run_id: str,
        *,
        finish_reason: AgentRunFinishReason = AgentRunFinishReason.COMPLETED,
    ) -> AgentRun | None:
        return _agent_run().model_copy(
            update={"status": AgentRunStatus.COMPLETED, "finish_reason": finish_reason}
        )

    async def fail_run(self, agent_run_id: str, *, error_type: str) -> AgentRun | None:
        return _agent_run().model_copy(
            update={
                "status": AgentRunStatus.FAILED,
                "finish_reason": AgentRunFinishReason.ERROR,
                "error_type": error_type,
            }
        )


class _EventRepository:
    async def append(self, **kwargs: object) -> None:
        return None


class _ModelInvoker:
    pass


class _ToolExecutor:
    def declarations(self) -> list:
        return []


class _Registry:
    def __init__(self, pattern) -> None:
        self.pattern = pattern

    def require(self, name: str):
        return self.pattern


class _Pattern:
    def __init__(self) -> None:
        self.visible_texts: list[str] = []

    def next_action(self, state: PatternRuntimeState):
        self.visible_texts = [
            block.text for message in state.visible_context_messages for block in message.content
        ]
        return CompleteAction(final_content="final answer")


@pytest.mark.asyncio
async def test_context_agent_run_window_watermark_and_final_submission() -> None:
    """AgentRun 使用 context window/watermark，最终 assistant 提交保持不变。"""
    session_manager = _SessionManager()
    config = AgentRuntimeConfig(
        CONTEXT_WINDOW_MESSAGES=4,
        CONTEXT_SNIP_THRESHOLD_MESSAGES=4,
        CONTEXT_SNIP_HEAD_MESSAGES=1,
        CONTEXT_SNIP_TAIL_MESSAGES=1,
    )
    pattern = _Pattern()
    kernel = AgentRuntimeKernel(
        patterns=_Registry(pattern),
        run_manager=_RunManager(),
        session_manager=session_manager,  # type: ignore[arg-type]
        context_builder=ContextBuilder(
            session_manager=session_manager,  # type: ignore[arg-type]
            config=config,
        ),
        event_repository=_EventRepository(),  # type: ignore[arg-type]
        model_invoker=_ModelInvoker(),  # type: ignore[arg-type]
        tool_executor=_ToolExecutor(),  # type: ignore[arg-type]
        config=config,
    )

    result: AgentRunExecutionResult | None = None
    async for event in kernel.stream(_agent_run()):
        if isinstance(event, AgentRunExecutionResult):
            result = event

    assert result is not None
    assert result.agent_run.status == AgentRunStatus.COMPLETED
    assert pattern.visible_texts == ["message 7", "message 8", "message 9", "message 10"]
    assert "message 11" not in pattern.visible_texts
    assert session_manager.final_messages == ["final answer"]
