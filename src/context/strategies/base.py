"""上下文策略协议。"""

from typing import Protocol

from src.context.schemas import ContextBundle


class ContextStrategy(Protocol):
    """上下文处理策略协议。"""

    async def apply(self, bundle: ContextBundle) -> ContextBundle:
        """处理上下文包。

        Args:
            bundle: 输入上下文包。

        Returns:
            处理后的上下文包。
        """
        ...


__all__ = ["ContextStrategy"]
