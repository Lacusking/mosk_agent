"""工具动作 executor 端口。"""

from typing import Protocol

from src.contracts.runtime import ModelToolDeclaration
from src.contracts.tools import ToolActionRequest
from src.contracts.tools import ToolActionResult


class ToolActionExecutor(Protocol):
    """Runtime 调用工具动作的最小端口。"""

    async def execute(self, request: ToolActionRequest) -> ToolActionResult:
        """执行工具动作。

        Args:
            request: 工具动作请求。

        Returns:
            工具动作结果。
        """
        ...

    def declarations(self) -> list[ModelToolDeclaration]:
        """返回已注册工具的模型声明。

        Returns:
            可传入 ModelRequest 的工具声明列表。
        """
        ...


__all__ = ["ToolActionExecutor"]
