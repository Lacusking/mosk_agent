"""模型生命周期的 durable runtime event 契约。"""

from datetime import datetime
from enum import StrEnum
from typing import cast

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from src.contracts.runtime.models import ModelProtocol
from src.contracts.runtime.models import ModelResponseStatus
from src.contracts.runtime.models import ModelStopReason
from src.contracts.runtime.models import ModelUsage


class _EventSchema(PydanticBaseModel):
    """Runtime event 契约的共同校验配置。"""

    model_config = ConfigDict(extra="forbid")


class RuntimeEventType(StrEnum):
    """可持久化的模型生命周期事件类型。"""

    MODEL_INVOCATION_STARTED = "model_invocation_started"
    MODEL_INVOCATION_COMPLETED = "model_invocation_completed"
    MODEL_INVOCATION_FAILED = "model_invocation_failed"
    MODEL_TOOL_CALLS_PRODUCED = "model_tool_calls_produced"


class RuntimeActorType(StrEnum):
    """触发 runtime event 的标准 actor 类型。"""

    RUNTIME = "runtime"
    SYSTEM = "system"
    USER = "user"


class ModelInvocationStartedPayload(_EventSchema):
    """模型调用已开始的安全事实 payload。"""

    invocation_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    protocol: ModelProtocol
    profile: str = Field(min_length=1)
    streaming: bool


_VALID_COMPLETION_REASONS: dict[ModelResponseStatus, frozenset[ModelStopReason]] = {
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


class ModelInvocationCompletedPayload(_EventSchema):
    """模型调用已形成可消费响应的安全事实 payload。"""

    invocation_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    protocol: ModelProtocol
    status: ModelResponseStatus
    stop_reason: ModelStopReason
    provider_stop_reason: str | None = None
    usage: ModelUsage
    latency_ms: float = Field(ge=0)
    tool_call_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_completion_semantics(self) -> "ModelInvocationCompletedPayload":
        """校验完成事实与统一模型响应语义一致。

        Returns:
            已校验的模型调用完成 payload。

        Raises:
            ValueError: 状态、停止原因或工具意图数量不一致。
        """
        if self.stop_reason not in _VALID_COMPLETION_REASONS[self.status]:
            raise ValueError("status 与 stop_reason 组合非法")
        if self.stop_reason == ModelStopReason.TOOL_USE and self.tool_call_count == 0:
            raise ValueError("tool_use 完成事件必须包含工具调用数量")
        if self.tool_call_count > 0 and self.stop_reason != ModelStopReason.TOOL_USE:
            raise ValueError("包含工具调用的完成事件必须使用 tool_use 停止原因")
        return self


class ModelInvocationFailedPayload(_EventSchema):
    """模型调用失败的安全决策事实 payload。"""

    invocation_id: str = Field(min_length=1)
    provider: str | None = None
    model: str | None = None
    protocol: ModelProtocol | None = None
    error_type: str = Field(min_length=1)
    retryable: bool
    fallback_allowed: bool
    provider_error_code: str | None = None
    provider_status_code: int | None = None
    latency_ms: float = Field(ge=0)


class ProducedToolCallFact(_EventSchema):
    """不含工具参数的已产生工具调用事实。"""

    call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments_validated: bool


class ModelToolCallsProducedPayload(_EventSchema):
    """模型已产生工具调用意图的安全事实 payload。"""

    invocation_id: str = Field(min_length=1)
    calls: list[ProducedToolCallFact] = Field(min_length=1)


type RuntimeEventPayload = (
    ModelInvocationStartedPayload
    | ModelInvocationCompletedPayload
    | ModelInvocationFailedPayload
    | ModelToolCallsProducedPayload
)

_PAYLOAD_BY_EVENT_TYPE: dict[RuntimeEventType, type[_EventSchema]] = {
    RuntimeEventType.MODEL_INVOCATION_STARTED: ModelInvocationStartedPayload,
    RuntimeEventType.MODEL_INVOCATION_COMPLETED: ModelInvocationCompletedPayload,
    RuntimeEventType.MODEL_INVOCATION_FAILED: ModelInvocationFailedPayload,
    RuntimeEventType.MODEL_TOOL_CALLS_PRODUCED: ModelToolCallsProducedPayload,
}


class RuntimeEvent(_EventSchema):
    """后续 runtime 与事件设施可消费的事实事件 envelope。"""

    event_id: str = Field(min_length=1)
    event_type: RuntimeEventType
    event_version: int = Field(default=1, ge=1)
    agent_run_id: str | None = None
    step_id: str | None = None
    session_id: str | None = None
    trace_id: str = Field(min_length=1)
    span_id: str = Field(min_length=1)
    parent_span_id: str | None = None
    actor_type: RuntimeActorType
    actor_id: str | None = None
    payload: RuntimeEventPayload
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def validate_created_at_has_timezone(cls, value: datetime) -> datetime:
        """要求事件时间明确携带时区。

        Args:
            value: 待校验的事件发生时间。

        Returns:
            具备时区信息的事件发生时间。

        Raises:
            ValueError: 时间不包含时区偏移信息。
        """
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at 必须包含时区信息")
        return value

    @model_validator(mode="after")
    def validate_typed_payload(self) -> "RuntimeEvent":
        """确保生命周期事件类型只携带相应 payload。

        Returns:
            已校验的 runtime event。

        Raises:
            ValueError: 事件类型与 payload 类型不匹配。
        """
        expected_type = _PAYLOAD_BY_EVENT_TYPE[self.event_type]
        if not isinstance(self.payload, expected_type):
            raise ValueError("event_type 与 payload 类型不匹配")
        self.payload = cast(RuntimeEventPayload, self.payload)
        return self


__all__ = [
    "ModelInvocationCompletedPayload",
    "ModelInvocationFailedPayload",
    "ModelInvocationStartedPayload",
    "ModelToolCallsProducedPayload",
    "ProducedToolCallFact",
    "RuntimeActorType",
    "RuntimeEvent",
    "RuntimeEventType",
]
