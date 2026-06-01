"""Single-turn pattern 实现。"""

from src.contracts.patterns import NextAction
from src.contracts.patterns import OutputVisibility
from src.contracts.patterns import PatternRuntimeState
from src.patterns.base import PatternLookup
from src.patterns.base import complete_from_last_model
from src.patterns.base import invoke_model
from src.patterns.base import system_message
from src.patterns.single_turn.prompt import SINGLE_TURN_SYSTEM_PROMPT


class SingleTurnPattern:
    """一次公开模型响应后完成的 pattern。"""

    name = "single_turn"

    def validate(self, registry: PatternLookup) -> None:
        """校验 single_turn 配置。

        Args:
            registry: pattern 查询接口。
        """
        return None

    def next_action(self, state: PatternRuntimeState) -> NextAction:
        """决定 single_turn 下一步动作。

        Args:
            state: runtime 状态。

        Returns:
            模型调用或完成动作。
        """
        if not state.observations:
            return invoke_model(
                [system_message(SINGLE_TURN_SYSTEM_PROMPT), *state.visible_context_messages],
                visibility=OutputVisibility.PUBLIC_OUTPUT,
            )
        return complete_from_last_model(state)


__all__ = ["SingleTurnPattern"]
