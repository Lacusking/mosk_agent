"""上下文策略管线。"""

from collections.abc import Sequence

from src.context.schemas import ContextBundle
from src.context.strategies.base import ContextStrategy


class ContextStrategyPipeline:
    """按注册顺序执行上下文策略。"""

    def __init__(self, strategies: Sequence[ContextStrategy] | None = None) -> None:
        """初始化管线。

        Args:
            strategies: 待顺序执行的策略列表。
        """
        self._strategies = list(strategies or [])

    async def apply(self, bundle: ContextBundle) -> ContextBundle:
        """执行全部上下文策略。

        Args:
            bundle: 原始上下文包。

        Returns:
            策略处理后的上下文包。
        """
        current = bundle
        for strategy in self._strategies:
            current = await strategy.apply(current)
        return current


__all__ = ["ContextStrategyPipeline"]
