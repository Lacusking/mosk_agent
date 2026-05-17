"""
Redis 客户端初始化

提供异步 Redis 客户端与健康检查。
"""

import logging

from redis.asyncio import Redis
from redis.exceptions import AuthenticationError
from redis.exceptions import TimeoutError

from src.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient(Redis):  # type: ignore[type-arg]
    """Redis 异步客户端。"""

    def __init__(self) -> None:
        super().__init__(
            host=settings.redis.REDIS_HOST,
            port=settings.redis.REDIS_PORT,
            password=settings.redis.REDIS_PASS,
            db=settings.redis.REDIS_DB,
            socket_timeout=settings.redis.REDIS_TIMEOUT,
            socket_connect_timeout=settings.redis.REDIS_TIMEOUT,
            socket_keepalive=True,
            health_check_interval=30,
            decode_responses=True,
        )

    async def init(self) -> None:
        """执行连接探活。"""
        try:
            await self.ping()
        except TimeoutError:
            logger.error("Redis 连接超时")
            raise
        except AuthenticationError:
            logger.error("Redis 认证失败")
            raise
        except Exception as e:
            logger.error("Redis 连接异常: %s", e)
            raise


redis_client = RedisClient()
