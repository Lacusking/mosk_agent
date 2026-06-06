"""Runtime kernel 上下文接入测试。"""

from collections.abc import AsyncIterator
from datetime import UTC
from datetime import datetime

import pytest

from src.context import ContextBundle
from src.context import ContextConversionError
from src.context import ContextItem
from src.context import ContextItemType
from src.context import ContextSource
from src.contracts.agent_runs import AgentMode
from src.contracts.agent_runs import AgentRun
from src.contracts.agent_runs import AgentRunFinishReason
from src.contracts.agent_runs import AgentRunStatus
from src.contracts.agent_runs import AgentRunStep
from src.contracts.agent_runs import AgentRunStepKind
from src.contracts.agent_runs import AgentRunStepStatus
from src.contracts.patterns import CompleteAction
from src.contracts.patterns import InvokeModelAction
from src.contracts.patterns import InvokeToolAction
from src.contracts.patterns import OutputVisibility
from src.contracts.patterns import PatternRuntimeState
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelResponse
from src.contracts.runtime import ModelResponseStatus
from src.contracts.runtime import ModelRole
from src.contracts.runtime import ModelStopReason
from src.contracts.runtime import ModelStreamEvent
from src.contracts.runtime import ModelToolCall
from src.contracts.runtime import TextContentBlock
from src.contracts.tools import ToolActionRequest
from src.contracts.tools import ToolActionResult
from src.contracts.tools import ToolActionStatus
from src.core.config import AgentRuntimeConfig
from src.exceptions import ModelContextLengthError
from src.runtime import AgentRunExecutionResult
from src.runtime import AgentRuntimeKernel


def _now() -> datetime:
    return datetime.now(UTC)


def _agent_run() -> AgentRun:
    now = _now()
    return AgentRun(
        agent_run_id="run-1",
        session_id="session-1",
        input_message_id="message-1",
        status=AgentRunStatus.CREATED,
        mode=AgentMode.CHAT,
        active_pattern="test",
        context_message_sequence=1,
        trace_id="trace-1",
        max_steps=6,
        timeout_seconds=120,
        retry_limit=1,
        created_at=now,
        updated_at=now,
    )


def _message(text: str) -> ModelMessage:
    return ModelMessage(role=ModelRole.USER, content=[TextContentBlock(text=text)])


def _bundle(message: ModelMessage | None = None) -> ContextBundle:
    content = message or _message("from context")
    return ContextBundle(
        agent_run_id="run-1",
        session_id="session-1",
        session_messages=[
            ContextItem(
                source=ContextSource.SESSION,
                type=ContextItemType.MESSAGE,
                content=content,
                metadata={"sequence": 1},
            )
        ],
    )


def _bundle_many(count: int) -> ContextBundle:
    return ContextBundle(
        agent_run_id="run-1",
        session_id="session-1",
        session_messages=[
            ContextItem(
                source=ContextSource.SESSION,
                type=ContextItemType.MESSAGE,
                content=_message(f"context {index}"),
                metadata={"sequence": index},
            )
            for index in range(1, count + 1)
        ],
    )


class _ContextBuilder:
    def __init__(self, bundle: ContextBundle | None = None, error: Exception | None = None) -> None:
        self.bundle = bundle or _bundle()
        self.error = error
        self.calls: list[str] = []
        self.observation_counts: list[int] = []

    async def build(self, agent_run: AgentRun, **kwargs: object) -> ContextBundle:
        self.calls.append(agent_run.agent_run_id)
        observations = kwargs.get("observations")
        self.observation_counts.append(len(observations) if isinstance(observations, list) else 0)
        if self.error:
            raise self.error
        return self.bundle


class _RunManager:
    def __init__(self) -> None:
        self.step_sequence = 0
        self.failed_error_type: str | None = None

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
    ) -> AgentRunStep | None:
        return None

    async def fail_step(
        self,
        *,
        step_id: str,
        error_type: str,
        safe_output: dict[str, object] | None = None,
    ) -> AgentRunStep | None:
        return None

    async def complete_run(
        self,
        agent_run_id: str,
        *,
        finish_reason: AgentRunFinishReason = AgentRunFinishReason.COMPLETED,
    ) -> AgentRun | None:
        return _agent_run().model_copy(
            update={
                "status": AgentRunStatus.COMPLETED,
                "finish_reason": finish_reason,
            }
        )

    async def fail_run(self, agent_run_id: str, *, error_type: str) -> AgentRun | None:
        self.failed_error_type = error_type
        return _agent_run().model_copy(
            update={
                "status": AgentRunStatus.FAILED,
                "finish_reason": AgentRunFinishReason.ERROR,
                "error_type": error_type,
            }
        )


class _SessionManager:
    def __init__(self) -> None:
        self.final_messages: list[str] = []

    async def append_final_assistant_text(
        self,
        *,
        session_id: str,
        agent_run_id: str,
        text: str,
    ) -> None:
        self.final_messages.append(text)

    async def model_context(self, **_: object) -> list[ModelMessage]:
        raise AssertionError("runtime must not call SessionManager.model_context")


class _EventRepository:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    async def append(self, **kwargs: object) -> None:
        self.events.append(kwargs)


class _ModelInvoker:
    async def invoke(self, request) -> object:
        raise AssertionError("model should not be invoked in this test")

    def stream(self, request) -> AsyncIterator[ModelStreamEvent]:
        raise AssertionError("model stream should not be invoked in this test")


class _ContextReductionModelInvoker:
    def __init__(self) -> None:
        self.requests: list[object] = []

    async def invoke(self, request) -> ModelResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            raise ModelContextLengthError(
                provider="mock",
                model="mock-model",
                protocol=ModelProtocol.MOCK.value,
            )
        return ModelResponse(
            invocation_id=request.invocation_id,
            provider="mock",
            model="mock-model",
            protocol=ModelProtocol.MOCK,
            content=[TextContentBlock(text="ok")],
            status=ModelResponseStatus.COMPLETED,
            stop_reason=ModelStopReason.COMPLETED,
        )

    def stream(self, request) -> AsyncIterator[ModelStreamEvent]:
        raise AssertionError("test uses blocking invoke")


class _ToolExecutor:
    def __init__(self) -> None:
        self.requests: list[ToolActionRequest] = []

    def declarations(self) -> list:
        return []

    async def execute(self, request: ToolActionRequest) -> ToolActionResult:
        self.requests.append(request)
        return ToolActionResult(
            call_id=request.call_id,
            name=request.name,
            status=ToolActionStatus.SUCCESS,
            observation={"value": "ok"},
        )


class _Registry:
    def __init__(self, pattern) -> None:
        self.pattern = pattern

    def require(self, name: str):
        return self.pattern


class _CompletePattern:
    def __init__(self) -> None:
        self.visible_messages: list[ModelMessage] = []

    def next_action(self, state: PatternRuntimeState):
        self.visible_messages = state.visible_context_messages
        return CompleteAction(final_content="done")


class _ObservationPattern:
    def __init__(self) -> None:
        self.observations_seen: list[list[str]] = []

    def next_action(self, state: PatternRuntimeState):
        self.observations_seen.append([observation.kind for observation in state.observations])
        if not state.observations:
            return InvokeToolAction(
                tool_call=ModelToolCall(call_id="call-1", name="mock.echo", arguments={})
            )
        assert state.observations[-1].kind == "tool_result"
        return CompleteAction(final_content="done after tool")


class _ModelThenCompletePattern:
    def next_action(self, state: PatternRuntimeState):
        if not state.observations:
            return InvokeModelAction(
                messages=state.visible_context_messages,
                output_visibility=OutputVisibility.INTERNAL,
            )
        return CompleteAction(final_content="done after model")


def _kernel(
    *,
    pattern,
    context_builder,
    session_manager=None,
    tool_executor=None,
    model_invoker=None,
    config=None,
):
    return AgentRuntimeKernel(
        patterns=_Registry(pattern),
        run_manager=_RunManager(),
        session_manager=session_manager or _SessionManager(),
        context_builder=context_builder,
        event_repository=_EventRepository(),
        model_invoker=model_invoker or _ModelInvoker(),
        tool_executor=tool_executor or _ToolExecutor(),
        config=config or AgentRuntimeConfig(),
    )


@pytest.mark.asyncio
async def test_kernel_context_uses_context_builder_for_visible_messages() -> None:
    """kernel 使用 ContextBuilder 输出创建 PatternRuntimeState。"""
    pattern = _CompletePattern()
    context_builder = _ContextBuilder(_bundle(_message("context message")))
    session_manager = _SessionManager()

    result = await _consume_result(
        _kernel(
            pattern=pattern,
            context_builder=context_builder,
            session_manager=session_manager,
        )
    )

    assert context_builder.calls == ["run-1"]
    assert pattern.visible_messages == [_message("context message")]
    assert session_manager.final_messages == ["done"]
    assert result.agent_run.status == AgentRunStatus.COMPLETED


@pytest.mark.asyncio
async def test_kernel_context_failure_marks_run_failed_without_model_call() -> None:
    """context 构建失败时 AgentRun 失败且不调用模型。"""
    result = await _consume_result(
        _kernel(
            pattern=_CompletePattern(),
            context_builder=_ContextBuilder(error=ContextConversionError(msg="bad context")),
        )
    )

    assert result.agent_run.status == AgentRunStatus.FAILED
    assert result.agent_run.error_type == "ContextConversionError"


@pytest.mark.asyncio
async def test_kernel_observation_keeps_tool_result_in_pattern_state() -> None:
    """工具 observation 留在 PatternRuntimeState.observations 中。"""
    pattern = _ObservationPattern()
    tool_executor = _ToolExecutor()
    context_builder = _ContextBuilder()

    result = await _consume_result(
        _kernel(
            pattern=pattern,
            context_builder=context_builder,
            tool_executor=tool_executor,
        )
    )

    assert pattern.observations_seen == [[], ["tool_result"]]
    assert context_builder.observation_counts == [0, 1]
    assert tool_executor.requests[0].name == "mock.echo"
    assert result.final_content == "done after tool"


@pytest.mark.asyncio
async def test_kernel_context_length_error_retries_with_reduced_messages() -> None:
    """模型上下文超限时 kernel 缩减消息后重试一次。"""
    invoker = _ContextReductionModelInvoker()
    kernel = _kernel(
        pattern=_ModelThenCompletePattern(),
        context_builder=_ContextBuilder(_bundle_many(6)),
        model_invoker=invoker,
        config=AgentRuntimeConfig(
            CONTEXT_WINDOW_MESSAGES=6,
            CONTEXT_SNIP_THRESHOLD_MESSAGES=3,
            CONTEXT_SNIP_HEAD_MESSAGES=1,
            CONTEXT_SNIP_TAIL_MESSAGES=2,
        ),
    )

    result = await kernel.execute(_agent_run())

    assert result.final_content == "done after model"
    assert len(invoker.requests) == 2
    assert len(invoker.requests[0].messages) == 6
    assert len(invoker.requests[1].messages) == 1
    assert invoker.requests[1].metadata["context_reduction_retry"] is True


async def _consume_result(kernel: AgentRuntimeKernel) -> AgentRunExecutionResult:
    result: AgentRunExecutionResult | None = None
    async for event in kernel.stream(_agent_run()):
        if isinstance(event, AgentRunExecutionResult):
            result = event
    if result is None:
        raise AssertionError("kernel did not yield execution result")
    return result
