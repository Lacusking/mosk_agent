"""不同模型 protocol 可共享的安全解析函数。"""

import json
from typing import Any

from src.contracts.runtime import ModelResponseStatus
from src.contracts.runtime import ModelStopReason
from src.contracts.runtime import ModelToolCall
from src.contracts.runtime import ModelUsage
from src.exceptions import ModelResponseParseError
from src.models.base import InvocationContext


def parse_tool_arguments(
    *,
    call_id: str,
    name: str,
    arguments: object,
    context: InvocationContext,
    provider_call_id: str | None = None,
) -> ModelToolCall:
    """将已完成工具参数解析为统一 tool call。

    Args:
        call_id: 统一工具调用 id。
        name: 工具名称。
        arguments: provider arguments object 或 JSON 字符串。
        context: 安全调用上下文。
        provider_call_id: provider 原始调用 id。

    Returns:
        已校验工具调用。

    Raises:
        ModelResponseParseError: 参数并非合法 JSON object。
    """
    try:
        parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
    except json.JSONDecodeError as exc:
        raise ModelResponseParseError(
            provider=context.provider,
            model=context.model,
            protocol=context.protocol.value,
            operation="parse",
            data={"reason": "invalid_tool_arguments", "call_id": call_id},
            cause=exc,
        ) from exc
    if not isinstance(parsed, dict):
        raise ModelResponseParseError(
            provider=context.provider,
            model=context.model,
            protocol=context.protocol.value,
            operation="parse",
            data={"reason": "tool_arguments_not_object", "call_id": call_id},
        )
    return ModelToolCall(
        call_id=call_id,
        provider_call_id=provider_call_id,
        name=name,
        arguments=parsed,
    )


def parse_usage(raw: object) -> ModelUsage | None:
    """映射 OpenAI 风格 token usage。

    Args:
        raw: provider usage object。

    Returns:
        provider 未提供 usage 时返回 ``None``，否则返回统一 usage。
    """
    if not isinstance(raw, dict):
        return None
    input_details = raw.get("input_tokens_details") or raw.get("prompt_tokens_details") or {}
    output_details = raw.get("output_tokens_details") or raw.get("completion_tokens_details") or {}
    if not isinstance(input_details, dict):
        input_details = {}
    if not isinstance(output_details, dict):
        output_details = {}
    return ModelUsage(
        input_tokens=_int_or_none(raw.get("input_tokens", raw.get("prompt_tokens"))),
        output_tokens=_int_or_none(raw.get("output_tokens", raw.get("completion_tokens"))),
        total_tokens=_int_or_none(raw.get("total_tokens")),
        cached_input_tokens=_int_or_none(input_details.get("cached_tokens")),
        reasoning_tokens=_int_or_none(output_details.get("reasoning_tokens")),
    )


def map_finish_reason(reason: str | None) -> tuple[ModelResponseStatus, ModelStopReason]:
    """将 provider 停止原因映射到统一响应语义。

    Args:
        reason: provider 原始停止原因。

    Returns:
        统一 status 与 stop reason 组合。
    """
    mappings = {
        "stop": (ModelResponseStatus.COMPLETED, ModelStopReason.COMPLETED),
        "completed": (ModelResponseStatus.COMPLETED, ModelStopReason.COMPLETED),
        "tool_calls": (ModelResponseStatus.COMPLETED, ModelStopReason.TOOL_USE),
        "function_call": (ModelResponseStatus.COMPLETED, ModelStopReason.TOOL_USE),
        "length": (ModelResponseStatus.INCOMPLETE, ModelStopReason.MAX_TOKENS),
        "max_output_tokens": (ModelResponseStatus.INCOMPLETE, ModelStopReason.MAX_TOKENS),
        "max_tokens": (ModelResponseStatus.INCOMPLETE, ModelStopReason.MAX_TOKENS),
        "content_filter": (ModelResponseStatus.INCOMPLETE, ModelStopReason.CONTENT_FILTERED),
        "content_filtered": (ModelResponseStatus.INCOMPLETE, ModelStopReason.CONTENT_FILTERED),
        "refusal": (ModelResponseStatus.REFUSED, ModelStopReason.REFUSED),
        "refused": (ModelResponseStatus.REFUSED, ModelStopReason.REFUSED),
    }
    return mappings.get(reason or "", (ModelResponseStatus.INCOMPLETE, ModelStopReason.UNKNOWN))


def _int_or_none(value: Any) -> int | None:
    """将 provider 整数统计字段安全映射为空或整数。"""
    return value if isinstance(value, int) and not isinstance(value, bool) else None
