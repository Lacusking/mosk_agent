"""预留自动摘要压缩策略。"""

from src.context.schemas import ContextBundle


class AutoCompactStrategy:
    """预留用于 LLM summary compact 的策略。"""

    async def apply(self, bundle: ContextBundle) -> ContextBundle:
        """执行策略。

        Args:
            bundle: 输入上下文包。

        Raises:
            NotImplementedError: 首期未实现。
        """
        raise NotImplementedError("autoCompact 策略预留，当前 change 不实现")


__all__ = ["AutoCompactStrategy"]
