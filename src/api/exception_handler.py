"""
全局异常处理

定义各类异常的统一处理方式。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from src.api.response import GeneralResponseCode
from src.api.response import StandardResponseCode
from src.api.response import response_base
from src.core.config import settings
from src.exceptions import BaseError

logger = logging.getLogger(__name__)


class ErrorResponseModel(PydanticBaseModel):
    """异常响应模型。"""

    code: int
    msg: str
    data: Any | None = None


def _is_dev() -> bool:
    return str(getattr(settings.app, "ENVIRONMENT", "")).lower() == "dev"


def _build_content(*, code: int, msg: str, data: Any | None) -> dict[str, Any]:
    return ErrorResponseModel(code=code, msg=msg, data=data).model_dump()


def register_exception(app: FastAPI) -> None:
    """注册全局异常处理器。"""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = list(exc.errors())
        error = errors[0] if errors else {}
        error_msg = str(error.get("msg", "参数校验失败"))
        msg = f"请求参数非法: {error_msg}"
        data = {"errors": errors} if _is_dev() else None

        logger.warning(
            "Validation error: path=%s method=%s errors=%s",
            request.url.path, request.method, errors,
        )
        return JSONResponse(
            status_code=StandardResponseCode.HTTP_422,
            content=_build_content(code=StandardResponseCode.HTTP_422, msg=msg, data=data),
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        errors = list(exc.errors())
        msg = f"数据校验失败: {errors[0].get('msg', '')}" if errors else "数据校验失败"
        logger.warning("Pydantic validation error: path=%s", request.url.path)
        return JSONResponse(
            status_code=StandardResponseCode.HTTP_422,
            content=_build_content(code=StandardResponseCode.HTTP_422, msg=msg, data=None),
        )

    @app.exception_handler(BaseError)
    async def base_error_handler(request: Request, exc: BaseError) -> JSONResponse:
        logger.info(
            "Business exception: path=%s code=%s msg=%s",
            request.url.path, exc.code, exc.msg,
        )
        return JSONResponse(
            status_code=StandardResponseCode.HTTP_400,
            content=exc.to_dict(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        logger.warning(
            "HTTP exception: path=%s status=%s detail=%s",
            request.url.path, exc.status_code, exc.detail,
        )
        if _is_dev():
            content = _build_content(code=exc.status_code, msg=str(exc.detail), data=None)
        else:
            res_code = (
                GeneralResponseCode.HTTP_400
                if 400 <= exc.status_code < 500
                else GeneralResponseCode.HTTP_500
            )
            content = response_base.fail(res=res_code).model_dump()
        return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)

    @app.exception_handler(Exception)
    async def unknown_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: path=%s method=%s", request.url.path, request.method)
        if _is_dev():
            content = _build_content(
                code=StandardResponseCode.HTTP_500,
                msg=f"Internal Server Error: {exc}",
                data={"error_type": exc.__class__.__name__},
            )
        else:
            content = response_base.fail(res=GeneralResponseCode.HTTP_500).model_dump()
        return JSONResponse(status_code=StandardResponseCode.HTTP_500, content=content)
