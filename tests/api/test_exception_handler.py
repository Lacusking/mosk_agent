"""API 对平台异常入口的集成测试。"""

import asyncio
import json

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.api.exception_handler import register_exception
from src.exceptions import BaseError
from src.exceptions import ValidationError


def test_base_error_is_handled_from_new_exception_package() -> None:
    app = FastAPI()
    register_exception(app)
    handler = app.exception_handlers[BaseError]
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/failure",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
        }
    )

    response = asyncio.run(
        handler(request, ValidationError(msg="请求被拒绝", data={"field": "goal"}))
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 400
    assert json.loads(response.body) == {
        "code": 40000,
        "msg": "请求被拒绝",
        "data": {"field": "goal"},
    }
