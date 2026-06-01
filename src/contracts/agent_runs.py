"""AgentRun 生命周期、步骤与运行级流输出契约。"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from typing import Literal
from typing import cast

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from src.contracts.runtime import JsonValue


class _AgentRunSchema(PydanticBaseModel):
    """AgentRun 契约的共同校验配置。"""

    model_config = ConfigDict(extra="forbid")


class AgentMode(StrEnum):
    """用户请求的 Agent 行为模式。"""

    CHAT = "chat"
    PLAN = "plan"
    BUILD = "build"
    REVIEW = "review"


class AgentRunStatus(StrEnum):
    """AgentRun 顶层生命周期状态。"""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRunFinishReason(StrEnum):
    """AgentRun 终止原因。"""

    COMPLETED = "completed"
    REFUSED = "refused"
    INCOMPLETE = "incomplete"
    ERROR = "error"
    CANCELLED = "cancelled"
    MAX_STEPS = "max_steps"
    TIMEOUT = "timeout"


class AgentRunStepKind(StrEnum):
    """AgentRun 内部 step 类型。"""

    MODEL = "model"
    TOOL = "tool"
    TRANSITION = "transition"
    COMPLETE = "complete"
    FAIL = "fail"


class AgentRunStepStatus(StrEnum):
    """AgentRunStep 生命周期状态。"""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRun(_AgentRunSchema):
    """一次 Agent 执行的公开状态快照。"""

    agent_run_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    input_message_id: str = Field(min_length=1)
    status: AgentRunStatus
    mode: AgentMode
    requested_pattern: str | None = None
    active_pattern: str = Field(min_length=1)
    context_message_sequence: int = Field(ge=1)
    trace_id: str = Field(min_length=1)
    finish_reason: AgentRunFinishReason | None = None
    error_type: str | None = None
    max_steps: int = Field(gt=0)
    timeout_seconds: float = Field(gt=0)
    retry_limit: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_terminal_fields(self) -> "AgentRun":
        """校验终态字段与状态一致。

        Returns:
            已校验的 AgentRun。

        Raises:
            ValueError: 终态缺少 finish_reason，或非失败状态携带 error_type。
        """
        if self.status in {
            AgentRunStatus.COMPLETED,
            AgentRunStatus.FAILED,
            AgentRunStatus.CANCELLED,
        }:
            if self.finish_reason is None:
                raise ValueError("终态 AgentRun 必须包含 finish_reason")
        if self.status != AgentRunStatus.FAILED and self.error_type is not None:
            raise ValueError("仅 failed AgentRun 可包含 error_type")
        return self


class AgentRunStep(_AgentRunSchema):
    """AgentRun 内部可审计 step 快照。"""

    step_id: str = Field(min_length=1)
    agent_run_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    kind: AgentRunStepKind
    status: AgentRunStepStatus
    pattern: str = Field(min_length=1)
    invocation_id: str | None = None
    safe_input: dict[str, JsonValue] = Field(default_factory=dict)
    safe_output: dict[str, JsonValue] = Field(default_factory=dict)
    error_type: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class CreateAgentRunRequest(_AgentRunSchema):
    """创建并执行 AgentRun 的 API 请求。"""

    session_id: str = Field(min_length=1)
    input: str = Field(min_length=1)
    mode: AgentMode = AgentMode.CHAT
    requested_pattern: str | None = None
    stream: bool = False


class AgentRunResponse(_AgentRunSchema):
    """AgentRun 普通 API 响应数据。"""

    agent_run: AgentRun


class AgentRunEventsResponse(_AgentRunSchema):
    """AgentRun 事实事件查询响应数据。"""

    agent_run_id: str = Field(min_length=1)
    events: list[dict[str, JsonValue]] = Field(default_factory=list)


class RunStartedStreamPayload(_AgentRunSchema):
    """AgentRun SSE 开始事件 payload。"""

    agent_run_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    mode: AgentMode
    pattern: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)


class OutputTextDeltaStreamPayload(_AgentRunSchema):
    """AgentRun SSE 文本增量 payload。"""

    agent_run_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    delta: str = Field(min_length=1)


class RunTerminalStreamPayload(_AgentRunSchema):
    """AgentRun SSE 终态事件 payload。"""

    agent_run_id: str = Field(min_length=1)
    status: Literal["completed", "failed", "cancelled"]
    finish_reason: AgentRunFinishReason | None = None
    error_type: str | None = None

    @model_validator(mode="after")
    def validate_terminal_payload(self) -> "RunTerminalStreamPayload":
        """校验终态 SSE payload。

        Returns:
            已校验的终态 payload。

        Raises:
            ValueError: 失败事件缺少 error_type 或成功事件携带 error_type。
        """
        if self.status == "failed" and not self.error_type:
            raise ValueError("run.failed 必须包含 error_type")
        if self.status != "failed" and self.error_type is not None:
            raise ValueError("仅 run.failed 可包含 error_type")
        return self


type AgentRunStreamPayload = Annotated[
    RunStartedStreamPayload | OutputTextDeltaStreamPayload | RunTerminalStreamPayload,
    Field(discriminator=None),
]


class AgentRunStreamEvent(_AgentRunSchema):
    """面向客户端的 AgentRun SSE 事件。"""

    event: Literal[
        "run.started",
        "output.text.delta",
        "run.completed",
        "run.failed",
        "run.cancelled",
    ]
    payload: AgentRunStreamPayload

    @model_validator(mode="after")
    def validate_payload_type(self) -> "AgentRunStreamEvent":
        """确保 SSE event 名称与 payload 类型匹配。

        Returns:
            已校验的 SSE 事件。

        Raises:
            ValueError: event 与 payload 类型或终态状态不匹配。
        """
        if self.event == "run.started" and not isinstance(self.payload, RunStartedStreamPayload):
            raise ValueError("run.started payload 类型不匹配")
        if self.event == "output.text.delta" and not isinstance(
            self.payload, OutputTextDeltaStreamPayload
        ):
            raise ValueError("output.text.delta payload 类型不匹配")
        if self.event.startswith("run.") and self.event != "run.started":
            if not isinstance(self.payload, RunTerminalStreamPayload):
                raise ValueError("run terminal payload 类型不匹配")
            expected = self.event.removeprefix("run.")
            if self.payload.status != expected:
                raise ValueError("run terminal event 与 status 不匹配")
        self.payload = cast(AgentRunStreamPayload, self.payload)
        return self


__all__ = [
    "AgentMode",
    "AgentRun",
    "AgentRunEventsResponse",
    "AgentRunFinishReason",
    "AgentRunResponse",
    "AgentRunStatus",
    "AgentRunStep",
    "AgentRunStepKind",
    "AgentRunStepStatus",
    "AgentRunStreamEvent",
    "AgentRunStreamPayload",
    "CreateAgentRunRequest",
    "OutputTextDeltaStreamPayload",
    "RunStartedStreamPayload",
    "RunTerminalStreamPayload",
]
