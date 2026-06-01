"""AgentRun 生命周期状态机。"""

from src.contracts.agent_runs import AgentRunStatus

_ALLOWED_TRANSITIONS: dict[AgentRunStatus, frozenset[AgentRunStatus]] = {
    AgentRunStatus.CREATED: frozenset(
        {
            AgentRunStatus.RUNNING,
            AgentRunStatus.COMPLETED,
            AgentRunStatus.FAILED,
            AgentRunStatus.CANCELLED,
        }
    ),
    AgentRunStatus.RUNNING: frozenset(
        {AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.CANCELLED}
    ),
    AgentRunStatus.COMPLETED: frozenset(),
    AgentRunStatus.FAILED: frozenset(),
    AgentRunStatus.CANCELLED: frozenset(),
}


def can_transition(current: AgentRunStatus, target: AgentRunStatus) -> bool:
    """判断 AgentRun 状态转换是否合法。

    Args:
        current: 当前状态。
        target: 目标状态。

    Returns:
        合法返回 True，否则 False。
    """
    return target in _ALLOWED_TRANSITIONS[current]


def ensure_transition(current: AgentRunStatus, target: AgentRunStatus) -> None:
    """校验 AgentRun 状态转换。

    Args:
        current: 当前状态。
        target: 目标状态。

    Raises:
        ValueError: 状态转换非法。
    """
    if not can_transition(current, target):
        raise ValueError(f"非法 AgentRun 状态转换: {current.value} -> {target.value}")


__all__ = ["can_transition", "ensure_transition"]
