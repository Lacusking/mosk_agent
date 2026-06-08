"""模型调用域异常类型。"""

from collections.abc import Mapping
from typing import Any

from src.exceptions.base import BaseError

_REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "authorization_header",
        "credential",
        "credentials",
        "headers",
        "messages",
        "password",
        "prompt",
        "raw_request",
        "raw_response",
        "secret",
        "token",
        "tool_arguments",
        "wire_payload",
    }
)


def _sanitize_data(value: Any) -> Any:
    """清洗允许随模型异常公开的诊断数据。

    Args:
        value: 待清洗的数据值。

    Returns:
        移除敏感字段内容后的数据副本。
    """
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            result[str(key)] = (
                _REDACTED if normalized_key in _SENSITIVE_KEYS else _sanitize_data(item)
            )
        return result
    if isinstance(value, list):
        return [_sanitize_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_data(item) for item in value)
    return value


class ModelError(BaseError):
    """模型调用异常基类，提供供 runtime 判定的安全元数据。"""

    code = 52000
    default_msg = "模型调用失败"
    retryable: bool = False
    fallback_allowed: bool = False

    def __init__(
        self,
        *,
        msg: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        protocol: str | None = None,
        operation: str | None = None,
        retryable: bool | None = None,
        fallback_allowed: bool | None = None,
        provider_error_code: str | None = None,
        provider_status_code: int | None = None,
        retry_after_seconds: float | None = None,
        data: Mapping[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """初始化标准化模型异常。

        Args:
            msg: 可公开错误消息。
            provider: 实际模型供应商标识。
            model: 实际模型标识。
            protocol: 使用的 wire protocol 标识。
            operation: 失败操作，例如 ``invoke``、``stream`` 或 ``parse``。
            retryable: 后续 runtime 是否可考虑重试；为空时使用类型默认值。
            fallback_allowed: 后续 runtime 是否可考虑 fallback。
            provider_error_code: 供应商返回的安全错误码。
            provider_status_code: 供应商返回的 HTTP 状态码。
            retry_after_seconds: 可重试错误的建议等待秒数。
            data: 经清洗后允许公开的附加诊断数据。
            cause: 原始异常，仅保留在进程内。

        Raises:
            ValueError: ``retry_after_seconds`` 小于零。
        """
        if retry_after_seconds is not None and retry_after_seconds < 0:
            raise ValueError("retry_after_seconds 不能小于零")

        self.provider = provider
        self.model = model
        self.protocol = protocol
        self.operation = operation
        self.retryable = self.__class__.retryable if retryable is None else retryable
        self.fallback_allowed = (
            self.__class__.fallback_allowed if fallback_allowed is None else fallback_allowed
        )
        self.provider_error_code = provider_error_code
        self.provider_status_code = provider_status_code
        self.retry_after_seconds = retry_after_seconds

        details: dict[str, Any] = {
            "error_type": self.__class__.__name__,
            "retryable": self.retryable,
            "fallback_allowed": self.fallback_allowed,
        }
        for key, value in {
            "provider": provider,
            "model": model,
            "protocol": protocol,
            "operation": operation,
            "provider_error_code": provider_error_code,
            "provider_status_code": provider_status_code,
            "retry_after_seconds": retry_after_seconds,
        }.items():
            if value is not None:
                details[key] = value
        if data:
            details["details"] = _sanitize_data(data)

        super().__init__(msg=msg, data=details, cause=cause)


class ModelConfigurationError(ModelError):
    """模型配置缺失或无效。"""

    code = 52001
    default_msg = "模型配置错误"


class ModelAuthenticationError(ModelError):
    """模型供应商认证失败。"""

    code = 52101
    default_msg = "模型认证失败"


class ModelAuthorizationError(ModelError):
    """模型供应商授权失败。"""

    code = 52103
    default_msg = "模型访问被拒绝"


class ModelRateLimitError(ModelError):
    """模型调用受到限流。"""

    code = 52229
    default_msg = "模型调用受到限流"
    retryable = True
    fallback_allowed = True


class ModelTimeoutError(ModelError):
    """模型调用超时。"""

    code = 52408
    default_msg = "模型调用超时"
    retryable = True
    fallback_allowed = True


class ModelUnavailableError(ModelError):
    """模型供应商临时不可用。"""

    code = 52503
    default_msg = "模型服务暂时不可用"
    retryable = True
    fallback_allowed = True


class ModelInvalidRequestError(ModelError):
    """模型请求不满足协议要求。"""

    code = 52400
    default_msg = "模型请求非法"


class ModelContextLengthError(ModelError):
    """模型请求上下文超过 provider context window。"""

    code = 52413
    default_msg = "模型上下文长度超限"
    retryable = True

    def __init__(
        self,
        *,
        prompt_tokens: int | None = None,
        max_context_tokens: int | None = None,
        data: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """初始化上下文超限错误。"""
        details = dict(data or {})
        provider_reported_tokens: dict[str, int] = {}
        if prompt_tokens is not None:
            details["prompt_tokens"] = prompt_tokens
            provider_reported_tokens["prompt_tokens"] = prompt_tokens
        if max_context_tokens is not None:
            details["max_context_tokens"] = max_context_tokens
            provider_reported_tokens["max_context_tokens"] = max_context_tokens
        if provider_reported_tokens:
            details["provider_reported_tokens"] = provider_reported_tokens
        super().__init__(data=details, **kwargs)


class ModelCapabilityError(ModelError):
    """目标模型不具备请求所需能力。"""

    code = 52422
    default_msg = "模型能力不支持该请求"


class ModelResponseParseError(ModelError):
    """供应商响应无法被协议解析。"""

    code = 52520
    default_msg = "模型响应解析失败"


class ModelStreamInterruptedError(ModelError):
    """模型流在完成边界前中断。"""

    code = 52521
    default_msg = "模型流式响应中断"
    retryable = True
    fallback_allowed = True

    def __init__(
        self,
        *,
        partial_content_received: bool = False,
        pending_tool_call: bool = False,
        data: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """初始化可供 runtime 判定部分状态的流中断异常。

        Args:
            partial_content_received: 中断前是否已有内容增量。
            pending_tool_call: 中断前是否存在尚未完成的工具意图。
            data: 其他允许公开的安全诊断数据。
            **kwargs: ``ModelError`` 支持的标准字段。
        """
        details = dict(data or {})
        details.update(
            {
                "partial_content_received": partial_content_received,
                "pending_tool_call": pending_tool_call,
            }
        )
        super().__init__(data=details, **kwargs)


class ModelSafetyError(ModelError):
    """模型调用被供应商安全策略阻断。"""

    code = 52451
    default_msg = "模型请求被安全策略阻断"
