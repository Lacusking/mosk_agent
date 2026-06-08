"""上下文装配错误。"""

from src.exceptions import ValidationError


class ContextError(ValidationError):
    """上下文装配或裁剪失败。"""


class ContextConversionError(ContextError):
    """上下文 item 无法转换为模型消息。"""


class ContextStrategyError(ContextError):
    """上下文策略执行失败。"""


class ContextBudgetError(ContextError):
    """上下文无法满足 token 预算。"""


__all__ = ["ContextBudgetError", "ContextConversionError", "ContextError", "ContextStrategyError"]
