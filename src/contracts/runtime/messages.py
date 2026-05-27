"""模型消息与内容块的公开契约。"""

from enum import StrEnum
from typing import Annotated
from typing import Literal

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic import Field

type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | dict[str, JsonValue]


class _MessageSchema(PydanticBaseModel):
    """模型消息契约的共同校验配置。"""

    model_config = ConfigDict(extra="forbid")


class ModelRole(StrEnum):
    """模型交互中的标准消息角色。"""

    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class TextContentBlock(_MessageSchema):
    """文本内容块。"""

    kind: Literal["text"] = "text"
    text: str = Field(min_length=1)


class ImageContentBlock(_MessageSchema):
    """图片引用内容块。"""

    kind: Literal["image"] = "image"
    url: str = Field(min_length=1)
    media_type: str | None = None
    detail: str | None = None


class ToolCallContentBlock(_MessageSchema):
    """助手返回的工具调用意图内容块。"""

    kind: Literal["tool_call"] = "tool_call"
    call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    provider_call_id: str | None = None


class ToolResultContentBlock(_MessageSchema):
    """已执行工具结果内容块。"""

    kind: Literal["tool_result"] = "tool_result"
    call_id: str = Field(min_length=1)
    output: JsonValue
    is_error: bool = False


class RefusalContentBlock(_MessageSchema):
    """模型受控拒绝内容块。"""

    kind: Literal["refusal"] = "refusal"
    refusal: str = Field(min_length=1)


class CustomContentBlock(_MessageSchema):
    """受控协议扩展内容块。"""

    kind: Literal["custom"] = "custom"
    namespace: str = Field(min_length=1)
    data: dict[str, JsonValue] = Field(default_factory=dict)


type ModelContentBlock = Annotated[
    TextContentBlock
    | ImageContentBlock
    | ToolCallContentBlock
    | ToolResultContentBlock
    | RefusalContentBlock
    | CustomContentBlock,
    Field(discriminator="kind"),
]


class ModelMessage(_MessageSchema):
    """可供协议 adapter 转换的标准模型消息。"""

    role: ModelRole
    content: list[ModelContentBlock] = Field(min_length=1)


__all__ = [
    "CustomContentBlock",
    "ImageContentBlock",
    "JsonValue",
    "ModelContentBlock",
    "ModelMessage",
    "ModelRole",
    "RefusalContentBlock",
    "TextContentBlock",
    "ToolCallContentBlock",
    "ToolResultContentBlock",
]
