"""
请求中间件

为每个请求注入 request_id。
"""

import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.context import request_safe_context


class RequestIdMiddleware(BaseHTTPMiddleware):
    """为每个请求生成唯一 request_id 并注入上下文。"""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = str(uuid.uuid4())
        with request_safe_context(request_id):
            response = await call_next(request)
            return response
