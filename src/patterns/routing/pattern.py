"""Routing pattern 实现。"""

import re

from src.contracts.patterns import FailAction
from src.contracts.patterns import NextAction
from src.contracts.patterns import OutputVisibility
from src.contracts.patterns import PatternRuntimeState
from src.contracts.patterns import RoutingConfig
from src.contracts.patterns import RoutingRule
from src.contracts.patterns import TransitionPatternAction
from src.patterns.base import PatternLookup
from src.patterns.base import invoke_model
from src.patterns.base import latest_user_text
from src.patterns.base import model_text
from src.patterns.base import system_message
from src.patterns.routing.prompt import DEFAULT_PATTERN_DESCRIPTIONS
from src.patterns.routing.prompt import ROUTING_PROMPT_TEMPLATE


def _build_pattern_descriptions(allowed: list[str]) -> str:
    """构建 pattern 描述文本，供 routing prompt 使用。"""
    lines = []
    for name in allowed:
        desc = DEFAULT_PATTERN_DESCRIPTIONS.get(name, f"{name} pattern")
        lines.append(f"- `{name}`: {desc}")
    return "\n".join(lines)


def default_routing_config() -> RoutingConfig:
    """返回默认 routing 配置。

    Returns:
        默认规则与允许目标。
    """
    return RoutingConfig(
        rules=[
            RoutingRule(condition_type="keyword", condition_value="计划", target_pattern="planning"),
            RoutingRule(condition_type="keyword", condition_value="plan", target_pattern="planning"),
            RoutingRule(condition_type="keyword", condition_value="审查", target_pattern="reflection"),
            RoutingRule(condition_type="keyword", condition_value="review", target_pattern="reflection"),
            RoutingRule(condition_type="keyword", condition_value="实现", target_pattern="react"),
            RoutingRule(condition_type="keyword", condition_value="build", target_pattern="react"),
        ],
        model_fallback=True,
        allowed_targets=["single_turn", "planning", "react", "reflection", "chaining"],
    )


def _extract_target(text: str, allowed: list[str]) -> str | None:
    """从模型输出中提取目标 pattern 名称。

    优先精确匹配，其次查找文本中唯一出现的 allowed target。

    Args:
        text: 模型输出文本。
        allowed: 允许的目标列表。

    Returns:
        目标 pattern 名称，无法确定时返回 None。
    """
    stripped = text.strip()
    if stripped in allowed:
        return stripped
    found = [target for target in allowed if re.search(rf"\b{re.escape(target)}\b", stripped)]
    if len(found) == 1:
        return found[0]
    return None


class RoutingPattern:
    """按规则或内部模型分类转移到目标 pattern。"""

    name = "routing"

    def __init__(self, config: RoutingConfig | None = None) -> None:
        """初始化 routing pattern。

        Args:
            config: 可选 routing 配置。
        """
        self.config = config or default_routing_config()

    def validate(self, registry: PatternLookup) -> None:
        """校验 routing 目标均已注册。

        Args:
            registry: pattern 查询接口。

        Raises:
            ValueError: 存在未注册目标。
        """
        targets = {rule.target_pattern for rule in self.config.rules}
        targets.update(self.config.allowed_targets)
        missing = sorted(target for target in targets if not registry.has(target))
        if missing:
            raise ValueError(f"routing 目标 pattern 未注册: {missing}")

    def next_action(self, state: PatternRuntimeState) -> NextAction:
        """决定 routing 下一步动作。

        Args:
            state: runtime 状态。

        Returns:
            pattern 转移动作、内部模型分类动作或失败动作。
        """
        if not state.observations:
            text = latest_user_text(state.visible_context_messages)
            target = self._match_rule(text)
            if target:
                return TransitionPatternAction(target_pattern=target, reason="routing_rule")
            if not self.config.model_fallback:
                return TransitionPatternAction(target_pattern="single_turn", reason="routing_fallback")
            descriptions = _build_pattern_descriptions(self.config.allowed_targets)
            prompt = ROUTING_PROMPT_TEMPLATE.format(pattern_descriptions=descriptions)
            return invoke_model(
                [system_message(prompt), *state.visible_context_messages],
                visibility=OutputVisibility.INTERNAL,
            )

        raw = model_text(state.observations[-1])
        target = _extract_target(raw, self.config.allowed_targets)
        if target:
            return TransitionPatternAction(target_pattern=target, reason="routing_model")
        return FailAction(
            reason=f"routing 模型返回无法识别的目标: {raw.strip()!r}",
            error_type="InvalidRoutingTarget",
        )

    def _match_rule(self, text: str) -> str | None:
        for rule in self.config.rules:
            if rule.condition_type == "keyword" and rule.condition_value.lower() in text.lower():
                return rule.target_pattern
            if rule.condition_type == "regex" and re.search(rule.condition_value, text):
                return rule.target_pattern
        return None


__all__ = ["RoutingPattern", "default_routing_config"]
