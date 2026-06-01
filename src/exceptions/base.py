"""平台结构化异常基类。"""

from typing import Any


class BaseError(Exception):
    """提供机器可读错误码与公开错误数据的异常基类。"""

    code: int = 50000
    default_msg: str = "未知错误"
    http_status: int = 400

    def __init__(
        self,
        *,
        msg: str | None = None,
        data: Any = None,
        cause: Exception | None = None,
    ) -> None:
        """初始化平台异常。

        Args:
            msg: 可公开展示的错误消息；为空时使用默认消息。
            data: 可公开序列化的结构化诊断数据。
            cause: 触发当前异常的原始异常，仅供进程内追踪。
        """
        self.msg = msg or self.default_msg
        self.data = data
        self.cause = cause
        super().__init__(self.msg)

    def to_dict(self) -> dict[str, Any]:
        """序列化为可 JSON 化的公开错误结构。

        Returns:
            包含错误码、消息及可选数据的字典。
        """
        result: dict[str, Any] = {
            "code": self.code,
            "msg": self.msg,
        }
        if self.data is not None:
            result["data"] = self.data
        return result
