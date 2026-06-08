"""预留 reactive compact 策略。"""

from src.context.schemas import ContextBundle


class ReactiveCompactStrategy:
    """预留用于 prompt_too_long/413 后错误恢复的策略。"""

    async def apply(self, bundle: ContextBundle) -> ContextBundle:
        """执行策略。

        Args:
            bundle: 输入上下文包。

        Raises:
            NotImplementedError: 首期未实现。
        """
        raise NotImplementedError("reactiveCompact 策略预留，当前 change 不实现")


__all__ = ["ReactiveCompactStrategy"]
