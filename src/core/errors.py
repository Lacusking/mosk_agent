"""
结构化异常体系

提供跨模块复用的异常基类与常用业务异常。
"""

from typing import Any


class BaseError(Exception):
    """
    结构化异常基类。

    同时保留机器可读错误码与人类可读错误信息。
    """

    code: int = 50000
    default_msg: str = "未知错误"

    def __init__(
        self,
        *,
        msg: str | None = None,
        data: Any = None,
        cause: Exception | None = None,
    ) -> None:
        self.msg = msg or self.default_msg
        self.data = data
        self.cause = cause
        super().__init__(self.msg)

    def to_dict(self) -> dict[str, Any]:
        """序列化为可 JSON 化的字典。"""
        result: dict[str, Any] = {
            "code": self.code,
            "msg": self.msg,
        }
        if self.data is not None:
            result["data"] = self.data
        return result


class ValidationError(BaseError):
    """参数校验异常。"""

    code = 40000
    default_msg = "参数校验失败"


class NotFoundError(BaseError):
    """资源不存在异常。"""

    code = 40400
    default_msg = "资源不存在"


class AuthenticationError(BaseError):
    """认证异常。"""

    code = 40100
    default_msg = "认证失败"


class ForbiddenError(BaseError):
    """禁止访问异常。"""

    code = 40300
    default_msg = "禁止访问"


class ConfigurationError(BaseError):
    """配置异常。"""

    code = 50001
    default_msg = "配置错误"


class StorageError(BaseError):
    """存储异常。"""

    code = 50002
    default_msg = "存储操作失败"
