"""
httpx 扩展注册

管理 httpx client 的初始化。
"""

import logging

from src.api.extensions.extension_http.schema import ServiceClient
from src.core.config import settings
from src.core.httpx_client import ClientConfig
from src.core.httpx_client import HttpxClientManager

logger = logging.getLogger(__name__)


def register() -> None:
    """遍历业务枚举，自动注册并初始化所有服务的连接池。"""
    default_config = ClientConfig(
        timeout=settings.app.HTTPX_TIMEOUT if hasattr(settings.app, "HTTPX_TIMEOUT") else 30.0,
    )

    registered_count = 0
    for client_name in ServiceClient:
        HttpxClientManager.register(client_name, default_config)
        registered_count += 1

    logger.info("Registered %d HTTP Client Pools from ServiceClient Enum.", registered_count)
