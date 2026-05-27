"""Anthropic Messages 协议身份保留模块。

本变更不提供可注册或可执行的 Anthropic protocol adapter。
"""

from src.contracts.runtime import ModelProtocol

RESERVED_PROTOCOL = ModelProtocol.ANTHROPIC_MESSAGES
