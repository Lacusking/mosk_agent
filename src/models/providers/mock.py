"""确定性的无网络 Mock provider。"""

from collections.abc import AsyncIterator

from src.contracts.runtime import ContentDeltaPayload
from src.contracts.runtime import InvocationStartedPayload
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelRequest
from src.contracts.runtime import ModelResponse
from src.contracts.runtime import ModelResponseStatus
from src.contracts.runtime import ModelStopReason
from src.contracts.runtime import ModelStreamEvent
from src.contracts.runtime import ModelStreamEventType
from src.contracts.runtime import ModelToolCall
from src.contracts.runtime import ModelUsage
from src.contracts.runtime import ResponseCompletedPayload
from src.contracts.runtime import TextContentBlock
from src.contracts.runtime import ToolCallCompletedPayload
from src.contracts.runtime import ToolCallDeltaPayload
from src.contracts.runtime import ToolCallStartedPayload
from src.contracts.runtime import UsageUpdatedPayload
from src.exceptions import ModelError
from src.exceptions import ModelInvalidRequestError
from src.exceptions import ModelUnavailableError
from src.models.base import InvocationContext
from src.models.parsers.errors import map_provider_error
from src.models.profiles import ModelProfile
from src.models.selector import ModelSelector


class MockProtocolAdapter:
    """Mock profile 的显式可执行 protocol identity。"""

    protocol = ModelProtocol.MOCK

    def build_payload(self, request: ModelRequest, profile: ModelProfile) -> dict[str, object]:
        """返回不携带正文的空 wire 表示。

        Args:
            request: 标准请求。
            profile: 已选择 profile。

        Returns:
            空字典；Mock 不使用 transport。
        """
        return {}

    def parse_response(self, response: object, context: InvocationContext) -> ModelResponse:
        """拒绝不应到达的 transport 解析调用。

        Args:
            response: 未使用的 provider response。
            context: 当前调用上下文。

        Raises:
            ModelInvalidRequestError: Mock 不解析远程响应。
        """
        raise ModelInvalidRequestError(
            provider=context.provider,
            model=context.model,
            protocol=context.protocol.value,
            operation="parse",
            data={"reason": "mock_has_no_wire_response"},
        )

    async def stream_events(
        self,
        events: AsyncIterator[dict[str, object]],
        context: InvocationContext,
    ) -> AsyncIterator[ModelStreamEvent]:
        """拒绝不应到达的 transport stream。

        Args:
            events: 未使用的流。
            context: 当前调用上下文。

        Yields:
            本方法不产生事件。
        """
        if False:
            yield _event(context, 0, ModelStreamEventType.INVOCATION_STARTED, {})
        raise ModelInvalidRequestError(
            provider=context.provider,
            model=context.model,
            protocol=context.protocol.value,
            operation="stream",
            data={"reason": "mock_has_no_wire_stream"},
        )

    def map_error(
        self, error: Exception, context: InvocationContext, *, operation: str
    ) -> ModelError:
        """映射不可预期的 Mock 错误。

        Args:
            error: 原始错误。
            context: 当前调用上下文。
            operation: 失败操作。

        Returns:
            标准模型错误。
        """
        return map_provider_error(error, context, operation=operation)


class MockModelAdapter:
    """以 metadata mode 驱动可重复的文本、工具和失败场景。"""

    def __init__(self, *, selector: ModelSelector, response_text: str = "mock response") -> None:
        """初始化 Mock adapter。

        Args:
            selector: 模型 selector。
            response_text: 默认文本响应。
        """
        self._selector = selector
        self._response_text = response_text

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        """生成确定性 blocking 响应。

        Args:
            request: 标准模型请求。

        Returns:
            标准最终响应。
        """
        if request.stream:
            raise ModelInvalidRequestError(operation="invoke", data={"reason": "stream_request"})
        context = self._context(request)
        self._raise_failure_if_requested(request, context)
        tool_call = _mock_tool_call() if request.metadata.get("mode") == "tool" else None
        return _response(context, self._response_text, tool_call)

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]:
        """生成确定性 streaming 事件。

        Args:
            request: 标准模型请求。

        Yields:
            标准流事件。
        """
        if not request.stream:
            raise ModelInvalidRequestError(operation="stream", data={"reason": "blocking_request"})
        context = self._context(request)
        self._raise_failure_if_requested(request, context)
        sequence = 0
        yield _event(
            context,
            sequence,
            ModelStreamEventType.INVOCATION_STARTED,
            InvocationStartedPayload(
                provider=context.provider,
                model=context.model,
                protocol=context.protocol,
            ),
        )
        sequence += 1
        if request.metadata.get("mode") == "tool":
            tool_call = _mock_tool_call()
            yield _event(
                context,
                sequence,
                ModelStreamEventType.TOOL_CALL_STARTED,
                ToolCallStartedPayload(call_id=tool_call.call_id, name=tool_call.name),
            )
            sequence += 1
            yield _event(
                context,
                sequence,
                ModelStreamEventType.TOOL_CALL_DELTA,
                ToolCallDeltaPayload(call_id=tool_call.call_id, arguments_delta='{"query":"mock"}'),
            )
            sequence += 1
            yield _event(
                context,
                sequence,
                ModelStreamEventType.TOOL_CALL_COMPLETED,
                ToolCallCompletedPayload(tool_call=tool_call),
            )
            sequence += 1
            stop_reason = ModelStopReason.TOOL_USE
        else:
            for delta in ("mock ", "response"):
                yield _event(
                    context,
                    sequence,
                    ModelStreamEventType.CONTENT_DELTA,
                    ContentDeltaPayload(delta=delta),
                )
                sequence += 1
            stop_reason = ModelStopReason.COMPLETED
        usage = ModelUsage(input_tokens=1, output_tokens=2, total_tokens=3)
        yield _event(
            context,
            sequence,
            ModelStreamEventType.USAGE_UPDATED,
            UsageUpdatedPayload(usage=usage),
        )
        sequence += 1
        yield _event(
            context,
            sequence,
            ModelStreamEventType.RESPONSE_COMPLETED,
            ResponseCompletedPayload(
                status=ModelResponseStatus.COMPLETED,
                stop_reason=stop_reason,
                provider_stop_reason="mock",
                usage=usage,
            ),
        )

    def _context(self, request: ModelRequest) -> InvocationContext:
        selected = self._selector.select(request)
        if selected.context.protocol != ModelProtocol.MOCK:
            raise ModelInvalidRequestError(
                provider=selected.context.provider,
                model=selected.context.model,
                protocol=selected.context.protocol.value,
                operation="select",
                data={"reason": "not_mock_protocol"},
            )
        return selected.context

    @staticmethod
    def _raise_failure_if_requested(request: ModelRequest, context: InvocationContext) -> None:
        if request.metadata.get("mode") == "fail":
            raise ModelUnavailableError(
                provider=context.provider,
                model=context.model,
                protocol=context.protocol.value,
                operation="invoke" if not request.stream else "stream",
                data={"reason": "configured_mock_failure"},
            )


def _mock_tool_call() -> ModelToolCall:
    return ModelToolCall(
        call_id="mock-call-1",
        name="lookup",
        arguments={"query": "mock"},
    )


def _response(
    context: InvocationContext, text: str, tool_call: ModelToolCall | None
) -> ModelResponse:
    return ModelResponse(
        invocation_id=context.invocation_id,
        provider=context.provider,
        model=context.model,
        protocol=context.protocol,
        content=[] if tool_call else [TextContentBlock(text=text)],
        tool_calls=[tool_call] if tool_call else [],
        status=ModelResponseStatus.COMPLETED,
        stop_reason=ModelStopReason.TOOL_USE if tool_call else ModelStopReason.COMPLETED,
        provider_stop_reason="mock",
        usage=ModelUsage(input_tokens=1, output_tokens=2, total_tokens=3),
    )


def _event(
    context: InvocationContext,
    sequence: int,
    event_type: ModelStreamEventType,
    payload: object,
) -> ModelStreamEvent:
    return ModelStreamEvent.model_validate(
        {
            "invocation_id": context.invocation_id,
            "sequence": sequence,
            "event_type": event_type,
            "payload": payload,
        }
    )
