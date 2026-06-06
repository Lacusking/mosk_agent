"""Provider transport/protocol 错误到标准模型错误的映射。"""

from typing import Any

import httpx

from src.exceptions import ModelAuthenticationError
from src.exceptions import ModelAuthorizationError
from src.exceptions import ModelContextLengthError
from src.exceptions import ModelError
from src.exceptions import ModelInvalidRequestError
from src.exceptions import ModelRateLimitError
from src.exceptions import ModelStreamInterruptedError
from src.exceptions import ModelTimeoutError
from src.exceptions import ModelUnavailableError
from src.models.base import InvocationContext


def map_provider_error(
    error: Exception,
    context: InvocationContext,
    *,
    operation: str,
    partial_content_received: bool = False,
    pending_tool_call: bool = False,
) -> ModelError:
    """将 transport failure 映射为可判定且不泄密的模型错误。

    Args:
        error: transport 或 provider 状态异常。
        context: 当前调用安全上下文。
        operation: ``invoke`` 或 ``stream``。
        partial_content_received: stream 是否已输出文本。
        pending_tool_call: stream 是否存在未完成工具意图。

    Returns:
        标准化模型错误。
    """
    common: dict[str, Any] = {
        "provider": context.provider,
        "model": context.model,
        "protocol": context.protocol.value,
        "operation": operation,
    }
    if isinstance(error, httpx.TimeoutException):
        if operation == "stream" and (partial_content_received or pending_tool_call):
            return ModelStreamInterruptedError(
                **common,
                partial_content_received=partial_content_received,
                pending_tool_call=pending_tool_call,
                data={"reason": "timeout"},
                cause=error,
            )
        return ModelTimeoutError(**common, cause=error)

    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        code = _provider_error_code(error.response)
        fields = {**common, "provider_status_code": status, "provider_error_code": code}
        if code == "context_length_exceeded":
            token_info = _provider_token_info(error.response)
            return ModelContextLengthError(
                **fields,
                prompt_tokens=token_info.get("prompt_tokens"),
                max_context_tokens=token_info.get("max_context_tokens"),
                cause=error,
            )
        if status == 401:
            return ModelAuthenticationError(**fields, cause=error)
        if status == 403:
            return ModelAuthorizationError(**fields, cause=error)
        if status == 429:
            return ModelRateLimitError(
                **fields,
                retry_after_seconds=_retry_after(error.response),
                cause=error,
            )
        if status in (408, 504):
            return ModelTimeoutError(**fields, cause=error)
        if status >= 500:
            return ModelUnavailableError(**fields, cause=error)
        return ModelInvalidRequestError(**fields, cause=error)

    if operation == "stream":
        return ModelStreamInterruptedError(
            **common,
            partial_content_received=partial_content_received,
            pending_tool_call=pending_tool_call,
            cause=error,
        )
    return ModelUnavailableError(**common, cause=error)


def _provider_error_code(response: httpx.Response) -> str | None:
    """读取 provider 返回的安全机器错误码。"""
    error = _provider_error_body(response)
    if error is None:
        return None
    code = error.get("code")
    return str(code) if code is not None else None


def _provider_error_body(response: httpx.Response) -> dict[str, Any] | None:
    """读取 provider error 对象。"""
    try:
        parsed = response.json()
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    error = parsed.get("error")
    if not isinstance(error, dict):
        return None
    return error


def _provider_token_info(response: httpx.Response) -> dict[str, int | None]:
    """从 provider error 中提取安全 token 诊断信息。"""
    error = _provider_error_body(response) or {}
    return {
        "prompt_tokens": _as_int(
            error.get("prompt_tokens")
            or error.get("tokens")
            or error.get("input_tokens")
        ),
        "max_context_tokens": _as_int(
            error.get("max_context_tokens")
            or error.get("context_window")
            or error.get("max_tokens")
        ),
    }


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _retry_after(response: httpx.Response) -> float | None:
    """解析标准 Retry-After 秒数。"""
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None
