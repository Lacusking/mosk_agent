"""基于 HTTP transport 的 OpenAI provider 执行器。"""

from collections.abc import AsyncIterator
from collections.abc import Callable

from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelRequest
from src.contracts.runtime import ModelResponse
from src.contracts.runtime import ModelStreamEvent
from src.contracts.runtime import ModelStreamEventType
from src.contracts.runtime import ToolCallCompletedPayload
from src.contracts.runtime import ToolCallDeltaPayload
from src.contracts.runtime import ToolCallStartedPayload
from src.exceptions import ModelCapabilityError
from src.exceptions import ModelError
from src.exceptions import ModelInvalidRequestError
from src.exceptions import ModelResponseParseError
from src.models.base import InvocationContext
from src.models.base import ProviderRegistration
from src.models.parsers.errors import map_provider_error
from src.models.selector import ModelSelector
from src.models.transport import HttpModelTransport

_PATH_BY_PROTOCOL = {
    ModelProtocol.OPENAI_CHAT: "/chat/completions",
    ModelProtocol.OPENAI_RESPONSES: "/responses",
}

type TransportFactory = Callable[[ProviderRegistration], HttpModelTransport]


class OpenAIModelAdapter:
    """选择 OpenAI protocol 并通过统一 transport 执行 invocation。"""

    def __init__(
        self,
        *,
        selector: ModelSelector,
        transport_factory: TransportFactory | None = None,
    ) -> None:
        """初始化 OpenAI 执行器。

        Args:
            selector: provider/profile/protocol 选择器。
            transport_factory: 测试或自定义 transport 工厂。
        """
        self._selector = selector
        self._transport_factory = transport_factory or _default_transport

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        """执行 blocking OpenAI 调用。

        Args:
            request: 标准模型请求，``stream`` 必须为 false。

        Returns:
            标准化最终响应。

        Raises:
            ModelError: 选择、传输或解析失败。
        """
        if request.stream:
            raise ModelInvalidRequestError(operation="invoke", data={"reason": "stream_request"})
        selected = self._selector.select(request)
        path = _require_openai_path(
            selected.context.protocol, selected.context.provider, request.model
        )
        payload = selected.protocol_adapter.build_payload(request, selected.profile)
        transport = self._transport_factory(selected.provider)
        try:
            raw = await transport.post_json(
                path, payload, timeout_seconds=selected.context.effective_timeout_seconds
            )
            return selected.protocol_adapter.parse_response(raw, selected.context)
        except ModelError:
            raise
        except ValueError as exc:
            raise ModelResponseParseError(
                provider=selected.context.provider,
                model=selected.context.model,
                protocol=selected.context.protocol.value,
                operation="parse",
                data={"reason": "invalid_json_response"},
                cause=exc,
            ) from exc
        except Exception as exc:
            raise selected.protocol_adapter.map_error(
                exc, selected.context, operation="invoke"
            ) from exc
        finally:
            await transport.close()

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]:
        """执行 streaming OpenAI 调用。

        Args:
            request: 标准模型请求，``stream`` 必须为 true。

        Yields:
            标准化流事件。

        Raises:
            ModelError: 选择、传输或协议转换失败。
        """
        if not request.stream:
            raise ModelInvalidRequestError(operation="stream", data={"reason": "blocking_request"})
        selected = self._selector.select(request)
        path = _require_openai_path(
            selected.context.protocol, selected.context.provider, request.model
        )
        payload = selected.protocol_adapter.build_payload(request, selected.profile)
        transport = self._transport_factory(selected.provider)
        partial_content_received = False
        pending_tool_call_ids: set[str] = set()
        try:
            raw_events = transport.stream_json(
                path, payload, timeout_seconds=selected.context.effective_timeout_seconds
            )
            async for event in selected.protocol_adapter.stream_events(
                raw_events, selected.context
            ):
                if event.event_type == ModelStreamEventType.CONTENT_DELTA:
                    partial_content_received = True
                elif event.event_type == ModelStreamEventType.TOOL_CALL_STARTED:
                    payload = event.payload
                    if not isinstance(payload, ToolCallStartedPayload):
                        raise _invalid_stream_payload(selected.context)
                    pending_tool_call_ids.add(payload.call_id)
                elif event.event_type == ModelStreamEventType.TOOL_CALL_DELTA:
                    payload = event.payload
                    if not isinstance(payload, ToolCallDeltaPayload):
                        raise _invalid_stream_payload(selected.context)
                    pending_tool_call_ids.add(payload.call_id)
                elif event.event_type == ModelStreamEventType.TOOL_CALL_COMPLETED:
                    payload = event.payload
                    if not isinstance(payload, ToolCallCompletedPayload):
                        raise _invalid_stream_payload(selected.context)
                    pending_tool_call_ids.discard(payload.tool_call.call_id)
                yield event
        except ModelError:
            raise
        except ValueError as exc:
            raise ModelResponseParseError(
                provider=selected.context.provider,
                model=selected.context.model,
                protocol=selected.context.protocol.value,
                operation="parse",
                data={"reason": "invalid_stream_event"},
                cause=exc,
            ) from exc
        except Exception as exc:
            raise map_provider_error(
                exc,
                selected.context,
                operation="stream",
                partial_content_received=partial_content_received,
                pending_tool_call=bool(pending_tool_call_ids),
            ) from exc
        finally:
            await transport.close()


def _default_transport(provider: ProviderRegistration) -> HttpModelTransport:
    return HttpModelTransport(
        base_url=provider.base_url,
        api_key=provider.api_key or "",
    )


def _invalid_stream_payload(context: InvocationContext) -> ModelResponseParseError:
    """创建 provider stream payload 不匹配错误。

    Args:
        context: 当前调用的安全上下文。

    Returns:
        标准模型解析错误。
    """
    return ModelResponseParseError(
        provider=context.provider,
        model=context.model,
        protocol=context.protocol.value,
        operation="parse",
        data={"reason": "stream_payload_mismatch"},
    )


def _require_openai_path(protocol: ModelProtocol, provider: str, model: str) -> str:
    try:
        return _PATH_BY_PROTOCOL[protocol]
    except KeyError as exc:
        raise ModelCapabilityError(
            provider=provider,
            model=model,
            protocol=protocol.value,
            operation="select",
            data={"reason": "unsupported_openai_protocol"},
        ) from exc
