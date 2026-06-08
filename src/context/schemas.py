"""上下文装配结构。"""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from src.context.errors import ContextConversionError
from src.contracts.runtime import JsonValue
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import ModelRole
from src.contracts.runtime import TextContentBlock
from src.contracts.runtime import ToolResultContentBlock

_SENSITIVE_METADATA_KEYS = frozenset(
    {
        "authorization",
        "api_key",
        "apikey",
        "password",
        "raw_provider_request",
        "raw_request",
        "secret",
        "token",
    }
)


class _ContextSchema(BaseModel):
    """上下文 schema 共同配置。"""

    model_config = ConfigDict(extra="forbid")


class ContextSource(StrEnum):
    """上下文来源。"""

    SESSION = "session"
    MEMORY = "memory"
    TOOL = "tool"
    ARTIFACT = "artifact"
    RAG = "rag"
    SYSTEM = "system"


class ContextItemType(StrEnum):
    """上下文 item 类型。"""

    MESSAGE = "message"
    SUMMARY = "summary"
    OBSERVATION = "observation"
    ARTIFACT = "artifact"
    CHUNK = "chunk"


class ContextBudget(_ContextSchema):
    """上下文预算快照。"""

    max_messages: int | None = Field(default=None, gt=0)
    snip_threshold_messages: int | None = Field(default=None, gt=0)
    snip_head_messages: int = Field(default=0, ge=0)
    snip_tail_messages: int = Field(default=0, ge=0)
    max_tokens: int | None = Field(default=None, gt=0)
    token_reserve: int = Field(default=0, ge=0)
    used_tokens: int = Field(default=0, ge=0)
    tool_result_budget_tokens: int | None = Field(default=None, gt=0)
    micro_item_max_tokens: int | None = Field(default=None, gt=0)


type ContextContent = Annotated[ModelMessage | dict[str, JsonValue], Field(discriminator=None)]


class ContextItem(_ContextSchema):
    """可参与上下文装配和裁剪的单段上下文。"""

    source: ContextSource
    type: ContextItemType
    content: ContextContent
    priority: int = Field(default=0)
    token_count: int | None = Field(default=None, ge=0)
    pinned: bool = False
    evictable: bool = True
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_item(self) -> "ContextItem":
        """校验 item 来源、内容和安全元数据。

        Returns:
            已校验的 ContextItem。

        Raises:
            ValueError: source/type/content 不匹配或 metadata 含敏感键。
        """
        if self.source == ContextSource.SESSION:
            if self.type != ContextItemType.MESSAGE:
                raise ValueError("session context item 必须是 message 类型")
            if not isinstance(self.content, ModelMessage):
                raise ValueError("session context item content 必须是 ModelMessage")
            sequence = self.metadata.get("sequence")
            if not isinstance(sequence, int):
                raise ValueError("session context item 必须记录 message sequence")
        _ensure_safe_metadata(self.metadata)
        return self

    @property
    def sequence(self) -> int | None:
        """返回 session message sequence。

        Returns:
            存在时返回 sequence，否则返回 None。
        """
        value = self.metadata.get("sequence")
        return value if isinstance(value, int) else None


class ContextBundle(_ContextSchema):
    """一次 AgentRun 的结构化上下文包。"""

    agent_run_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    session_messages: list[ContextItem] = Field(default_factory=list)
    memory_summary: ContextItem | None = None
    tool_observations: list[ContextItem] = Field(default_factory=list)
    artifacts: list[ContextItem] = Field(default_factory=list)
    evicted_items: list[ContextItem] = Field(default_factory=list)
    budget: ContextBudget | None = None
    diagnostics: dict[str, JsonValue] = Field(default_factory=dict)

    def to_model_messages(self) -> list[ModelMessage]:
        """提取可交给 pattern/model 的模型消息视图。

        Returns:
            按 session sequence 升序排列的 ModelMessage 列表。

        Raises:
            ContextConversionError: 必需 item 无法转换为 ModelMessage。
        """
        sorted_items = sorted(
            self.session_messages,
            key=lambda item: item.sequence if item.sequence is not None else 0,
        )
        messages: list[ModelMessage] = []
        if self.memory_summary is not None:
            messages.append(_summary_to_message(self.memory_summary))
        for item in sorted_items:
            if not isinstance(item.content, ModelMessage):
                raise ContextConversionError(msg="ContextItem 无法转换为 ModelMessage")
            messages.append(item.content)
        for item in sorted(
            self.tool_observations,
            key=lambda value: int(value.metadata.get("order", 0)),
        ):
            messages.append(_tool_observation_to_message(item))
        return messages


def _summary_to_message(item: ContextItem) -> ModelMessage:
    content = item.content
    if isinstance(content, ModelMessage):
        return content
    text = content.get("summary") or content.get("text")
    if not isinstance(text, str) or not text:
        raise ContextConversionError(msg="summary ContextItem 无法转换为 ModelMessage")
    return ModelMessage(role=ModelRole.SYSTEM, content=[TextContentBlock(text=text)])


def _tool_observation_to_message(item: ContextItem) -> ModelMessage:
    content = item.content
    if isinstance(content, ModelMessage):
        return content
    call_id = content.get("call_id")
    observation = content.get("observation")
    is_error = bool(content.get("is_error", False))
    if not isinstance(call_id, str) or "observation" not in content:
        raise ContextConversionError(msg="tool observation ContextItem 无法转换为 ModelMessage")
    return ModelMessage(
        role=ModelRole.TOOL,
        content=[
            ToolResultContentBlock(
                call_id=call_id,
                output=observation,
                is_error=is_error,
            )
        ],
    )


def _ensure_safe_metadata(metadata: dict[str, JsonValue]) -> None:
    for key in metadata:
        normalized = key.lower()
        if normalized in _SENSITIVE_METADATA_KEYS:
            raise ValueError("ContextItem metadata 包含敏感字段")


__all__ = [
    "ContextBudget",
    "ContextBundle",
    "ContextContent",
    "ContextItem",
    "ContextItemType",
    "ContextSource",
]
