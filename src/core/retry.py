"""
指数退避重试装饰器
"""

import asyncio
import functools
import logging
import random
from collections.abc import Callable
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)


def async_retry_with_backoff(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retry_on_exceptions: tuple[type[Exception], ...] = (Exception,),
    non_retryable_filter: Callable[[Exception], bool] | None = None,
) -> Callable:
    """
    异步指数退避重试装饰器。

    Args:
        max_retries: 最大重试次数。
        base_delay: 初始延迟时间（秒），每次重试按指数增长。
        max_delay: 最大延迟时间（秒）。
        retry_on_exceptions: 触发重试的异常类型元组。
        non_retryable_filter: 可选过滤函数，返回 True 时停止重试。

    Returns:
        装饰器函数。
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            delay = base_delay

            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except retry_on_exceptions as e:
                    if non_retryable_filter is not None and non_retryable_filter(e):
                        logger.error(
                            "[RetryDecorator] Non-retryable exception in %s: %s",
                            func.__name__, e,
                        )
                        raise

                    retries += 1
                    if retries == max_retries:
                        logger.error(
                            "[RetryDecorator] All %d retries failed for %s.",
                            max_retries, func.__name__,
                        )
                        raise

                    jitter = random.uniform(0.5, 1.5)
                    sleep_time = min(delay * jitter, max_delay)
                    logger.warning(
                        "[RetryDecorator] Error in %s: %s. Retrying in %.2fs (%d/%d).",
                        func.__name__, e, sleep_time, retries, max_retries,
                    )
                    await asyncio.sleep(sleep_time)
                    delay *= 2

            raise RuntimeError(f"Retry logic failed unexpectedly for {func.__name__}")

        return wrapper

    return decorator
