"""Agent pattern 动作契约。"""

from enum import StrEnum
from typing import Annotated
from typing import Literal

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic import Field

from src.contracts.agent_runs import AgentRun
from src.contracts.runtime import JsonValue
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import ModelOptions
from src.contracts.runtime import ModelToolCall
from src.contracts.runtime import ModelToolDeclaration
from src.contracts.tools import ToolActionRequest


class _PatternSchema(PydanticBaseModel):
    """Pattern 契约共同校验配置。"""

    model_config = ConfigDict(extra="forbid")


class OutputVisibility(StrEnum):
    """模型动作输出可见性。"""

    INTERNAL = "internal"
    PUBLIC_OUTPUT = "public_output"


class PatternObservation(_PatternSchema):
    """Runtime 执行动作后的受控观察。"""

    kind: str = Field(min_length=1)
    data: dict[str, JsonValue] = Field(default_factory=dict)


class PatternRuntimeState(_PatternSchema):
    """传给 pattern 的运行时状态快照。"""

    agent_run: AgentRun
    visible_context_messages: list[ModelMessage] = Field(default_factory=list)
    observations: list[PatternObservation] = Field(default_factory=list)
    step_count: int = Field(ge=0)
    available_tools: list[ModelToolDeclaration] = Field(default_factory=list)


class InvokeModelAction(_PatternSchema):
    """请求 runtime 调用模型。"""

    kind: Literal["invoke_model"] = "invoke_model"
    messages: list[ModelMessage] = Field(min_length=1)
    options: ModelOptions = Field(default_factory=ModelOptions)
    tools: list[ModelToolDeclaration] = Field(default_factory=list)
    output_visibility: OutputVisibility = OutputVisibility.PUBLIC_OUTPUT


class InvokeToolAction(_PatternSchema):
    """请求 runtime 执行工具动作。"""

    kind: Literal["invoke_tool"] = "invoke_tool"
    tool_call: ModelToolCall

    def to_tool_action_request(
        self,
        *,
        agent_run_id: str,
        step_id: str | None = None,
    ) -> ToolActionRequest:
        """转换为工具 executor 请求。

        Args:
            agent_run_id: AgentRun id。
            step_id: 可选 step id。

        Returns:
            ToolActionRequest。
        """
        return ToolActionRequest(
            call_id=self.tool_call.call_id,
            name=self.tool_call.name,
            arguments=self.tool_call.arguments,
            agent_run_id=agent_run_id,
            step_id=step_id,
        )


class TransitionPatternAction(_PatternSchema):
    """请求 runtime 转移到另一个 pattern。"""

    kind: Literal["transition_pattern"] = "transition_pattern"
    target_pattern: str = Field(min_length=1)
    reason: str = Field(default="pattern_decision", min_length=1)


class CompleteAction(_PatternSchema):
    """请求 runtime 完成 AgentRun。"""

    kind: Literal["complete"] = "complete"
    final_content: str = Field(min_length=1)


class FailAction(_PatternSchema):
    """请求 runtime 失败终止 AgentRun。"""

    kind: Literal["fail"] = "fail"
    reason: str = Field(min_length=1)
    error_type: str = Field(default="PatternFailed", min_length=1)


type NextAction = Annotated[
    InvokeModelAction | InvokeToolAction | TransitionPatternAction | CompleteAction | FailAction,
    Field(discriminator="kind"),
]


class ChainStage(_PatternSchema):
    """Chaining pattern 的单个阶段配置。"""

    name: str = Field(min_length=1)
    system_prompt: str | None = None
    output_visibility: OutputVisibility
    inject_previous_output: bool = True


class ChainConfig(_PatternSchema):
    """Chaining pattern 配置。"""

    stages: list[ChainStage] = Field(min_length=2)


class RoutingRule(_PatternSchema):
    """Routing pattern 的静态规则。"""

    condition_type: Literal["keyword", "regex"]
    condition_value: str = Field(min_length=1)
    target_pattern: str = Field(min_length=1)


class RoutingConfig(_PatternSchema):
    """Routing pattern 配置。"""

    rules: list[RoutingRule] = Field(default_factory=list)
    model_fallback: bool = True
    allowed_targets: list[str] = Field(default_factory=list)


__all__ = [
    "ChainConfig",
    "ChainStage",
    "CompleteAction",
    "FailAction",
    "InvokeModelAction",
    "InvokeToolAction",
    "NextAction",
    "OutputVisibility",
    "PatternObservation",
    "PatternRuntimeState",
    "RoutingConfig",
    "RoutingRule",
    "TransitionPatternAction",
]
