"""AgentRun runtime kernel。"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from time import monotonic
from uuid import uuid4

from src.agent_runs import AgentRunManager
from src.contracts.agent_runs import AgentRun
from src.contracts.agent_runs import AgentRunFinishReason
from src.contracts.agent_runs import AgentRunStatus
from src.contracts.agent_runs import AgentRunStep
from src.contracts.agent_runs import AgentRunStepKind
from src.contracts.agent_runs import AgentRunStepStatus
from src.contracts.agent_runs import AgentRunStreamEvent
from src.contracts.patterns import CompleteAction
from src.contracts.patterns import FailAction
from src.contracts.patterns import InvokeModelAction
from src.contracts.patterns import InvokeToolAction
from src.contracts.patterns import OutputVisibility
from src.contracts.patterns import PatternObservation
from src.contracts.patterns import PatternRuntimeState
from src.contracts.patterns import TransitionPatternAction
from src.contracts.runtime import ContentDeltaPayload
from src.contracts.runtime import ModelInvocationCompletedPayload
from src.contracts.runtime import ModelInvocationFailedPayload
from src.contracts.runtime import ModelInvocationStartedPayload
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelRequest
from src.contracts.runtime import ModelResponse
from src.contracts.runtime import ModelStreamEventType
from src.contracts.runtime import ModelToolCallsProducedPayload
from src.contracts.runtime import ModelUsage
from src.contracts.runtime import ProducedToolCallFact
from src.contracts.runtime import RuntimeEventType
from src.contracts.runtime import StepCompletedPayload
from src.contracts.runtime import StepStartedPayload
from src.contracts.runtime import TextContentBlock
from src.contracts.runtime import ToolActionExecutedPayload
from src.core.config import AgentRuntimeConfig
from src.exceptions import ModelError
from src.models.streaming import ModelStreamReducer
from src.patterns import PatternRegistry
from src.runtime.cancellation import CancellationToken
from src.runtime.cancellation import CancellationTrigger
from src.runtime.cancellation import CancelledError
from src.runtime.error_policy import decide_model_error
from src.runtime.finish_reason import finish_reason_from_model_response
from src.runtime.model_invoker import RuntimeModelInvoker
from src.runtime.stream import output_text_delta_event
from src.runtime.stream import run_started_event
from src.runtime.stream import terminal_event
from src.sessions import SessionManager
from src.storage.database.repositories import RuntimeEventRepository
from src.tools import ToolActionExecutor


@dataclass(frozen=True)
class AgentRunExecutionResult:
    """AgentRun 执行结果。"""

    agent_run: AgentRun
    final_content: str | None = None


class AgentRuntimeKernel:
    """执行 pattern action loop 的 runtime kernel。"""

    def __init__(
        self,
        *,
        patterns: PatternRegistry,
        run_manager: AgentRunManager,
        session_manager: SessionManager,
        event_repository: RuntimeEventRepository,
        model_invoker: RuntimeModelInvoker,
        tool_executor: ToolActionExecutor,
        config: AgentRuntimeConfig,
        model: str = "mock-model",
        provider: str = "mock",
        protocol: ModelProtocol = ModelProtocol.MOCK,
    ) -> None:
        """初始化 runtime kernel。

        Args:
            patterns: pattern 注册表。
            run_manager: AgentRun manager。
            session_manager: Session manager。
            event_repository: 事件仓库。
            model_invoker: 模型调用封装。
            tool_executor: 工具动作 executor。
            config: runtime 配置。
            model: 默认模型名。
            provider: 默认 provider。
            protocol: 默认协议。
        """
        self._patterns = patterns
        self._run_manager = run_manager
        self._session_manager = session_manager
        self._events = event_repository
        self._model_invoker = model_invoker
        self._tool_executor = tool_executor
        self._config = config
        self._model = model
        self._provider = provider
        self._protocol = protocol

    async def execute(
        self,
        agent_run: AgentRun,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> AgentRunExecutionResult:
        """同步执行 run 到终态。

        Args:
            agent_run: 已创建的 AgentRun。
            cancellation_token: 可选取消令牌。

        Returns:
            执行结果。
        """
        result: AgentRunExecutionResult | None = None
        async for _event in self.stream(
            agent_run,
            cancellation_token=cancellation_token,
            emit_public_deltas=False,
        ):
            result = _event if isinstance(_event, AgentRunExecutionResult) else result
        if result is None:
            latest = await self._run_manager.mark_running(agent_run.agent_run_id)
            return AgentRunExecutionResult(agent_run=latest or agent_run)
        return result

    async def stream(
        self,
        agent_run: AgentRun,
        *,
        cancellation_token: CancellationToken | None = None,
        emit_public_deltas: bool = True,
    ) -> AsyncIterator[AgentRunStreamEvent | AgentRunExecutionResult]:
        """执行 run 并输出运行级 SSE 事件。

        Args:
            agent_run: 已创建的 AgentRun。
            cancellation_token: 可选取消令牌。
            emit_public_deltas: 是否产出公开文本 delta。

        Yields:
            SSE 事件；最后额外产出 AgentRunExecutionResult 供同步路径消费。
        """
        started_at = monotonic()
        current_run = await self._run_manager.mark_running(agent_run.agent_run_id) or agent_run
        await self._append_run_started(current_run)
        yield run_started_event(
            agent_run_id=current_run.agent_run_id,
            session_id=current_run.session_id,
            mode=current_run.mode,
            pattern=current_run.active_pattern,
            trace_id=current_run.trace_id,
        )

        observations: list[PatternObservation] = []
        final_content: str | None = None
        last_finish_reason = AgentRunFinishReason.COMPLETED
        step_count = 0

        try:
            context = await self._session_manager.model_context(
                session_id=current_run.session_id,
                through_sequence=current_run.context_message_sequence,
            )
            while step_count < current_run.max_steps:
                if cancellation_token:
                    cancellation_token.raise_if_cancelled()
                pattern = self._patterns.require(current_run.active_pattern)
                state = PatternRuntimeState(
                    agent_run=current_run,
                    visible_context_messages=context,
                    observations=observations,
                    step_count=step_count,
                    available_tools=self._tool_executor.declarations(),
                )
                action = pattern.next_action(state)

                if isinstance(action, InvokeModelAction):
                    step_count += 1
                    observation, finish_reason, deltas = await self._execute_model_action(
                        current_run,
                        action,
                        pattern=current_run.active_pattern,
                        stream=emit_public_deltas,
                        react_tool_probe=self._is_react_tool_probe(current_run.active_pattern, observations, action),
                    )
                    last_finish_reason = finish_reason
                    observations.append(observation)
                    for event in deltas:
                        yield event
                    continue

                if isinstance(action, InvokeToolAction):
                    step_count += 1
                    observation = await self._execute_tool_action(
                        current_run,
                        action,
                        pattern=current_run.active_pattern,
                    )
                    observations.append(observation)
                    continue

                if isinstance(action, TransitionPatternAction):
                    step_count += 1
                    step = await self._start_step(
                        current_run,
                        kind=AgentRunStepKind.TRANSITION,
                        pattern=current_run.active_pattern,
                        safe_input={"target_pattern": action.target_pattern, "reason": action.reason},
                    )
                    self._patterns.require(action.target_pattern)
                    await self._complete_step(current_run, step, status=AgentRunStepStatus.SUCCEEDED)
                    await self._append_pattern_transitioned(current_run, step, action)
                    updated = await self._run_manager.set_active_pattern(
                        agent_run_id=current_run.agent_run_id,
                        active_pattern=action.target_pattern,
                    )
                    current_run = updated or current_run.model_copy(
                        update={"active_pattern": action.target_pattern}
                    )
                    observations = []
                    continue

                if isinstance(action, CompleteAction):
                    step_count += 1
                    step = await self._start_step(
                        current_run,
                        kind=AgentRunStepKind.COMPLETE,
                        pattern=current_run.active_pattern,
                    )
                    await self._complete_step(
                        current_run,
                        step,
                        status=AgentRunStepStatus.SUCCEEDED,
                        safe_output={"has_final_content": True},
                    )
                    final_content = action.final_content
                    await self._session_manager.append_final_assistant_text(
                        session_id=current_run.session_id,
                        agent_run_id=current_run.agent_run_id,
                        text=final_content,
                    )
                    completed = await self._run_manager.complete_run(
                        current_run.agent_run_id,
                        finish_reason=last_finish_reason,
                    )
                    current_run = completed or current_run
                    await self._append_run_completed(current_run, step_count, started_at)
                    yield terminal_event(
                        agent_run_id=current_run.agent_run_id,
                        status="completed",
                        finish_reason=current_run.finish_reason or last_finish_reason,
                    )
                    yield AgentRunExecutionResult(agent_run=current_run, final_content=final_content)
                    return

                if isinstance(action, FailAction):
                    step_count += 1
                    step = await self._start_step(
                        current_run,
                        kind=AgentRunStepKind.FAIL,
                        pattern=current_run.active_pattern,
                        safe_input={"reason": action.reason},
                    )
                    await self._complete_step(
                        current_run,
                        step,
                        status=AgentRunStepStatus.FAILED,
                        error_type=action.error_type,
                    )
                    current_run = await self._fail_run(
                        current_run,
                        error_type=action.error_type,
                        step_count=step_count,
                        started_at=started_at,
                    )
                    yield terminal_event(
                        agent_run_id=current_run.agent_run_id,
                        status="failed",
                        finish_reason=current_run.finish_reason,
                        error_type=current_run.error_type,
                    )
                    yield AgentRunExecutionResult(agent_run=current_run)
                    return

                current_run = await self._fail_run(
                    current_run,
                    error_type="UnsupportedPatternAction",
                    step_count=step_count,
                    started_at=started_at,
                )
                yield terminal_event(
                    agent_run_id=current_run.agent_run_id,
                    status="failed",
                    finish_reason=current_run.finish_reason,
                    error_type=current_run.error_type,
                )
                yield AgentRunExecutionResult(agent_run=current_run)
                return

            current_run = await self._fail_run(
                current_run,
                error_type="MaxStepsExceeded",
                step_count=step_count,
                started_at=started_at,
            )
            yield terminal_event(
                agent_run_id=current_run.agent_run_id,
                status="failed",
                finish_reason=AgentRunFinishReason.MAX_STEPS,
                error_type=current_run.error_type,
            )
            yield AgentRunExecutionResult(agent_run=current_run)
        except CancelledError as exc:
            current_run = await self._cancel_run(
                current_run,
                trigger=exc.trigger or CancellationTrigger.EXPLICIT,
                step_count=step_count,
                started_at=started_at,
            )
            yield terminal_event(
                agent_run_id=current_run.agent_run_id,
                status="cancelled",
                finish_reason=AgentRunFinishReason.CANCELLED,
            )
            yield AgentRunExecutionResult(agent_run=current_run)
        except ModelError as exc:
            current_run = await self._fail_run(
                current_run,
                error_type=exc.__class__.__name__,
                step_count=step_count,
                started_at=started_at,
            )
            yield terminal_event(
                agent_run_id=current_run.agent_run_id,
                status="failed",
                finish_reason=current_run.finish_reason,
                error_type=current_run.error_type,
            )
            yield AgentRunExecutionResult(agent_run=current_run)

    async def _execute_model_action(
        self,
        agent_run: AgentRun,
        action: InvokeModelAction,
        *,
        pattern: str,
        stream: bool,
        react_tool_probe: bool,
    ) -> tuple[PatternObservation, AgentRunFinishReason, list[AgentRunStreamEvent]]:
        invocation_id = str(uuid4())
        step = await self._start_step(
            agent_run,
            kind=AgentRunStepKind.MODEL,
            pattern=pattern,
            invocation_id=invocation_id,
            safe_input={
                "visibility": action.output_visibility.value,
                "tool_count": len(action.tools),
            },
        )
        request = ModelRequest(
            invocation_id=invocation_id,
            provider=self._provider,
            model=self._model,
            protocol=self._protocol,
            messages=action.messages,
            tools=action.tools,
            options=action.options,
            stream=stream,
            timeout_seconds=agent_run.timeout_seconds,
            metadata={
                "agent_run_id": agent_run.agent_run_id,
                "step_id": step.step_id,
                "trace_id": agent_run.trace_id,
                "mode": "tool" if react_tool_probe else agent_run.mode.value,
            },
        )
        await self._append_model_started(agent_run, step, request)
        try:
            response, deltas = await self._call_model(request, action, agent_run, step, stream=stream)
        except ModelError as exc:
            await self._run_manager.fail_step(step_id=step.step_id, error_type=exc.__class__.__name__)
            raise

        await self._append_model_completed(agent_run, step, response)
        if response.tool_calls:
            await self._append_tool_calls_produced(agent_run, step, response)
        await self._complete_step(
            agent_run,
            step,
            status=AgentRunStepStatus.SUCCEEDED,
            safe_output={
                "status": response.status.value,
                "stop_reason": response.stop_reason.value,
                "tool_call_count": len(response.tool_calls),
                "text_length": len(_response_text(response)),
            },
        )
        return (
            PatternObservation(
                kind="model_response",
                data={
                    "text": _response_text(response),
                    "status": response.status.value,
                    "stop_reason": response.stop_reason.value,
                    "tool_calls": [call.model_dump(mode="json") for call in response.tool_calls],
                    "visibility": action.output_visibility.value,
                },
            ),
            finish_reason_from_model_response(response),
            deltas,
        )

    async def _call_model(
        self,
        request: ModelRequest,
        action: InvokeModelAction,
        agent_run: AgentRun,
        step: AgentRunStep,
        *,
        stream: bool,
    ) -> tuple[ModelResponse, list[AgentRunStreamEvent]]:
        retry_count = 0
        visible_output_sent = False
        while True:
            try:
                if not stream:
                    return await self._model_invoker.invoke(request), []
                reducer = ModelStreamReducer()
                deltas: list[AgentRunStreamEvent] = []
                delta_sequence = 1
                async for event in self._model_invoker.stream(request):
                    reducer.consume(event)
                    if (
                        action.output_visibility == OutputVisibility.PUBLIC_OUTPUT
                        and event.event_type == ModelStreamEventType.CONTENT_DELTA
                        and isinstance(event.payload, ContentDeltaPayload)
                    ):
                        visible_output_sent = True
                        deltas.append(
                            output_text_delta_event(
                                agent_run_id=agent_run.agent_run_id,
                                sequence=delta_sequence,
                                delta=event.payload.delta,
                            )
                        )
                        delta_sequence += 1
                return reducer.response(), deltas
            except ModelError as exc:
                decision = decide_model_error(
                    exc,
                    retry_count=retry_count,
                    retry_limit=agent_run.retry_limit,
                    visible_output_sent=visible_output_sent,
                )
                await self._append_model_failed(agent_run, step, request.invocation_id, exc)
                if not decision.retry:
                    raise
                retry_count += 1

    async def _execute_tool_action(
        self,
        agent_run: AgentRun,
        action: InvokeToolAction,
        *,
        pattern: str,
    ) -> PatternObservation:
        step = await self._start_step(
            agent_run,
            kind=AgentRunStepKind.TOOL,
            pattern=pattern,
            safe_input={"tool_name": action.tool_call.name, "call_id": action.tool_call.call_id},
        )
        started_at = monotonic()
        result = await self._tool_executor.execute(
            action.to_tool_action_request(
                agent_run_id=agent_run.agent_run_id,
                step_id=step.step_id,
            )
        )
        await self._events.append(
            agent_run_id=agent_run.agent_run_id,
            step_id=step.step_id,
            session_id=agent_run.session_id,
            event_type=RuntimeEventType.TOOL_ACTION_EXECUTED,
            trace_id=agent_run.trace_id,
            span_id=str(uuid4()),
            payload=ToolActionExecutedPayload(
                agent_run_id=agent_run.agent_run_id,
                step_id=step.step_id,
                tool_name=result.name,
                call_id=result.call_id,
                status=result.status.value,
                latency_ms=_latency_ms(started_at),
            ),
        )
        await self._complete_step(
            agent_run,
            step,
            status=AgentRunStepStatus.FAILED if result.is_error else AgentRunStepStatus.SUCCEEDED,
            safe_output={"status": result.status.value, "is_error": result.is_error},
            error_type=result.error_type,
        )
        return PatternObservation(
            kind="tool_result",
            data={
                "call_id": result.call_id,
                "name": result.name,
                "status": result.status.value,
                "observation": result.observation,
                "is_error": result.is_error,
                "error_type": result.error_type,
            },
        )

    async def _start_step(
        self,
        agent_run: AgentRun,
        *,
        kind: AgentRunStepKind,
        pattern: str,
        invocation_id: str | None = None,
        safe_input: dict[str, object] | None = None,
    ) -> AgentRunStep:
        step = await self._run_manager.create_step(
            agent_run_id=agent_run.agent_run_id,
            kind=kind,
            pattern=pattern,
            invocation_id=invocation_id,
            safe_input=safe_input,
        )
        await self._events.append(
            agent_run_id=agent_run.agent_run_id,
            step_id=step.step_id,
            session_id=agent_run.session_id,
            event_type=RuntimeEventType.STEP_STARTED,
            trace_id=agent_run.trace_id,
            span_id=str(uuid4()),
            payload=StepStartedPayload(
                agent_run_id=agent_run.agent_run_id,
                step_id=step.step_id,
                sequence=step.sequence,
                kind=kind.value,
                pattern=pattern,
            ),
        )
        return step

    async def _complete_step(
        self,
        agent_run: AgentRun,
        step: AgentRunStep,
        *,
        status: AgentRunStepStatus,
        safe_output: dict[str, object] | None = None,
        error_type: str | None = None,
    ) -> None:
        started_at = monotonic()
        if status == AgentRunStepStatus.SUCCEEDED:
            await self._run_manager.complete_step(step_id=step.step_id, safe_output=safe_output)
        else:
            await self._run_manager.fail_step(
                step_id=step.step_id,
                error_type=error_type or "StepFailed",
                safe_output=safe_output,
            )
        await self._events.append(
            agent_run_id=agent_run.agent_run_id,
            step_id=step.step_id,
            session_id=agent_run.session_id,
            event_type=RuntimeEventType.STEP_COMPLETED,
            trace_id=agent_run.trace_id,
            span_id=str(uuid4()),
            payload=StepCompletedPayload(
                agent_run_id=agent_run.agent_run_id,
                step_id=step.step_id,
                sequence=step.sequence,
                kind=step.kind.value,
                status=status.value,
                latency_ms=_latency_ms(started_at),
            ),
        )

    async def _append_run_started(self, agent_run: AgentRun) -> None:
        from src.contracts.runtime import AgentRunStartedPayload

        await self._events.append(
            agent_run_id=agent_run.agent_run_id,
            session_id=agent_run.session_id,
            event_type=RuntimeEventType.AGENT_RUN_STARTED,
            trace_id=agent_run.trace_id,
            span_id=str(uuid4()),
            payload=AgentRunStartedPayload(
                agent_run_id=agent_run.agent_run_id,
                session_id=agent_run.session_id,
                mode=agent_run.mode.value,
                pattern=agent_run.active_pattern,
                context_message_sequence=agent_run.context_message_sequence,
                trace_id=agent_run.trace_id,
            ),
        )

    async def _append_run_completed(
        self,
        agent_run: AgentRun,
        step_count: int,
        started_at: float,
    ) -> None:
        from src.contracts.runtime import AgentRunCompletedPayload

        await self._events.append(
            agent_run_id=agent_run.agent_run_id,
            session_id=agent_run.session_id,
            event_type=RuntimeEventType.AGENT_RUN_COMPLETED,
            trace_id=agent_run.trace_id,
            span_id=str(uuid4()),
            payload=AgentRunCompletedPayload(
                agent_run_id=agent_run.agent_run_id,
                status=AgentRunStatus.COMPLETED.value,
                finish_reason=(agent_run.finish_reason or AgentRunFinishReason.COMPLETED).value,
                step_count=step_count,
                latency_ms=_latency_ms(started_at),
            ),
        )

    async def _fail_run(
        self,
        agent_run: AgentRun,
        *,
        error_type: str,
        step_count: int,
        started_at: float,
    ) -> AgentRun:
        from src.contracts.runtime import AgentRunFailedPayload

        failed = await self._run_manager.fail_run(agent_run.agent_run_id, error_type=error_type)
        result = failed or agent_run.model_copy(
            update={
                "status": AgentRunStatus.FAILED,
                "finish_reason": AgentRunFinishReason.ERROR,
                "error_type": error_type,
            }
        )
        await self._events.append(
            agent_run_id=result.agent_run_id,
            session_id=result.session_id,
            event_type=RuntimeEventType.AGENT_RUN_FAILED,
            trace_id=result.trace_id,
            span_id=str(uuid4()),
            payload=AgentRunFailedPayload(
                agent_run_id=result.agent_run_id,
                status=AgentRunStatus.FAILED.value,
                error_type=error_type,
                error_classification="runtime",
                last_step_sequence=step_count or None,
                latency_ms=_latency_ms(started_at),
            ),
        )
        return result

    async def _cancel_run(
        self,
        agent_run: AgentRun,
        *,
        trigger: CancellationTrigger,
        step_count: int,
        started_at: float,
    ) -> AgentRun:
        from src.contracts.runtime import AgentRunCancelledPayload

        cancelled = await self._run_manager.cancel_run(agent_run.agent_run_id)
        result = cancelled or agent_run.model_copy(
            update={
                "status": AgentRunStatus.CANCELLED,
                "finish_reason": AgentRunFinishReason.CANCELLED,
            }
        )
        await self._events.append(
            agent_run_id=result.agent_run_id,
            session_id=result.session_id,
            event_type=RuntimeEventType.AGENT_RUN_CANCELLED,
            trace_id=result.trace_id,
            span_id=str(uuid4()),
            payload=AgentRunCancelledPayload(
                agent_run_id=result.agent_run_id,
                status=AgentRunStatus.CANCELLED.value,
                trigger=trigger.value,
                last_step_sequence=step_count or None,
                latency_ms=_latency_ms(started_at),
            ),
        )
        return result

    async def _append_pattern_transitioned(
        self,
        agent_run: AgentRun,
        step: AgentRunStep,
        action: TransitionPatternAction,
    ) -> None:
        from src.contracts.runtime import PatternTransitionedPayload

        await self._events.append(
            agent_run_id=agent_run.agent_run_id,
            step_id=step.step_id,
            session_id=agent_run.session_id,
            event_type=RuntimeEventType.PATTERN_TRANSITIONED,
            trace_id=agent_run.trace_id,
            span_id=str(uuid4()),
            payload=PatternTransitionedPayload(
                agent_run_id=agent_run.agent_run_id,
                from_pattern=agent_run.active_pattern,
                to_pattern=action.target_pattern,
                step_sequence=step.sequence,
                reason=action.reason,
            ),
        )

    async def _append_model_started(
        self,
        agent_run: AgentRun,
        step: AgentRunStep,
        request: ModelRequest,
    ) -> None:
        await self._events.append(
            agent_run_id=agent_run.agent_run_id,
            step_id=step.step_id,
            session_id=agent_run.session_id,
            event_type=RuntimeEventType.MODEL_INVOCATION_STARTED,
            trace_id=agent_run.trace_id,
            span_id=str(uuid4()),
            payload=ModelInvocationStartedPayload(
                invocation_id=request.invocation_id,
                provider=request.provider or self._provider,
                model=request.model,
                protocol=request.protocol or self._protocol,
                profile="runtime_default",
                streaming=request.stream,
            ),
        )

    async def _append_model_completed(
        self,
        agent_run: AgentRun,
        step: AgentRunStep,
        response: ModelResponse,
    ) -> None:
        await self._events.append(
            agent_run_id=agent_run.agent_run_id,
            step_id=step.step_id,
            session_id=agent_run.session_id,
            event_type=RuntimeEventType.MODEL_INVOCATION_COMPLETED,
            trace_id=agent_run.trace_id,
            span_id=str(uuid4()),
            payload=ModelInvocationCompletedPayload(
                invocation_id=response.invocation_id,
                provider=response.provider,
                model=response.model,
                protocol=response.protocol,
                status=response.status,
                stop_reason=response.stop_reason,
                provider_stop_reason=response.provider_stop_reason,
                usage=response.usage or ModelUsage(),
                latency_ms=0,
                tool_call_count=len(response.tool_calls),
            ),
        )

    async def _append_model_failed(
        self,
        agent_run: AgentRun,
        step: AgentRunStep,
        invocation_id: str,
        error: ModelError,
    ) -> None:
        await self._events.append(
            agent_run_id=agent_run.agent_run_id,
            step_id=step.step_id,
            session_id=agent_run.session_id,
            event_type=RuntimeEventType.MODEL_INVOCATION_FAILED,
            trace_id=agent_run.trace_id,
            span_id=str(uuid4()),
            payload=ModelInvocationFailedPayload(
                invocation_id=invocation_id,
                provider=error.provider,
                model=error.model,
                protocol=ModelProtocol(error.protocol) if error.protocol else None,
                error_type=error.__class__.__name__,
                retryable=error.retryable,
                fallback_allowed=error.fallback_allowed,
                provider_error_code=error.provider_error_code,
                provider_status_code=error.provider_status_code,
                latency_ms=0,
            ),
        )

    async def _append_tool_calls_produced(
        self,
        agent_run: AgentRun,
        step: AgentRunStep,
        response: ModelResponse,
    ) -> None:
        await self._events.append(
            agent_run_id=agent_run.agent_run_id,
            step_id=step.step_id,
            session_id=agent_run.session_id,
            event_type=RuntimeEventType.MODEL_TOOL_CALLS_PRODUCED,
            trace_id=agent_run.trace_id,
            span_id=str(uuid4()),
            payload=ModelToolCallsProducedPayload(
                invocation_id=response.invocation_id,
                calls=[
                    ProducedToolCallFact(
                        call_id=call.call_id,
                        name=call.name,
                        arguments_validated=True,
                    )
                    for call in response.tool_calls
                ],
            ),
        )

    @staticmethod
    def _is_react_tool_probe(
        pattern: str,
        observations: list[PatternObservation],
        action: InvokeModelAction,
    ) -> bool:
        return (
            pattern == "react"
            and action.output_visibility == OutputVisibility.INTERNAL
            and not any(observation.kind == "tool_result" for observation in observations)
        )


def _response_text(response: ModelResponse) -> str:
    parts = [block.text for block in response.content if isinstance(block, TextContentBlock)]
    return "".join(parts)


def _latency_ms(started_at: float) -> float:
    return max(0.0, (monotonic() - started_at) * 1000)


__all__ = ["AgentRunExecutionResult", "AgentRuntimeKernel"]
