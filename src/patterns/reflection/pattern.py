"""Reflection pattern 实现。"""

from src.contracts.patterns import FailAction
from src.contracts.patterns import NextAction
from src.contracts.patterns import OutputVisibility
from src.contracts.patterns import PatternRuntimeState
from src.patterns.base import PatternLookup
from src.patterns.base import complete_from_last_model
from src.patterns.base import invoke_model
from src.patterns.base import model_observation_count
from src.patterns.base import model_text
from src.patterns.base import system_message
from src.patterns.base import user_message
from src.patterns.reflection.prompt import REFLECTION_CRITIQUE_PROMPT
from src.patterns.reflection.prompt import REFLECTION_DRAFT_PROMPT
from src.patterns.reflection.prompt import REFLECTION_REVISE_PROMPT


class ReflectionPattern:
    """draft、critique、revise 三阶段 reflection pattern。"""

    name = "reflection"

    def validate(self, registry: PatternLookup) -> None:
        """校验 reflection 配置。

        Args:
            registry: pattern 查询接口。
        """
        return None

    def next_action(self, state: PatternRuntimeState) -> NextAction:
        """决定 reflection 下一步动作。

        Args:
            state: runtime 状态。

        Returns:
            模型调用、完成或失败动作。
        """
        count = model_observation_count(state)
        if count == 0:
            return invoke_model(
                [
                    system_message(REFLECTION_DRAFT_PROMPT),
                    *state.visible_context_messages,
                ],
                visibility=OutputVisibility.INTERNAL,
            )
        if count == 1:
            draft = model_text(state.observations[-1]).strip()
            if not draft:
                return FailAction(reason="draft 阶段未产生文本", error_type="EmptyDraftOutput")
            return invoke_model(
                [
                    system_message(REFLECTION_CRITIQUE_PROMPT),
                    user_message(draft),
                ],
                visibility=OutputVisibility.INTERNAL,
            )
        if count == 2:
            draft = model_text(state.observations[-2]).strip()
            critique = model_text(state.observations[-1]).strip()
            if not draft:
                return FailAction(reason="draft 阶段未产生文本", error_type="EmptyDraftOutput")
            if not critique:
                return FailAction(reason="critique 阶段未产生文本", error_type="EmptyCritiqueOutput")
            return invoke_model(
                [
                    system_message(REFLECTION_REVISE_PROMPT),
                    *state.visible_context_messages,
                    user_message(f"草稿：\n{draft}\n\ncritique：\n{critique}"),
                ],
                visibility=OutputVisibility.PUBLIC_OUTPUT,
            )
        return complete_from_last_model(state)


__all__ = ["ReflectionPattern"]
