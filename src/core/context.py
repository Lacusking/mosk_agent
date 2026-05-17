"""
请求上下文管理

管理 request_id 和 trace_id 的线程安全上下文变量。
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from contextvars import Token

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
trace_id_ctx: ContextVar[str | None] = ContextVar("trace_id", default=None)


@contextmanager
def request_safe_context(
    initial_data: str | None = None,
) -> Iterator[None]:
    """
    request_id 请求上下文管理器。

    Args:
        initial_data: 指定 request_id，为 None 时自动生成 UUID。
    """
    if initial_data is None:
        initial_data = str(uuid.uuid4())
    token: Token = request_id_ctx.set(initial_data)
    try:
        yield
    finally:
        request_id_ctx.reset(token)


@contextmanager
def trace_safe_context(
    initial_data: str | None = None,
) -> Iterator[None]:
    """
    trace_id 跟踪上下文管理器。

    Args:
        initial_data: 指定 trace_id，为 None 时自动生成 UUID。
    """
    if initial_data is None:
        initial_data = str(uuid.uuid4())
    token: Token = trace_id_ctx.set(initial_data)
    try:
        yield
    finally:
        trace_id_ctx.reset(token)
