"""预留工具结果预算策略。"""

from src.context.schemas import ContextBundle


class ToolResultBudgetStrategy:
    """预留用于限制 tool result 总大小的策略。"""

    async def apply(self, bundle: ContextBundle) -> ContextBundle:
        """执行策略。

        Args:
            bundle: 输入上下文包。

        Raises:
            NotImplementedError: 首期未实现。
        """
        raise NotImplementedError("toolResultBudget 策略预留，当前 change 不实现")


__all__ = ["ToolResultBudgetStrategy"]
