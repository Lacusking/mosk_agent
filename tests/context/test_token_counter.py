"""上下文 token counter 测试。"""

import sys

import pytest

from src.context import DefaultTokenCounter
from src.context import TiktokenCounter
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import ModelRole
from src.contracts.runtime import TextContentBlock


def test_default_token_counter_counts_text_and_messages() -> None:
    """默认估算器返回正整数并支持消息列表。"""
    counter = DefaultTokenCounter()
    message = ModelMessage(
        role=ModelRole.USER,
        content=[TextContentBlock(text="hello world")],
    )

    assert counter.count("hello") > 0
    assert counter.count_message(message) > 0
    assert counter.count_messages([message, message]) == counter.count_message(message) * 2


def test_tiktoken_counter_is_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    """未安装 tiktoken 时精确计数器给出明确错误。"""
    monkeypatch.setitem(sys.modules, "tiktoken", None)

    with pytest.raises(RuntimeError, match="tiktoken"):
        TiktokenCounter()
