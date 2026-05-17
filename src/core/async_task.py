"""
异步任务队列管理器

Worker Pool 模式，支持单任务和批量任务。
"""

import asyncio
import logging
from asyncio import Future
from asyncio import Queue
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Coroutine
from typing import Any
from typing import TypeVar
from typing import overload

logger = logging.getLogger(__name__)
T = TypeVar("T")


class AsyncQueueManager:
    """异步任务队列管理器。"""

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.queue: Queue[Any] = Queue()
        self._workers: list[asyncio.Task[None]] = []
        self._sentinel = object()
        self._started = False

    async def _worker(self) -> None:
        while True:
            try:
                item = await self.queue.get()
                if item is self._sentinel:
                    self.queue.task_done()
                    break

                func, args, kwargs, future_to_resolve = item
                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = await asyncio.to_thread(func, *args, **kwargs)
                    if not future_to_resolve.done():
                        future_to_resolve.set_result(result)
                except Exception as e:
                    if not future_to_resolve.done():
                        future_to_resolve.set_exception(e)
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                break

    async def _run_batch_in_taskgroup(self, coros: list[Coroutine[Any, Any, Any]]) -> list[Any]:
        tasks: list[asyncio.Task[Any]] = []
        try:
            async with asyncio.TaskGroup() as tg:
                for coro in coros:
                    tasks.append(tg.create_task(coro))
            return [task.result() for task in tasks]
        except* Exception as eg:
            raise RuntimeError("Batch exec task failed") from eg

    @overload
    async def add_task(
        self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> Future[T]: ...

    @overload
    async def add_task(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> Future[T]: ...

    async def add_task(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
        """添加任务到队列。"""
        if not self._started:
            raise RuntimeError("QueueManager not started")

        loop = asyncio.get_running_loop()
        future: Future[Any] = loop.create_future()
        await self.queue.put((func, args, kwargs, future))
        return future

    async def add_batch(self, coros: list[Coroutine[Any, Any, Any]]) -> Future[list[Any]]:
        """批量添加协程任务，使用 TaskGroup 管理。"""
        return await self.add_task(self._run_batch_in_taskgroup, coros)

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._workers = [asyncio.create_task(self._worker()) for _ in range(self.max_workers)]

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        await self.queue.join()
        for _ in self._workers:
            await self.queue.put(self._sentinel)
        await asyncio.gather(*self._workers, return_exceptions=True)

    async def __aenter__(self) -> "AsyncQueueManager":
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.stop()
