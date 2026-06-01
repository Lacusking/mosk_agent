"""Agent pattern 基础协议与通用工具。"""

from typing import Protocol

from src.contracts.patterns import CompleteAction
from src.contracts.patterns import FailAction
from src.contracts.patterns import InvokeModelAction
from src.contracts.patterns import NextAction
from src.contracts.patterns import OutputVisibility
from src.contracts.patterns import PatternObservation
from src.contracts.patterns import PatternRuntimeState
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import ModelRole
from src.contracts.runtime import ModelToolCall
from src.contracts.runtime import ModelToolDeclaration
from src.contracts.runtime import TextContentBlock


class Pattern(Protocol):
    """Agent pattern 策略协议。"""

    name: str

    def validate(self, registry: "PatternLookup") -> None:
        """校验 pattern 当前配置可执行。

        Args:
            registry: 已注册 pattern 查询接口。
        """
        ...

    def next_action(self, state: PatternRuntimeState) -> NextAction:
        """根据运行状态决定下一步动作。

        Args:
            state: runtime 提供的只读状态快照。

        Returns:
            下一步类型化动作。
        """
        ...


class PatternLookup(Protocol):
    """供 pattern/selector 校验目标 pattern 是否可用的最小接口。"""

    def has(self, name: str) -> bool:
        """检查 pattern 是否已注册。

        Args:
            name: pattern 名称。

        Returns:
            已注册时返回 True。
        """
        ...


def system_message(text: str) -> ModelMessage:
    """构造 system 文本消息。

    Args:
        text: system prompt。

    Returns:
        模型消息。
    """
    return ModelMessage(role=ModelRole.SYSTEM, content=[TextContentBlock(text=text)])


def user_message(text: str) -> ModelMessage:
    """构造 user 文本消息。

    Args:
        text: 用户文本。

    Returns:
        模型消息。
    """
    return ModelMessage(role=ModelRole.USER, content=[TextContentBlock(text=text)])


def latest_user_text(messages: list[ModelMessage]) -> str:
    """提取最后一条 user 文本。

    Args:
        messages: 可见上下文消息。

    Returns:
        最后一条 user 消息中的文本；不存在时返回空字符串。
    """
    for message in reversed(messages):
        if message.role != ModelRole.USER:
            continue
        text = message_text(message)
        if text:
            return text
    return ""


def message_text(message: ModelMessage) -> str:
    """提取消息中的文本内容。

    Args:
        message: 模型消息。

    Returns:
        拼接后的文本。
    """
    parts = [block.text for block in message.content if isinstance(block, TextContentBlock)]
    return "\n".join(parts)


def model_text(observation: PatternObservation | None) -> str:
    """从模型 observation 中提取文本。

    Args:
        observation: runtime 反馈的 observation。

    Returns:
        模型文本内容。
    """
    if observation is None or observation.kind != "model_response":
        return ""
    value = observation.data.get("text")
    return value if isinstance(value, str) else ""


def model_tool_calls(observation: PatternObservation | None) -> list[ModelToolCall]:
    """从模型 observation 中提取工具调用。

    Args:
        observation: runtime 反馈的 observation。

    Returns:
        工具调用列表。
    """
    if observation is None or observation.kind != "model_response":
        return []
    raw_calls = observation.data.get("tool_calls")
    if not isinstance(raw_calls, list):
        return []
    calls: list[ModelToolCall] = []
    for raw_call in raw_calls:
        if isinstance(raw_call, dict):
            calls.append(ModelToolCall.model_validate(raw_call))
    return calls


def last_observation(state: PatternRuntimeState) -> PatternObservation | None:
    """返回最后一个 observation。

    Args:
        state: pattern 运行状态。

    Returns:
        最后一个 observation，不存在时返回 None。
    """
    return state.observations[-1] if state.observations else None


def model_observation_count(state: PatternRuntimeState) -> int:
    """统计模型响应 observation 数量。

    Args:
        state: pattern 运行状态。

    Returns:
        模型响应数量。
    """
    return sum(1 for observation in state.observations if observation.kind == "model_response")


def complete_from_last_model(state: PatternRuntimeState) -> CompleteAction | FailAction:
    """将最后一次模型响应转换为完成动作。

    Args:
        state: pattern 运行状态。

    Returns:
        完成或失败动作。
    """
    observation = last_observation(state)
    if model_tool_calls(observation):
        return FailAction(reason="pattern 不接受工具调用", error_type="UnexpectedToolCall")
    text = model_text(observation).strip()
    if not text:
        return FailAction(reason="模型未返回可完成文本", error_type="EmptyModelOutput")
    return CompleteAction(final_content=text)


def invoke_model(
    messages: list[ModelMessage],
    *,
    visibility: OutputVisibility,
    tools: list[ModelToolDeclaration] | None = None,
) -> InvokeModelAction:
    """构造模型调用动作。

    Args:
        messages: 模型上下文。
        visibility: 输出可见性。
        tools: 可选工具声明列表。

    Returns:
        模型调用动作。
    """
    action = InvokeModelAction(messages=messages, output_visibility=visibility)
    if tools:
        action = action.model_copy(update={"tools": tools})
    return action


__all__ = [
    "Pattern",
    "PatternLookup",
    "complete_from_last_model",
    "invoke_model",
    "last_observation",
    "latest_user_text",
    "message_text",
    "model_observation_count",
    "model_text",
    "model_tool_calls",
    "system_message",
    "user_message",
]
