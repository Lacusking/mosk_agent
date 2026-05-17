"""
FastAPI 应用注册

注册日志、中间件、路由、异常处理、扩展。
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.exception_handler import register_exception
from src.api.middlewares.request_middleware import RequestIdMiddleware
from src.core.config import settings
from src.core.logging import setup_logger

logger = logging.getLogger(__name__)


def _build_cors_origins(raw_origins: str) -> list[str]:
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return origins or ["http://localhost:3000"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理。"""
    _ = app
    from src.api import extensions

    await extensions.startup()
    logger.info("Application started")

    yield

    logger.info("Application shutdown: cleaning up resources...")
    await extensions.shutdown()
    logger.info("Cleanup complete.")


def register_app() -> FastAPI:
    """注册并返回 FastAPI 应用实例。"""
    app = FastAPI(
        title=settings.app.SERVICE_TITLE,
        version=settings.app.VERSION,
        lifespan=lifespan,
    )

    register_logger()
    register_middleware(app)
    register_router(app)
    register_exception(app)

    return app


def register_logger() -> None:
    """注册日志系统。"""
    setup_logger(
        name="mosk_agent",
        level=settings.log.LOG_LEVEL,
        log_dir=settings.log.LOG_DIR,
        log_format=settings.log.LOG_FORMAT,
        console_json=settings.log.ENABLE_JSON,
        file_json=settings.log.ENABLE_JSON,
        json_indent=2,
        console_color=True,
        max_bytes=settings.log.LOG_FILE_MAX_SIZE,
        backup_count=settings.log.LOG_FILE_BACKUP_COUNT,
        enable_console=settings.log.ENABLE_CONSOLE,
        enable_file=settings.log.ENABLE_FILE,
        exclude_logger_name=["httpx", "httpcore"],
    )


def register_middleware(app: FastAPI) -> None:
    """注册中间件（执行顺序从下往上）。"""
    cors_origins = _build_cors_origins(settings.app.CORS_ORIGINS)
    cors_allow_credentials = settings.app.CORS_ALLOW_CREDENTIALS

    if settings.app.ENVIRONMENT != "dev" and "*" in cors_origins and cors_allow_credentials:
        logger.warning(
            "CORS misconfiguration detected in non-dev environment, "
            "forcing allow_credentials=False."
        )
        cors_allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RequestIdMiddleware)


def register_router(app: FastAPI) -> None:
    """注册路由。"""
    from src.api.controllers.v1.router import api_router

    app.include_router(api_router, prefix="")
