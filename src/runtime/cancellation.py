"""AgentRun 进程内取消令牌。"""

from dataclasses import dataclass
from enum import StrEnum


class CancellationTrigger(StrEnum):
    """取消触发来源。"""

    EXPLICIT = "explicit"
    SSE_DISCONNECT = "sse_disconnect"


@dataclass
class CancellationToken:
    """单个 AgentRun 的取消状态。"""

    agent_run_id: str
    cancelled: bool = False
    trigger: CancellationTrigger | None = None

    def cancel(self, trigger: CancellationTrigger) -> None:
        """标记取消。

        Args:
            trigger: 取消触发来源。
        """
        self.cancelled = True
        self.trigger = trigger

    def raise_if_cancelled(self) -> None:
        """取消时抛出 CancelledError。

        Raises:
            CancelledError: 当前 token 已取消。
        """
        if self.cancelled:
            raise CancelledError(self.agent_run_id, self.trigger)


class CancelledError(Exception):
    """AgentRun 已取消。"""

    def __init__(self, agent_run_id: str, trigger: CancellationTrigger | None) -> None:
        """初始化取消异常。

        Args:
            agent_run_id: AgentRun id。
            trigger: 取消来源。
        """
        self.agent_run_id = agent_run_id
        self.trigger = trigger
        super().__init__(f"AgentRun cancelled: {agent_run_id}")


class CancellationRegistry:
    """进程内 AgentRun 取消令牌注册表。"""

    def __init__(self) -> None:
        self._tokens: dict[str, CancellationToken] = {}

    def get_or_create(self, agent_run_id: str) -> CancellationToken:
        """获取或创建取消令牌。

        Args:
            agent_run_id: AgentRun id。

        Returns:
            对应取消令牌。
        """
        token = self._tokens.get(agent_run_id)
        if token is None:
            token = CancellationToken(agent_run_id=agent_run_id)
            self._tokens[agent_run_id] = token
        return token

    def cancel(self, agent_run_id: str, trigger: CancellationTrigger) -> CancellationToken:
        """取消指定 AgentRun。

        Args:
            agent_run_id: AgentRun id。
            trigger: 取消来源。

        Returns:
            已取消的令牌。
        """
        token = self.get_or_create(agent_run_id)
        token.cancel(trigger)
        return token

    def remove(self, agent_run_id: str) -> None:
        """移除令牌。

        Args:
            agent_run_id: AgentRun id。
        """
        self._tokens.pop(agent_run_id, None)


__all__ = ["CancellationRegistry", "CancellationToken", "CancellationTrigger", "CancelledError"]
