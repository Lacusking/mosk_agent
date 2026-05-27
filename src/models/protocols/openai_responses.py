"""OpenAI Responses wire protocol adapter。"""

import json
from collections.abc import AsyncIterator

from src.contracts.runtime import ContentDeltaPayload
from src.contracts.runtime import InvocationStartedPayload
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelRequest
from src.contracts.runtime import ModelResponse
from src.contracts.runtime import ModelResponseFormatType
from src.contracts.runtime import ModelResponseStatus
from src.contracts.runtime import ModelStopReason
from src.contracts.runtime import ModelStreamEvent
from src.contracts.runtime import ModelStreamEventType
from src.contracts.runtime import ModelToolCall
from src.contracts.runtime import ModelToolChoiceMode
from src.contracts.runtime import RefusalContentBlock
from src.contracts.runtime import ResponseCompletedPayload
from src.contracts.runtime import ResponseFailedPayload
from src.contracts.runtime import TextContentBlock
from src.contracts.runtime import ToolCallCompletedPayload
from src.contracts.runtime import ToolCallContentBlock
from src.contracts.runtime import ToolCallDeltaPayload
from src.contracts.runtime import ToolCallStartedPayload
from src.contracts.runtime import ToolResultContentBlock
from src.contracts.runtime import UsageUpdatedPayload
from src.exceptions import ModelError
from src.exceptions import ModelResponseParseError
from src.models.base import InvocationContext
from src.models.parsers.common import map_finish_reason
from src.models.parsers.common import parse_tool_arguments
from src.models.parsers.common import parse_usage
from src.models.parsers.errors import map_provider_error
from src.models.profiles import ModelProfile


class OpenAIResponsesProtocolAdapter:
    """将 Responses API 编解码为统一模型契约。"""

    protocol = ModelProtocol.OPENAI_RESPONSES

    def build_payload(self, request: ModelRequest, profile: ModelProfile) -> dict[str, object]:
        """构造 Responses API 请求体。

        Args:
            request: 统一请求。
            profile: 已选择的 profile。

        Returns:
            不含凭证和 timeout 的 wire 请求体。
        """
        payload: dict[str, object] = {
            "model": request.model,
            "input": [_encode_input_message(message) for message in request.messages],
        }
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema,
                    "strict": tool.strict,
                }
                for tool in request.tools
            ]
        if request.tool_choice is not None:
            if request.tool_choice.mode == ModelToolChoiceMode.NAMED:
                payload["tool_choice"] = {
                    "type": "function",
                    "name": request.tool_choice.name,
                }
            else:
                payload["tool_choice"] = request.tool_choice.mode.value
        if request.response_format is not None:
            if request.response_format.type == ModelResponseFormatType.JSON_SCHEMA:
                payload["text"] = {
                    "format": {
                        "type": "json_schema",
                        "schema": request.response_format.json_schema,
                    }
                }
            elif request.response_format.type != ModelResponseFormatType.TEXT:
                payload["text"] = {"format": {"type": request.response_format.type.value}}
        options = request.options
        for field_name in ("temperature", "max_output_tokens", "top_p", "parallel_tool_calls"):
            value = getattr(options, field_name)
            if value is not None:
                payload[field_name] = value
        if options.stop_sequences is not None:
            payload["stop"] = options.stop_sequences
        payload.update(options.provider_options)
        if request.stream:
            payload["stream"] = True
        return payload

    def parse_response(self, response: object, context: InvocationContext) -> ModelResponse:
        """解析 Responses blocking 输出。

        Args:
            response: provider JSON object。
            context: 安全调用上下文。

        Returns:
            标准响应。

        Raises:
            ModelResponseParseError: 输出 item 无法解释。
        """
        if not isinstance(response, dict):
            raise _parse_error(context, "response_not_object")
        content: list = []
        tool_calls: list[ModelToolCall] = []
        for item in _as_dict_list(response.get("output")):
            item_type = item.get("type")
            if item_type == "function_call":
                call_id = item.get("call_id") or item.get("id")
                name = item.get("name")
                if not isinstance(call_id, str) or not isinstance(name, str):
                    raise _parse_error(context, "function_call_incomplete")
                tool_calls.append(
                    parse_tool_arguments(
                        call_id=call_id,
                        provider_call_id=call_id,
                        name=name,
                        arguments=item.get("arguments"),
                        context=context,
                    )
                )
            elif item_type == "message":
                for block in _as_dict_list(item.get("content")):
                    if block.get("type") == "output_text":
                        text = block.get("text")
                        if isinstance(text, str) and text:
                            content.append(TextContentBlock(text=text))
                    elif block.get("type") == "refusal":
                        refusal = block.get("refusal")
                        if isinstance(refusal, str) and refusal:
                            content.append(RefusalContentBlock(refusal=refusal))
            elif item_type == "refusal":
                refusal = item.get("refusal")
                if isinstance(refusal, str) and refusal:
                    content.append(RefusalContentBlock(refusal=refusal))
        provider_reason = _response_reason(response)
        if tool_calls:
            status, stop_reason = ModelResponseStatus.COMPLETED, ModelStopReason.TOOL_USE
        elif any(isinstance(block, RefusalContentBlock) for block in content):
            status, stop_reason = ModelResponseStatus.REFUSED, ModelStopReason.REFUSED
        elif response.get("status") == "completed":
            status, stop_reason = ModelResponseStatus.COMPLETED, ModelStopReason.COMPLETED
        else:
            status, stop_reason = map_finish_reason(provider_reason)
        return ModelResponse(
            invocation_id=context.invocation_id,
            provider=context.provider,
            model=_actual_model(response, context),
            protocol=context.protocol,
            content=content,
            tool_calls=tool_calls,
            status=status,
            stop_reason=stop_reason,
            provider_stop_reason=provider_reason,
            usage=parse_usage(response.get("usage")),
        )

    async def stream_events(
        self,
        events: AsyncIterator[dict[str, object]],
        context: InvocationContext,
    ) -> AsyncIterator[ModelStreamEvent]:
        """转换 Responses 语义化流事件。

        Args:
            events: provider SSE JSON 事件。
            context: 安全调用上下文。

        Yields:
            统一模型流事件。
        """
        sequence = 0
        yield _stream_event(
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
        pending: dict[str, dict[str, str]] = {}
        completed_ids: set[str] = set()
        completed_response: dict[str, object] | None = None
        async for event in events:
            event_type = event.get("type")
            if event_type == "response.output_text.delta":
                delta = event.get("delta")
                if isinstance(delta, str) and delta:
                    yield _stream_event(
                        context,
                        sequence,
                        ModelStreamEventType.CONTENT_DELTA,
                        ContentDeltaPayload(delta=delta),
                    )
                    sequence += 1
            elif event_type == "response.output_item.added":
                item = event.get("item")
                if isinstance(item, dict) and item.get("type") == "function_call":
                    call_id = item.get("call_id") or item.get("id")
                    name = item.get("name")
                    if isinstance(call_id, str) and isinstance(name, str):
                        pending[call_id] = {"name": name, "args": ""}
                        yield _stream_event(
                            context,
                            sequence,
                            ModelStreamEventType.TOOL_CALL_STARTED,
                            ToolCallStartedPayload(
                                call_id=call_id, name=name, provider_call_id=call_id
                            ),
                        )
                        sequence += 1
            elif event_type == "response.function_call_arguments.delta":
                call_id = event.get("call_id") or event.get("item_id")
                delta = event.get("delta")
                if isinstance(call_id, str) and isinstance(delta, str) and delta:
                    info = pending.setdefault(call_id, {"name": _name(event), "args": ""})
                    info["args"] += delta
                    yield _stream_event(
                        context,
                        sequence,
                        ModelStreamEventType.TOOL_CALL_DELTA,
                        ToolCallDeltaPayload(call_id=call_id, arguments_delta=delta),
                    )
                    sequence += 1
            elif event_type == "response.function_call_arguments.done":
                call_id = event.get("call_id") or event.get("item_id")
                if isinstance(call_id, str):
                    info = pending.setdefault(call_id, {"name": _name(event), "args": ""})
                    if not info["name"]:
                        raise _parse_error(context, "function_call_missing_name")
                    arguments = event.get("arguments")
                    if isinstance(arguments, str):
                        info["args"] = arguments
                    tool_call = parse_tool_arguments(
                        call_id=call_id,
                        provider_call_id=call_id,
                        name=info["name"],
                        arguments=info["args"],
                        context=context,
                    )
                    completed_ids.add(call_id)
                    yield _stream_event(
                        context,
                        sequence,
                        ModelStreamEventType.TOOL_CALL_COMPLETED,
                        ToolCallCompletedPayload(tool_call=tool_call),
                    )
                    sequence += 1
            elif event_type == "response.completed":
                response = event.get("response")
                if isinstance(response, dict):
                    completed_response = response
            elif event_type in {"response.failed", "error"}:
                yield _stream_event(
                    context,
                    sequence,
                    ModelStreamEventType.RESPONSE_FAILED,
                    ResponseFailedPayload(
                        error_type="ModelUnavailableError",
                        message="provider stream failed",
                        retryable=True,
                        fallback_allowed=True,
                        provider_error_code=_safe_error_code(event),
                    ),
                )
                return
        if completed_response is None:
            yield _stream_event(
                context,
                sequence,
                ModelStreamEventType.RESPONSE_FAILED,
                ResponseFailedPayload(
                    error_type="ModelStreamInterruptedError",
                    message="provider stream ended before completion",
                    retryable=True,
                    fallback_allowed=True,
                ),
            )
            return
        final = self.parse_response(completed_response, context)
        for tool_call in final.tool_calls:
            if tool_call.call_id not in completed_ids:
                yield _stream_event(
                    context,
                    sequence,
                    ModelStreamEventType.TOOL_CALL_COMPLETED,
                    ToolCallCompletedPayload(tool_call=tool_call),
                )
                sequence += 1
        if final.usage is not None:
            yield _stream_event(
                context,
                sequence,
                ModelStreamEventType.USAGE_UPDATED,
                UsageUpdatedPayload(usage=final.usage),
            )
            sequence += 1
        yield _stream_event(
            context,
            sequence,
            ModelStreamEventType.RESPONSE_COMPLETED,
            ResponseCompletedPayload(
                status=final.status,
                stop_reason=final.stop_reason,
                provider_stop_reason=final.provider_stop_reason,
                usage=final.usage,
            ),
        )

    def map_error(
        self, error: Exception, context: InvocationContext, *, operation: str
    ) -> ModelError:
        """映射 Responses transport failure。

        Args:
            error: transport 错误。
            context: 安全调用上下文。
            operation: 当前操作。

        Returns:
            标准模型错误。
        """
        return map_provider_error(error, context, operation=operation)


def _encode_input_message(message: ModelMessage) -> dict[str, object]:
    tool_results = [block for block in message.content if isinstance(block, ToolResultContentBlock)]
    if tool_results:
        block = tool_results[0]
        return {
            "type": "function_call_output",
            "call_id": block.call_id,
            "output": block.output if isinstance(block.output, str) else json.dumps(block.output),
        }
    tool_calls = [block for block in message.content if isinstance(block, ToolCallContentBlock)]
    if tool_calls:
        block = tool_calls[0]
        return {
            "type": "function_call",
            "call_id": block.provider_call_id or block.call_id,
            "name": block.name,
            "arguments": json.dumps(block.arguments),
        }
    content = [
        {"type": "input_text", "text": block.text}
        for block in message.content
        if isinstance(block, TextContentBlock)
    ]
    return {"role": message.role.value, "content": content}


def _response_reason(response: dict[str, object]) -> str | None:
    status = response.get("status")
    if status == "completed":
        return "completed"
    details = response.get("incomplete_details")
    if isinstance(details, dict) and isinstance(details.get("reason"), str):
        return details["reason"]
    return status if isinstance(status, str) else None


def _actual_model(response: dict[str, object], context: InvocationContext) -> str:
    model = response.get("model")
    return model if isinstance(model, str) and model else context.model


def _safe_error_code(event: dict[str, object]) -> str | None:
    error = event.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    return str(code) if code is not None else None


def _name(event: dict[str, object]) -> str:
    name = event.get("name")
    return name if isinstance(name, str) and name else ""


def _as_dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _parse_error(context: InvocationContext, reason: str) -> ModelResponseParseError:
    return ModelResponseParseError(
        provider=context.provider,
        model=context.model,
        protocol=context.protocol.value,
        operation="parse",
        data={"reason": reason},
    )


def _stream_event(
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
