"""OpenAI Chat Completions wire protocol adapter。"""

import json
from collections.abc import AsyncIterator

from src.contracts.runtime import ContentDeltaPayload
from src.contracts.runtime import ImageContentBlock
from src.contracts.runtime import InvocationStartedPayload
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelRequest
from src.contracts.runtime import ModelResponse
from src.contracts.runtime import ModelResponseFormatType
from src.contracts.runtime import ModelStreamEvent
from src.contracts.runtime import ModelStreamEventType
from src.contracts.runtime import ModelToolChoiceMode
from src.contracts.runtime import ModelUsage
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


class OpenAIChatProtocolAdapter:
    """将 Chat Completions 编解码为统一模型契约。"""

    protocol = ModelProtocol.OPENAI_CHAT

    def build_payload(self, request: ModelRequest, profile: ModelProfile) -> dict[str, object]:
        """构造 Chat Completions 请求体。

        Args:
            request: 统一请求。
            profile: 已选择的 profile。

        Returns:
            不包含认证与调用 timeout 的请求体。
        """
        payload: dict[str, object] = {
            "model": request.model,
            "messages": [_encode_message(message) for message in request.messages],
        }
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters_schema,
                        "strict": tool.strict,
                    },
                }
                for tool in request.tools
            ]
        if request.tool_choice is not None:
            if request.tool_choice.mode == ModelToolChoiceMode.NAMED:
                payload["tool_choice"] = {
                    "type": "function",
                    "function": {"name": request.tool_choice.name},
                }
            else:
                payload["tool_choice"] = request.tool_choice.mode.value
        if request.response_format is not None:
            response_type = request.response_format.type
            if response_type == ModelResponseFormatType.JSON_SCHEMA:
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": request.response_format.json_schema,
                }
            else:
                payload["response_format"] = {"type": response_type.value}
        options = request.options
        for field_name, wire_name in {
            "temperature": "temperature",
            "max_output_tokens": "max_completion_tokens",
            "top_p": "top_p",
            "stop_sequences": "stop",
            "parallel_tool_calls": "parallel_tool_calls",
        }.items():
            value = getattr(options, field_name)
            if value is not None:
                payload[wire_name] = value
        payload.update(options.provider_options)
        if request.stream:
            payload["stream"] = True
            payload["stream_options"] = {"include_usage": True}
        return payload

    def parse_response(self, response: object, context: InvocationContext) -> ModelResponse:
        """解析 Chat Completions blocking 响应。

        Args:
            response: provider JSON object。
            context: 安全调用上下文。

        Returns:
            标准响应。

        Raises:
            ModelResponseParseError: provider 返回结构损坏。
        """
        if not isinstance(response, dict):
            raise _parse_error(context, "response_not_object")
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise _parse_error(context, "missing_choice")
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, dict):
            raise _parse_error(context, "missing_message")
        provider_reason = choice.get("finish_reason")
        reason = provider_reason if isinstance(provider_reason, str) else None
        tool_calls = _parse_tool_calls(message.get("tool_calls"), context)
        status, stop_reason = map_finish_reason("tool_calls" if tool_calls else reason)
        content = []
        text = message.get("content")
        refusal = message.get("refusal")
        if isinstance(text, str) and text:
            content.append(TextContentBlock(text=text))
        if isinstance(refusal, str) and refusal:
            content.append(RefusalContentBlock(refusal=refusal))
            status, stop_reason = map_finish_reason("refusal")
        return ModelResponse(
            invocation_id=context.invocation_id,
            provider=context.provider,
            model=_actual_model(response, context),
            protocol=context.protocol,
            content=content,
            tool_calls=tool_calls,
            status=status,
            stop_reason=stop_reason,
            provider_stop_reason=reason,
            usage=parse_usage(response.get("usage")),
        )

    async def stream_events(
        self,
        events: AsyncIterator[dict[str, object]],
        context: InvocationContext,
    ) -> AsyncIterator[ModelStreamEvent]:
        """转换 Chat Completions SSE chunks。

        Args:
            events: provider SSE JSON 数据。
            context: 安全调用上下文。

        Yields:
            统一流事件。

        Raises:
            ModelResponseParseError: 完成时工具参数仍非法。
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
        pending: dict[int, dict[str, str]] = {}
        provider_reason: str | None = None
        usage: ModelUsage | None = None
        async for chunk in events:
            error = chunk.get("error")
            if isinstance(error, dict):
                code = error.get("code")
                yield _stream_event(
                    context,
                    sequence,
                    ModelStreamEventType.RESPONSE_FAILED,
                    ResponseFailedPayload(
                        error_type="ModelUnavailableError",
                        message="provider stream failed",
                        retryable=True,
                        fallback_allowed=True,
                        provider_error_code=str(code) if code is not None else None,
                    ),
                )
                return
            parsed_usage = parse_usage(chunk.get("usage"))
            if parsed_usage is not None:
                usage = parsed_usage
                yield _stream_event(
                    context,
                    sequence,
                    ModelStreamEventType.USAGE_UPDATED,
                    UsageUpdatedPayload(usage=parsed_usage),
                )
                sequence += 1
            choices = chunk.get("choices")
            if not isinstance(choices, list):
                continue
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                delta = choice.get("delta")
                if isinstance(delta, dict):
                    text = delta.get("content")
                    if isinstance(text, str) and text:
                        yield _stream_event(
                            context,
                            sequence,
                            ModelStreamEventType.CONTENT_DELTA,
                            ContentDeltaPayload(delta=text),
                        )
                        sequence += 1
                    for raw_tool in _as_dict_list(delta.get("tool_calls")):
                        index = raw_tool.get("index")
                        if not isinstance(index, int):
                            raise _parse_error(context, "tool_delta_missing_index")
                        call = pending.setdefault(
                            index, {"id": f"call_{index}", "name": "", "args": ""}
                        )
                        call_id = raw_tool.get("id")
                        if isinstance(call_id, str) and call_id:
                            call["id"] = call_id
                        function = raw_tool.get("function")
                        if isinstance(function, dict):
                            name = function.get("name")
                            if isinstance(name, str) and name and not call["name"]:
                                call["name"] = name
                                yield _stream_event(
                                    context,
                                    sequence,
                                    ModelStreamEventType.TOOL_CALL_STARTED,
                                    ToolCallStartedPayload(
                                        call_id=call["id"],
                                        name=name,
                                        provider_call_id=call["id"],
                                    ),
                                )
                                sequence += 1
                            arguments = function.get("arguments")
                            if isinstance(arguments, str) and arguments:
                                call["args"] += arguments
                                yield _stream_event(
                                    context,
                                    sequence,
                                    ModelStreamEventType.TOOL_CALL_DELTA,
                                    ToolCallDeltaPayload(
                                        call_id=call["id"], arguments_delta=arguments
                                    ),
                                )
                                sequence += 1
                finish_reason = choice.get("finish_reason")
                if isinstance(finish_reason, str):
                    provider_reason = finish_reason
        if provider_reason is None:
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
        for index in sorted(pending):
            tool = pending[index]
            if not tool["name"]:
                raise _parse_error(context, "tool_call_missing_name")
            completed = parse_tool_arguments(
                call_id=tool["id"],
                provider_call_id=tool["id"],
                name=tool["name"],
                arguments=tool["args"],
                context=context,
            )
            yield _stream_event(
                context,
                sequence,
                ModelStreamEventType.TOOL_CALL_COMPLETED,
                ToolCallCompletedPayload(tool_call=completed),
            )
            sequence += 1
        status, stop_reason = map_finish_reason("tool_calls" if pending else provider_reason)
        yield _stream_event(
            context,
            sequence,
            ModelStreamEventType.RESPONSE_COMPLETED,
            ResponseCompletedPayload(
                status=status,
                stop_reason=stop_reason,
                provider_stop_reason=provider_reason,
                usage=usage,
            ),
        )

    def map_error(
        self, error: Exception, context: InvocationContext, *, operation: str
    ) -> ModelError:
        """映射 Chat transport failure。

        Args:
            error: transport 错误。
            context: 安全调用上下文。
            operation: 当前操作。

        Returns:
            标准模型错误。
        """
        return map_provider_error(error, context, operation=operation)


def _encode_message(message: ModelMessage) -> dict[str, object]:
    tool_results = [block for block in message.content if isinstance(block, ToolResultContentBlock)]
    if tool_results:
        block = tool_results[0]
        content = block.output if isinstance(block.output, str) else json.dumps(block.output)
        return {"role": "tool", "tool_call_id": block.call_id, "content": content}
    tool_calls = [block for block in message.content if isinstance(block, ToolCallContentBlock)]
    if tool_calls:
        return {
            "role": message.role.value,
            "tool_calls": [
                {
                    "id": block.provider_call_id or block.call_id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.arguments),
                    },
                }
                for block in tool_calls
            ],
        }
    images = [block for block in message.content if isinstance(block, ImageContentBlock)]
    texts = [block.text for block in message.content if isinstance(block, TextContentBlock)]
    if images:
        content: list[dict[str, object]] = [{"type": "text", "text": text} for text in texts]
        content.extend(
            {
                "type": "image_url",
                "image_url": {"url": image.url, "detail": image.detail or "auto"},
            }
            for image in images
        )
        return {"role": message.role.value, "content": content}
    return {"role": message.role.value, "content": "\n".join(texts)}


def _parse_tool_calls(raw: object, context: InvocationContext) -> list:
    calls = []
    for index, raw_call in enumerate(_as_dict_list(raw)):
        provider_id = raw_call.get("id")
        function = raw_call.get("function")
        if not isinstance(function, dict):
            raise _parse_error(context, "tool_call_missing_function")
        name = function.get("name")
        if not isinstance(name, str) or not name:
            raise _parse_error(context, "tool_call_missing_name")
        call_id = provider_id if isinstance(provider_id, str) and provider_id else f"call_{index}"
        calls.append(
            parse_tool_arguments(
                call_id=call_id,
                provider_call_id=call_id,
                name=name,
                arguments=function.get("arguments"),
                context=context,
            )
        )
    return calls


def _actual_model(response: dict[str, object], context: InvocationContext) -> str:
    model = response.get("model")
    return model if isinstance(model, str) and model else context.model


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
