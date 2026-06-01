"""Runtime 对 ModelAdapter 的统一调用封装。"""

from collections.abc import AsyncIterator

from src.contracts.runtime import ModelRequest
from src.contracts.runtime import ModelResponse
from src.contracts.runtime import ModelStreamEvent
from src.models.base import ModelAdapter
from src.models.streaming import ModelStreamReducer


class RuntimeModelInvoker:
    """为 runtime 提供 blocking 与 streaming 模型调用入口。"""

    def __init__(self, adapter: ModelAdapter) -> None:
        """初始化 invoker。

        Args:
            adapter: 已注册的模型 adapter。
        """
        self._adapter = adapter

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        """执行 blocking 模型调用。

        Args:
            request: 标准模型请求。

        Returns:
            统一模型响应。
        """
        return await self._adapter.invoke(request)

    async def stream_and_reduce(
        self,
        request: ModelRequest,
    ) -> tuple[ModelResponse, list[ModelStreamEvent]]:
        """消费模型流并归约为最终响应。

        Args:
            request: 标准模型请求。

        Returns:
            最终 ModelResponse 与消费过的流事件列表。
        """
        reducer = ModelStreamReducer()
        events: list[ModelStreamEvent] = []
        async for event in self.stream(request):
            reducer.consume(event)
            events.append(event)
        return reducer.response(), events

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]:
        """执行 streaming 模型调用。

        Args:
            request: 标准模型请求。

        Returns:
            统一模型流事件异步迭代器。
        """
        return self._adapter.stream(request)


__all__ = ["RuntimeModelInvoker"]
