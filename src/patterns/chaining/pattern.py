"""Chaining pattern 实现。"""

from src.contracts.patterns import ChainConfig
from src.contracts.patterns import ChainStage
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
from src.patterns.chaining.prompt import CHAIN_ANALYZE_SYSTEM_PROMPT
from src.patterns.chaining.prompt import CHAIN_FINAL_SYSTEM_PROMPT


def default_chain_config() -> ChainConfig:
    """返回首期默认 chaining 配置。

    Returns:
        默认两阶段链。
    """
    return ChainConfig(
        stages=[
            ChainStage(
                name="analyze",
                system_prompt=CHAIN_ANALYZE_SYSTEM_PROMPT,
                output_visibility=OutputVisibility.INTERNAL,
                inject_previous_output=False,
            ),
            ChainStage(
                name="final",
                system_prompt=CHAIN_FINAL_SYSTEM_PROMPT,
                output_visibility=OutputVisibility.PUBLIC_OUTPUT,
                inject_previous_output=True,
            ),
        ]
    )


class ChainingPattern:
    """按固定阶段顺序执行模型调用的 pattern。"""

    name = "chaining"

    def __init__(self, config: ChainConfig | None = None) -> None:
        """初始化 chaining pattern。

        Args:
            config: 可选 chain 配置。
        """
        self.config = config or default_chain_config()

    def validate(self, registry: PatternLookup) -> None:
        """校验 chain 配置。

        Args:
            registry: pattern 查询接口。

        Raises:
            ValueError: 最后一阶段不是 public_output。
        """
        if len(self.config.stages) < 2:
            raise ValueError("chaining 至少需要两个阶段")
        if self.config.stages[-1].output_visibility != OutputVisibility.PUBLIC_OUTPUT:
            raise ValueError("chaining 最后一阶段必须为 public_output")

    def next_action(self, state: PatternRuntimeState) -> NextAction:
        """决定 chaining 下一步动作。

        Args:
            state: runtime 状态。

        Returns:
            模型调用、完成或失败动作。
        """
        stage_index = model_observation_count(state)
        if stage_index >= len(self.config.stages):
            return complete_from_last_model(state)

        stage = self.config.stages[stage_index]
        messages = list(state.visible_context_messages)
        if stage.system_prompt:
            messages.insert(0, system_message(stage.system_prompt))
        if stage.inject_previous_output and state.observations:
            model_observations = [
                obs for obs in state.observations if obs.kind == "model_response"
            ]
            prev_obs = model_observations[stage_index - 1] if stage_index > 0 and stage_index <= len(model_observations) else None
            previous = model_text(prev_obs).strip() if prev_obs else ""
            if not previous:
                return FailAction(reason="chaining 前序阶段无文本输出", error_type="EmptyChainStageOutput")
            messages.append(user_message(f"前序阶段输出：\n{previous}"))
        return invoke_model(messages, visibility=stage.output_visibility)


__all__ = ["ChainingPattern", "default_chain_config"]
