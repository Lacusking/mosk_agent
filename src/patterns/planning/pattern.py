"""Planning pattern 实现。"""

from src.contracts.patterns import NextAction
from src.contracts.patterns import OutputVisibility
from src.contracts.patterns import PatternRuntimeState
from src.patterns.base import PatternLookup
from src.patterns.base import complete_from_last_model
from src.patterns.base import invoke_model
from src.patterns.base import system_message
from src.patterns.planning.prompt import PLANNING_SYSTEM_PROMPT


class PlanningPattern:
    """以结构化计划文本完成的 pattern。"""

    name = "planning"

    def validate(self, registry: PatternLookup) -> None:
        """校验 planning 配置。

        Args:
            registry: pattern 查询接口。
        """
        return None

    def next_action(self, state: PatternRuntimeState) -> NextAction:
        """决定 planning 下一步动作。

        Args:
            state: runtime 状态。

        Returns:
            模型调用或完成动作。
        """
        if not state.observations:
            return invoke_model(
                [system_message(PLANNING_SYSTEM_PROMPT), *state.visible_context_messages],
                visibility=OutputVisibility.PUBLIC_OUTPUT,
            )
        return complete_from_last_model(state)


__all__ = ["PLANNING_SYSTEM_PROMPT", "PlanningPattern"]
