"""模型调用、响应、usage 与流事件的公开契约。"""

from enum import StrEnum
from typing import cast

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from src.contracts.runtime.messages import JsonValue
from src.contracts.runtime.messages import ModelContentBlock
from src.contracts.runtime.messages import ModelMessage


class _ModelSchema(PydanticBaseModel):
    """模型契约的共同校验配置。"""

    model_config = ConfigDict(extra="forbid")


class ModelProtocol(StrEnum):
    """模型 wire protocol 身份。"""

    OPENAI_CHAT = "openai_chat"
    OPENAI_RESPONSES = "openai_responses"
    ANTHROPIC_MESSAGES = "anthropic_messages"
    CUSTOM = "custom"
    MOCK = "mock"


class ModelResponseStatus(StrEnum):
    """可消费模型响应的整体状态。"""

    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    REFUSED = "refused"


class ModelStopReason(StrEnum):
    """模型停止生成或交还控制权的标准原因。"""

    COMPLETED = "completed"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    CONTENT_FILTERED = "content_filtered"
    REFUSED = "refused"
    UNKNOWN = "unknown"


class ModelCapabilities(_ModelSchema):
    """模型 profile 可声明的标准能力。"""

    tool_calling: bool = False
    streaming: bool = False
    structured_output: bool = False
    vision: bool = False
    reasoning: bool = False


class ModelToolDeclaration(_ModelSchema):
    """允许模型提出调用意图的工具声明。"""

    name: str = Field(min_length=1)
    description: str | None = None
    parameters_schema: dict[str, JsonValue] = Field(default_factory=dict)
    strict: bool = False


class ModelToolCall(_ModelSchema):
    """模型完成并可由后续 runtime 处理的工具调用意图。"""

    call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    provider_call_id: str | None = None


class ModelToolChoiceMode(StrEnum):
    """工具选择控制模式。"""

    AUTO = "auto"
    NONE = "none"
    REQUIRED = "required"
    NAMED = "named"


class ModelToolChoice(_ModelSchema):
    """单次请求对工具选择的控制要求。"""

    mode: ModelToolChoiceMode = ModelToolChoiceMode.AUTO
    name: str | None = None

    @model_validator(mode="after")
    def validate_named_tool(self) -> "ModelToolChoice":
        """确保仅 named 模式携带工具名称。

        Returns:
            已校验的工具选择配置。

        Raises:
            ValueError: 工具名称与选择模式不匹配。
        """
        if self.mode == ModelToolChoiceMode.NAMED and not self.name:
            raise ValueError("named 工具选择必须提供 name")
        if self.mode != ModelToolChoiceMode.NAMED and self.name is not None:
            raise ValueError("仅 named 工具选择可提供 name")
        return self


class ModelResponseFormatType(StrEnum):
    """模型输出格式要求。"""

    TEXT = "text"
    JSON_OBJECT = "json_object"
    JSON_SCHEMA = "json_schema"


class ModelResponseFormat(_ModelSchema):
    """结构化输出要求。"""

    type: ModelResponseFormatType = ModelResponseFormatType.TEXT
    json_schema: dict[str, JsonValue] | None = None

    @model_validator(mode="after")
    def validate_json_schema(self) -> "ModelResponseFormat":
        """确保 JSON schema 只在对应模式中提供。

        Returns:
            已校验的输出格式要求。

        Raises:
            ValueError: 输出格式与 JSON schema 不匹配。
        """
        if self.type == ModelResponseFormatType.JSON_SCHEMA and self.json_schema is None:
            raise ValueError("json_schema 输出格式必须提供 json_schema")
        if self.type != ModelResponseFormatType.JSON_SCHEMA and self.json_schema is not None:
            raise ValueError("仅 json_schema 输出格式可提供 json_schema")
        return self


class ModelOptions(_ModelSchema):
    """影响生成语义而非 transport 执行的请求选项。"""

    temperature: float | None = Field(default=None, ge=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    top_p: float | None = Field(default=None, ge=0, le=1)
    stop_sequences: list[str] | None = None
    parallel_tool_calls: bool | None = None
    provider_options: dict[str, JsonValue] = Field(default_factory=dict)


class ModelRequest(_ModelSchema):
    """单次标准化模型调用请求。"""

    invocation_id: str = Field(min_length=1)
    provider: str | None = None
    model: str = Field(min_length=1)
    protocol: ModelProtocol | None = None
    messages: list[ModelMessage] = Field(min_length=1)
    tools: list[ModelToolDeclaration] = Field(default_factory=list)
    tool_choice: ModelToolChoice | None = None
    response_format: ModelResponseFormat | None = None
    options: ModelOptions = Field(default_factory=ModelOptions)
    stream: bool = False
    timeout_seconds: float | None = Field(default=None, gt=0)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_tools(self) -> "ModelRequest":
        """验证工具声明和选择可在 provider 调用前解析。

        Returns:
            已校验的模型请求。

        Raises:
            ValueError: 工具声明重复或选择了不存在的工具。
        """
        tool_names = [tool.name for tool in self.tools]
        if len(tool_names) != len(set(tool_names)):
            raise ValueError("工具声明名称不能重复")
        if self.tool_choice is None:
            return self
        if self.tool_choice.mode == ModelToolChoiceMode.REQUIRED and not self.tools:
            raise ValueError("required 工具选择必须声明 tools")
        if (
            self.tool_choice.mode == ModelToolChoiceMode.NAMED
            and self.tool_choice.name not in tool_names
        ):
            raise ValueError("named 工具选择必须引用已声明工具")
        return self


class ModelUsage(_ModelSchema):
    """单次调用由 provider 报告的 token 使用量。"""

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    cache_creation_input_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)
    provider_details: dict[str, JsonValue] = Field(default_factory=dict)


_VALID_RESPONSE_REASONS: dict[ModelResponseStatus, frozenset[ModelStopReason]] = {
    ModelResponseStatus.COMPLETED: frozenset(
        {ModelStopReason.COMPLETED, ModelStopReason.TOOL_USE}
    ),
    ModelResponseStatus.INCOMPLETE: frozenset(
        {
            ModelStopReason.MAX_TOKENS,
            ModelStopReason.CONTENT_FILTERED,
            ModelStopReason.UNKNOWN,
        }
    ),
    ModelResponseStatus.REFUSED: frozenset({ModelStopReason.REFUSED}),
}


class ModelResponse(_ModelSchema):
    """协议 adapter 输出的可消费模型最终响应。"""

    invocation_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    protocol: ModelProtocol
    content: list[ModelContentBlock] = Field(default_factory=list)
    tool_calls: list[ModelToolCall] = Field(default_factory=list)
    status: ModelResponseStatus
    stop_reason: ModelStopReason
    provider_stop_reason: str | None = None
    usage: ModelUsage | None = None

    @model_validator(mode="after")
    def validate_status_and_stop_reason(self) -> "ModelResponse":
        """拒绝不一致的响应状态、停止原因与工具意图。

        Returns:
            已校验的最终响应。

        Raises:
            ValueError: 状态映射或工具调用意图不一致。
        """
        if self.stop_reason not in _VALID_RESPONSE_REASONS[self.status]:
            raise ValueError("status 与 stop_reason 组合非法")
        if self.stop_reason == ModelStopReason.TOOL_USE and not self.tool_calls:
            raise ValueError("tool_use 响应必须包含已完成工具调用")
        if self.tool_calls and self.stop_reason != ModelStopReason.TOOL_USE:
            raise ValueError("包含工具调用的响应必须使用 tool_use 停止原因")
        return self


class ModelStreamEventType(StrEnum):
    """统一模型流事件类型。"""

    INVOCATION_STARTED = "invocation_started"
    CONTENT_DELTA = "content_delta"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_DELTA = "tool_call_delta"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    USAGE_UPDATED = "usage_updated"
    RESPONSE_COMPLETED = "response_completed"
    RESPONSE_FAILED = "response_failed"


class InvocationStartedPayload(_ModelSchema):
    """流式调用开始 payload。"""

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    protocol: ModelProtocol


class ContentDeltaPayload(_ModelSchema):
    """文本流增量 payload。"""

    delta: str = Field(min_length=1)


class ToolCallStartedPayload(_ModelSchema):
    """工具调用增量开始 payload。"""

    call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    provider_call_id: str | None = None


class ToolCallDeltaPayload(_ModelSchema):
    """尚不可执行的工具参数字符串增量 payload。"""

    call_id: str = Field(min_length=1)
    arguments_delta: str = Field(min_length=1)


class ToolCallCompletedPayload(_ModelSchema):
    """已完成并验证的工具调用 payload。"""

    tool_call: ModelToolCall


class UsageUpdatedPayload(_ModelSchema):
    """调用 usage 更新 payload。"""

    usage: ModelUsage


class ResponseCompletedPayload(_ModelSchema):
    """模型流最终响应边界 payload。"""

    status: ModelResponseStatus
    stop_reason: ModelStopReason
    provider_stop_reason: str | None = None
    usage: ModelUsage | None = None

    @model_validator(mode="after")
    def validate_status_and_stop_reason(self) -> "ResponseCompletedPayload":
        """校验最终流状态与停止原因映射。

        Returns:
            已校验的完成 payload。

        Raises:
            ValueError: 状态与停止原因组合非法。
        """
        if self.stop_reason not in _VALID_RESPONSE_REASONS[self.status]:
            raise ValueError("status 与 stop_reason 组合非法")
        return self


class ResponseFailedPayload(_ModelSchema):
    """模型流标准化失败 payload。"""

    error_type: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool
    fallback_allowed: bool
    provider_error_code: str | None = None
    provider_status_code: int | None = None


type ModelStreamPayload = (
    InvocationStartedPayload
    | ContentDeltaPayload
    | ToolCallStartedPayload
    | ToolCallDeltaPayload
    | ToolCallCompletedPayload
    | UsageUpdatedPayload
    | ResponseCompletedPayload
    | ResponseFailedPayload
)

_PAYLOAD_BY_EVENT_TYPE: dict[ModelStreamEventType, type[_ModelSchema]] = {
    ModelStreamEventType.INVOCATION_STARTED: InvocationStartedPayload,
    ModelStreamEventType.CONTENT_DELTA: ContentDeltaPayload,
    ModelStreamEventType.TOOL_CALL_STARTED: ToolCallStartedPayload,
    ModelStreamEventType.TOOL_CALL_DELTA: ToolCallDeltaPayload,
    ModelStreamEventType.TOOL_CALL_COMPLETED: ToolCallCompletedPayload,
    ModelStreamEventType.USAGE_UPDATED: UsageUpdatedPayload,
    ModelStreamEventType.RESPONSE_COMPLETED: ResponseCompletedPayload,
    ModelStreamEventType.RESPONSE_FAILED: ResponseFailedPayload,
}


class ModelStreamEvent(_ModelSchema):
    """协议 adapter 向 reducer 输出的类型化流事件。"""

    invocation_id: str = Field(min_length=1)
    event_type: ModelStreamEventType
    sequence: int = Field(ge=0)
    payload: ModelStreamPayload

    @model_validator(mode="after")
    def validate_typed_payload(self) -> "ModelStreamEvent":
        """确保流事件类型只携带其对应 payload。

        Returns:
            已校验的模型流事件。

        Raises:
            ValueError: 事件类型与 payload 类型不匹配。
        """
        expected_type = _PAYLOAD_BY_EVENT_TYPE[self.event_type]
        if not isinstance(self.payload, expected_type):
            raise ValueError("event_type 与 payload 类型不匹配")
        self.payload = cast(ModelStreamPayload, self.payload)
        return self


__all__ = [
    "ContentDeltaPayload",
    "InvocationStartedPayload",
    "ModelCapabilities",
    "ModelOptions",
    "ModelProtocol",
    "ModelRequest",
    "ModelResponse",
    "ModelResponseFormat",
    "ModelResponseFormatType",
    "ModelResponseStatus",
    "ModelStopReason",
    "ModelStreamEvent",
    "ModelStreamEventType",
    "ModelToolCall",
    "ModelToolChoice",
    "ModelToolChoiceMode",
    "ModelToolDeclaration",
    "ModelUsage",
    "ResponseCompletedPayload",
    "ResponseFailedPayload",
    "ToolCallCompletedPayload",
    "ToolCallDeltaPayload",
    "ToolCallStartedPayload",
    "UsageUpdatedPayload",
]
