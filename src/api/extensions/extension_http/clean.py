"""
httpx 扩展清理

清理 HTTP 客户端资源。
"""

import logging

from src.core.httpx_client import HttpxClientManager

logger = logging.getLogger(__name__)


async def clean() -> None:
    """关闭所有 HTTP Client Pool。"""
    logger.info("Closing all HTTP Client Pools...")
    await HttpxClientManager.close()
