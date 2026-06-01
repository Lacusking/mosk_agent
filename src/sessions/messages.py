"""SessionMessage 与 ModelMessage 的转换工具。"""

from collections.abc import Sequence

from src.contracts.runtime import ModelContentBlock
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import TextContentBlock
from src.contracts.sessions import SessionMessage
from src.contracts.sessions import SessionMessageRole
from src.contracts.sessions import session_role_to_model_role


def text_content(text: str) -> list[ModelContentBlock]:
    """构造单文本内容块列表。

    Args:
        text: 文本内容。

    Returns:
        仅包含一个 TextContentBlock 的内容块列表。
    """
    return [TextContentBlock(text=text)]


def to_model_message(message: SessionMessage) -> ModelMessage:
    """将会话可见消息转换为模型输入消息。

    Args:
        message: 会话消息。

    Returns:
        可交给 ModelAdapter 的 ModelMessage。
    """
    return ModelMessage(
        role=session_role_to_model_role(message.role),
        content=message.content,
    )


def to_model_messages(messages: Sequence[SessionMessage]) -> list[ModelMessage]:
    """批量转换会话可见消息。

    Args:
        messages: 按 sequence 排列的会话消息。

    Returns:
        对应的模型消息列表。
    """
    return [to_model_message(message) for message in messages]


def user_text_content(text: str) -> tuple[SessionMessageRole, list[ModelContentBlock]]:
    """构造用户文本消息角色与内容。

    Args:
        text: 用户输入文本。

    Returns:
        用户角色与文本内容块。
    """
    return SessionMessageRole.USER, text_content(text)


def assistant_text_content(text: str) -> tuple[SessionMessageRole, list[ModelContentBlock]]:
    """构造 assistant 文本消息角色与内容。

    Args:
        text: assistant 输出文本。

    Returns:
        assistant 角色与文本内容块。
    """
    return SessionMessageRole.ASSISTANT, text_content(text)


__all__ = [
    "assistant_text_content",
    "text_content",
    "to_model_message",
    "to_model_messages",
    "user_text_content",
]
