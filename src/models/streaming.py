"""统一模型流事件归约器。"""

from src.contracts.runtime import ContentDeltaPayload
from src.contracts.runtime import InvocationStartedPayload
from src.contracts.runtime import ModelResponse
from src.contracts.runtime import ModelStreamEvent
from src.contracts.runtime import ModelStreamEventType
from src.contracts.runtime import ModelToolCall
from src.contracts.runtime import ModelUsage
from src.contracts.runtime import ResponseCompletedPayload
from src.contracts.runtime import ResponseFailedPayload
from src.contracts.runtime import TextContentBlock
from src.contracts.runtime import ToolCallCompletedPayload
from src.contracts.runtime import ToolCallDeltaPayload
from src.contracts.runtime import ToolCallStartedPayload
from src.contracts.runtime import UsageUpdatedPayload
from src.exceptions import ModelResponseParseError
from src.exceptions import ModelStreamInterruptedError


class ModelStreamReducer:
    """将标准流事件归约为与 blocking 路径同形的响应。"""

    def __init__(self) -> None:
        self._invocation_id: str | None = None
        self._started: InvocationStartedPayload | None = None
        self._content: list[str] = []
        self._tool_calls: list[ModelToolCall] = []
        self._pending_tool_call_ids: set[str] = set()
        self._usage: ModelUsage | None = None
        self._completed: ResponseCompletedPayload | None = None

    def consume(self, event: ModelStreamEvent) -> None:
        """消费单条统一流事件。

        Args:
            event: protocol 转换后的统一流事件。

        Raises:
            ModelStreamInterruptedError: 流显式报告失败。
        """
        self._invocation_id = self._invocation_id or event.invocation_id
        if event.invocation_id != self._invocation_id:
            raise ModelResponseParseError(msg="流事件 invocation_id 不一致")
        if event.event_type == ModelStreamEventType.INVOCATION_STARTED:
            payload = event.payload
            if not isinstance(payload, InvocationStartedPayload):
                raise _invalid_payload_error(event)
            self._started = payload
        elif event.event_type == ModelStreamEventType.CONTENT_DELTA:
            payload = event.payload
            if not isinstance(payload, ContentDeltaPayload):
                raise _invalid_payload_error(event)
            self._content.append(payload.delta)
        elif event.event_type == ModelStreamEventType.TOOL_CALL_STARTED:
            payload = event.payload
            if not isinstance(payload, ToolCallStartedPayload):
                raise _invalid_payload_error(event)
            self._pending_tool_call_ids.add(payload.call_id)
        elif event.event_type == ModelStreamEventType.TOOL_CALL_DELTA:
            payload = event.payload
            if not isinstance(payload, ToolCallDeltaPayload):
                raise _invalid_payload_error(event)
            self._pending_tool_call_ids.add(payload.call_id)
        elif event.event_type == ModelStreamEventType.TOOL_CALL_COMPLETED:
            payload = event.payload
            if not isinstance(payload, ToolCallCompletedPayload):
                raise _invalid_payload_error(event)
            self._tool_calls.append(payload.tool_call)
            self._pending_tool_call_ids.discard(payload.tool_call.call_id)
        elif event.event_type == ModelStreamEventType.USAGE_UPDATED:
            payload = event.payload
            if not isinstance(payload, UsageUpdatedPayload):
                raise _invalid_payload_error(event)
            self._usage = payload.usage
        elif event.event_type == ModelStreamEventType.RESPONSE_COMPLETED:
            payload = event.payload
            if not isinstance(payload, ResponseCompletedPayload):
                raise _invalid_payload_error(event)
            self._completed = payload
            self._usage = payload.usage or self._usage
        elif event.event_type == ModelStreamEventType.RESPONSE_FAILED:
            payload = event.payload
            if not isinstance(payload, ResponseFailedPayload):
                raise _invalid_payload_error(event)
            raise ModelStreamInterruptedError(
                msg=payload.message,
                provider=self._started.provider if self._started else None,
                model=self._started.model if self._started else None,
                protocol=self._started.protocol.value if self._started else None,
                operation="stream",
                partial_content_received=bool(self._content),
                pending_tool_call=bool(self._pending_tool_call_ids),
                retryable=payload.retryable,
                fallback_allowed=payload.fallback_allowed,
                provider_error_code=payload.provider_error_code,
                provider_status_code=payload.provider_status_code,
            )

    def response(self) -> ModelResponse:
        """返回完成流的统一响应。

        Returns:
            与 blocking 路径同形的 ``ModelResponse``。

        Raises:
            ModelResponseParseError: 流缺少开始/完成边界或工具参数未完成。
        """
        if self._invocation_id is None or self._started is None or self._completed is None:
            raise ModelResponseParseError(msg="模型流缺少开始或完成边界")
        if self._pending_tool_call_ids:
            raise ModelResponseParseError(msg="模型流包含未完成工具参数")
        content = [TextContentBlock(text="".join(self._content))] if self._content else []
        return ModelResponse(
            invocation_id=self._invocation_id,
            provider=self._started.provider,
            model=self._started.model,
            protocol=self._started.protocol,
            content=content,
            tool_calls=self._tool_calls,
            status=self._completed.status,
            stop_reason=self._completed.stop_reason,
            provider_stop_reason=self._completed.provider_stop_reason,
            usage=self._usage,
        )


def _invalid_payload_error(event: ModelStreamEvent) -> ModelResponseParseError:
    """创建统一的流 payload 不一致错误。

    Args:
        event: 不满足声明类型的流事件。

    Returns:
        可公开的标准模型解析错误。
    """
    return ModelResponseParseError(
        operation="parse",
        data={"reason": "stream_payload_mismatch", "event_type": event.event_type.value},
    )
