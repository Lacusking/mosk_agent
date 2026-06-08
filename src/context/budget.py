"""上下文 token 预算与计数工具。"""

import json
from typing import Protocol

from src.contracts.runtime import JsonValue
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import TextContentBlock


class TokenCounter(Protocol):
    """可插拔 token 计数协议。"""

    def count(self, text: str) -> int:
        """计算文本 token 数。"""
        ...

    def count_message(self, message: ModelMessage) -> int:
        """计算单条模型消息 token 数。"""
        ...

    def count_messages(self, messages: list[ModelMessage]) -> int:
        """计算模型消息列表 token 总数。"""
        ...

    def count_json(self, value: JsonValue) -> int:
        """计算 JSON 值序列化后的 token 数。"""
        ...


class DefaultTokenCounter:
    """无依赖字符长度估算器。"""

    def count(self, text: str) -> int:
        """按 ``len/4`` 估算 token 数，结果至少为 1。"""
        return max(1, (len(text) + 3) // 4)

    def count_message(self, message: ModelMessage) -> int:
        """计算消息中所有内容块的估算 token 数。"""
        total = self.count(message.role.value)
        for block in message.content:
            if isinstance(block, TextContentBlock):
                total += self.count(block.text)
            else:
                total += self.count_json(block.model_dump(mode="json"))
        return max(1, total)

    def count_messages(self, messages: list[ModelMessage]) -> int:
        """计算消息列表的估算 token 总数。"""
        return sum(self.count_message(message) for message in messages)

    def count_json(self, value: JsonValue) -> int:
        """计算 JSON 值的估算 token 数。"""
        return self.count(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


class TiktokenCounter(DefaultTokenCounter):
    """基于 tiktoken 的可选精确计数器。"""

    def __init__(self, *, model_name: str = "gpt-4o-mini") -> None:
        """初始化 tiktoken 编码器。

        Raises:
            RuntimeError: 当前环境未安装 tiktoken。
        """
        try:
            import tiktoken
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise RuntimeError("tiktoken is not installed") from exc
        try:
            self._encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self._encoding = tiktoken.get_encoding("cl100k_base")

    def count(self, text: str) -> int:
        """使用 tiktoken 编码器计算 token 数。"""
        return max(1, len(self._encoding.encode(text)))


def estimate_message_tokens(message: ModelMessage) -> int:
    """以默认字符估算方式计算消息 token 数。"""
    return DefaultTokenCounter().count_message(message)


__all__ = [
    "DefaultTokenCounter",
    "TiktokenCounter",
    "TokenCounter",
    "estimate_message_tokens",
]
