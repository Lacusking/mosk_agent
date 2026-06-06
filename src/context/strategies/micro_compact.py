"""预留 micro compact 策略。"""

from src.context.schemas import ContextBundle


class MicroCompactStrategy:
    """预留用于压缩旧 observation 或大段工具结果的策略。"""

    async def apply(self, bundle: ContextBundle) -> ContextBundle:
        """执行策略。

        Args:
            bundle: 输入上下文包。

        Raises:
            NotImplementedError: 首期未实现。
        """
        raise NotImplementedError("microCompact 策略预留，当前 change 不实现")


__all__ = ["MicroCompactStrategy"]
