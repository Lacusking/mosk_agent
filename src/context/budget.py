"""上下文预算工具。"""

from src.contracts.runtime import ModelMessage
from src.contracts.runtime import TextContentBlock


def estimate_message_tokens(message: ModelMessage) -> int:
    """估算单条模型消息 token 数。

    Args:
        message: 模型消息。

    Returns:
        粗略 token 估算值；首期仅用于排序/诊断，不作为精确预算。
    """
    text_length = sum(
        len(block.text) for block in message.content if isinstance(block, TextContentBlock)
    )
    return max(1, text_length // 4)


__all__ = ["estimate_message_tokens"]
