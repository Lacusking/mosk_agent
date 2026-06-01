"""Session 与可见消息历史的跨模块契约。"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from src.contracts.runtime import JsonValue
from src.contracts.runtime import ModelContentBlock
from src.contracts.runtime import ModelRole


class _SessionSchema(PydanticBaseModel):
    """Session 契约的共同校验配置。"""

    model_config = ConfigDict(extra="forbid")


class SessionStatus(StrEnum):
    """Session 生命周期状态。"""

    ACTIVE = "active"
    ARCHIVED = "archived"


class SessionMessageRole(StrEnum):
    """会话可见历史允许保存的消息角色。"""

    USER = "user"
    ASSISTANT = "assistant"


class Session(_SessionSchema):
    """可持久化会话的公开数据形态。"""

    session_id: str = Field(min_length=1)
    status: SessionStatus = SessionStatus.ACTIVE
    title: str | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    last_message_sequence: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class SessionMessage(_SessionSchema):
    """会话内按序保存的用户可见消息。"""

    message_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    agent_run_id: str | None = None
    sequence: int = Field(ge=1)
    role: SessionMessageRole
    content: list[ModelContentBlock] = Field(min_length=1)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CreateSessionRequest(_SessionSchema):
    """创建 Session 的 API 请求。"""

    title: str | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class SessionResponse(_SessionSchema):
    """Session 普通 API 响应数据。"""

    session: Session


class SessionMessagesResponse(_SessionSchema):
    """会话历史查询响应数据。"""

    session_id: str = Field(min_length=1)
    messages: list[SessionMessage] = Field(default_factory=list)

    @field_validator("messages")
    @classmethod
    def validate_message_order(cls, value: list[SessionMessage]) -> list[SessionMessage]:
        """要求响应中的消息按 sequence 升序排列。

        Args:
            value: 待返回的会话消息列表。

        Returns:
            已校验的消息列表。

        Raises:
            ValueError: 消息顺序不是按 sequence 升序排列。
        """
        sequences = [message.sequence for message in value]
        if sequences != sorted(sequences):
            raise ValueError("messages 必须按 sequence 升序排列")
        return value


def session_role_to_model_role(role: SessionMessageRole) -> ModelRole:
    """转换会话可见角色为模型消息角色。

    Args:
        role: 会话消息角色。

    Returns:
        对应的模型消息角色。
    """
    return ModelRole(role.value)


__all__ = [
    "CreateSessionRequest",
    "Session",
    "SessionMessage",
    "SessionMessageRole",
    "SessionMessagesResponse",
    "SessionResponse",
    "SessionStatus",
    "session_role_to_model_role",
]
