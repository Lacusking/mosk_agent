"""
httpx 异步 HTTP 客户端管理

支持多客户端池、连接复用与自动重试。
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from typing import Any

import httpx
from pydantic import BaseModel

from src.core.retry import async_retry_with_backoff

logger = logging.getLogger(__name__)


class ClientName(StrEnum):
    """客户端名称枚举。"""

    DEFAULT = "default"


@dataclass
class ClientConfig:
    """客户端配置项。"""

    base_url: str = ""
    timeout: float = 30.0
    max_connections: int = 100
    max_keepalive: int = 20
    headers: dict[str, str] | BaseModel = field(default_factory=dict)


@async_retry_with_backoff(max_retries=3)
async def _internal_request(
    method: str,
    url: str,
    *,
    client_name: str | ClientName = ClientName.DEFAULT,
    params: dict | None = None,
    json: dict | None = None,
    **kwargs: Any,
) -> bytes:
    """底层请求实现，包含重试机制。"""
    client = await HttpxClientManager.get_client(client_name)
    logger.debug("[HTTP-%s] %s %s", client_name, method, url)

    try:
        response = await client.request(method=method, url=url, params=params, json=json, **kwargs)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error("[HTTP-%s] Request Error: %s", client_name, e)
        raise


@asynccontextmanager
async def _internal_stream(
    method: str,
    url: str,
    *,
    client_name: str | ClientName = ClientName.DEFAULT,
    **kwargs: Any,
) -> AsyncGenerator[httpx.Response, None]:
    """底层流式请求实现。"""
    client = await HttpxClientManager.get_client(client_name)
    try:
        async with client.stream(method, url, **kwargs) as response:
            yield response
    except Exception as e:
        logger.error("[HTTP-%s] Stream Error: %s", client_name, e)
        raise


class BoundHttpClient:
    """绑定了特定 client_name 的客户端代理。"""

    def __init__(self, name: str | ClientName = ClientName.DEFAULT):
        self.client_name = name

    async def request(self, method: str, url: str, **kwargs: Any) -> Any:
        return await _internal_request(method, url, client_name=self.client_name, **kwargs)

    async def get(self, url: str, **kwargs: Any) -> Any:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> Any:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> Any:
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> Any:
        return await self.request("DELETE", url, **kwargs)

    def stream(self, method: str, url: str, **kwargs: Any) -> Any:
        return _internal_stream(method, url, client_name=self.client_name, **kwargs)


class AsyncHttpClient:
    """通用 HTTP 客户端静态工具。"""

    @classmethod
    def bind(cls, name: str | ClientName = ClientName.DEFAULT) -> BoundHttpClient:
        return BoundHttpClient(name)

    @staticmethod
    async def request(
        method: str,
        url: str,
        *,
        client_name: str | ClientName = ClientName.DEFAULT,
        params: dict | None = None,
        json: dict | None = None,
        **kwargs: Any,
    ) -> bytes:
        return await _internal_request(
            method, url, client_name=client_name, params=params, json=json, **kwargs,
        )

    @staticmethod
    def stream(
        method: str,
        url: str,
        *,
        client_name: str | ClientName = ClientName.DEFAULT,
        **kwargs: Any,
    ) -> Any:
        return _internal_stream(method, url, client_name=client_name, **kwargs)

    @classmethod
    async def get(cls, url: str, client_name: Any = ClientName.DEFAULT, **kwargs: Any) -> bytes:
        return await cls.request("GET", url, client_name=client_name, **kwargs)

    @classmethod
    async def post(cls, url: str, client_name: Any = ClientName.DEFAULT, **kwargs: Any) -> bytes:
        return await cls.request("POST", url, client_name=client_name, **kwargs)


class HttpxClientManager:
    """管理多个 httpx.AsyncClient 的容器。"""

    _clients: dict[str, httpx.AsyncClient] = {}
    _configs: dict[str, ClientConfig] = {}
    _lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    def register(cls, name: str | ClientName, config: ClientConfig) -> None:
        cls._configs[str(name)] = config
        logger.debug("Registered HTTP Client config for: %s", name)

    @classmethod
    def is_registered(cls, name: str | ClientName) -> bool:
        return str(name) in cls._configs

    @classmethod
    async def get_client(cls, name: str | ClientName | None = None) -> httpx.AsyncClient:
        """获取或创建客户端实例。"""
        if name is None:
            name = ClientName.DEFAULT

        name_str = str(name)

        if name_str in cls._clients:
            return cls._clients[name_str]

        async with cls._lock:
            if name_str in cls._clients:
                return cls._clients[name_str]

            if not cls.is_registered(name_str):
                if name_str == ClientName.DEFAULT:
                    logger.warning("Default client not registered. Using fallback config.")
                    config = ClientConfig()
                else:
                    raise ValueError(f"HTTP Client '{name_str}' is NOT registered!")
            else:
                config = cls._configs[name_str]

            logger.info(
                "Initializing HTTP Client: %s (BaseURL: %s)", name_str, config.base_url or "None"
            )

            cls._clients[name_str] = httpx.AsyncClient(
                base_url=config.base_url,
                limits=httpx.Limits(
                    max_connections=config.max_connections,
                    max_keepalive_connections=config.max_keepalive,
                ),
                timeout=httpx.Timeout(config.timeout),
                headers=config.headers if isinstance(config.headers, dict) else {},
                follow_redirects=True,
            )

        return cls._clients[name_str]

    @classmethod
    async def close(cls) -> None:
        """关闭所有客户端。"""
        async with cls._lock:
            for name, client in cls._clients.items():
                logger.info("Closing HTTP Client: %s", name)
                await client.aclose()
            cls._clients.clear()
