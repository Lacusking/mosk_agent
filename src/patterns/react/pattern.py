"""ReAct pattern 实现。"""

from src.contracts.patterns import FailAction
from src.contracts.patterns import InvokeToolAction
from src.contracts.patterns import NextAction
from src.contracts.patterns import OutputVisibility
from src.contracts.patterns import PatternObservation
from src.contracts.patterns import PatternRuntimeState
from src.patterns.base import PatternLookup
from src.patterns.base import complete_from_last_model
from src.patterns.base import invoke_model
from src.patterns.base import last_observation
from src.patterns.base import model_text
from src.patterns.base import model_tool_calls
from src.patterns.base import system_message
from src.patterns.base import user_message
from src.patterns.react.prompt import REACT_FINAL_PROMPT
from src.patterns.react.prompt import REACT_OBSERVE_PROMPT
from src.patterns.react.prompt import REACT_THINK_PROMPT


def _has_preceding_tool_result(observations: list[PatternObservation]) -> bool:
    """检查 observation 历史中是否包含 tool_result。"""
    return any(obs.kind == "tool_result" for obs in observations)


class ReactPattern:
    """支持多轮 think-act-observe 循环的 ReAct pattern。"""

    name = "react"

    def validate(self, registry: PatternLookup) -> None:
        """校验 react 配置。

        Args:
            registry: pattern 查询接口。
        """
        return None

    def next_action(self, state: PatternRuntimeState) -> NextAction:
        """决定 ReAct 下一步动作。

        状态转换：
        - 无 observation -> internal 模型调用（带工具声明）
        - model_response 有 tool_calls -> 执行第一个工具
        - model_response 无 tool_calls + 之前有 tool_result -> public final generation
        - model_response 无 tool_calls + 之前无 tool_result -> 直接完成
        - tool_result -> internal 模型调用（带工具声明，继续循环）

        Args:
            state: runtime 状态。

        Returns:
            模型调用、工具动作、完成或失败动作。
        """
        if state.step_count >= state.agent_run.max_steps:
            return FailAction(reason="达到最大 step 限制", error_type="MaxStepsExceeded")

        observation = last_observation(state)

        if observation is None:
            return self._think(state)

        if observation.kind == "tool_result":
            return self._think_after_observation(state, observation)

        if observation.kind == "model_response":
            return self._handle_model_response(state, observation)

        return FailAction(reason="ReAct 收到未知 observation", error_type="InvalidObservation")

    def _think(self, state: PatternRuntimeState) -> NextAction:
        """首次 think：internal 模型调用，带工具声明。"""
        return invoke_model(
            [system_message(REACT_THINK_PROMPT), *state.visible_context_messages],
            visibility=OutputVisibility.INTERNAL,
            tools=state.available_tools,
        )

    def _think_after_observation(
        self, state: PatternRuntimeState, observation: PatternObservation
    ) -> NextAction:
        """工具结果后继续 think：internal 模型调用，仍可选择工具。"""
        obs_data = observation.data
        return invoke_model(
            [
                system_message(REACT_OBSERVE_PROMPT),
                *state.visible_context_messages,
                user_message(f"工具 observation：\n{obs_data}"),
            ],
            visibility=OutputVisibility.INTERNAL,
            tools=state.available_tools,
        )

    def _handle_model_response(
        self, state: PatternRuntimeState, observation: PatternObservation
    ) -> NextAction:
        """处理模型响应：有工具调用则执行，无则准备完成。"""
        calls = model_tool_calls(observation)
        if calls:
            return InvokeToolAction(tool_call=calls[0])

        text = model_text(observation).strip()
        if not text:
            return FailAction(reason="ReAct 模型未返回文本或工具调用", error_type="EmptyModelOutput")

        if _has_preceding_tool_result(state.observations):
            return invoke_model(
                [
                    system_message(REACT_FINAL_PROMPT),
                    *state.visible_context_messages,
                    user_message(f"内部分析结论：\n{text}"),
                ],
                visibility=OutputVisibility.PUBLIC_OUTPUT,
            )

        return complete_from_last_model(state)


__all__ = ["ReactPattern"]
