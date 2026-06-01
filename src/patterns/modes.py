"""Agent mode 到默认 pattern 的映射。"""

from src.contracts.agent_runs import AgentMode
from src.core.config import AgentRuntimeConfig


def default_pattern_for_mode(mode: AgentMode, config: AgentRuntimeConfig) -> str:
    """根据 mode 和配置解析默认 pattern。

    Args:
        mode: Agent mode。
        config: runtime 配置。

    Returns:
        默认 pattern 名称。
    """
    return {
        AgentMode.CHAT: config.DEFAULT_CHAT_PATTERN,
        AgentMode.PLAN: config.DEFAULT_PLAN_PATTERN,
        AgentMode.BUILD: config.DEFAULT_BUILD_PATTERN,
        AgentMode.REVIEW: config.DEFAULT_REVIEW_PATTERN,
    }[mode]


__all__ = ["default_pattern_for_mode"]
