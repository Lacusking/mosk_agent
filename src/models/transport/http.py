"""基于 httpx 的模型 HTTP 与 SSE transport。"""

import json
from collections.abc import AsyncIterator

import httpx

from src.models.transport.auth import build_openai_headers


class HttpModelTransport:
    """将 OpenAI endpoint、认证头与调用级 timeout 限制在 transport 边界。"""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._headers = build_openai_headers(api_key)
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(base_url=base_url)
        self._base_url = base_url.rstrip("/")

    async def post_json(
        self,
        path: str,
        payload: dict[str, object],
        *,
        timeout_seconds: float,
    ) -> dict[str, object]:
        """发送 JSON 模型请求。

        Args:
            path: provider endpoint 路径。
            payload: protocol 已生成的 payload。
            timeout_seconds: 单次 invocation 的有效 timeout。

        Returns:
            解析后的 JSON object。
        """
        response = await self._client.post(
            f"{self._base_url}{path}",
            headers=self._headers,
            json=payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        parsed = response.json()
        if not isinstance(parsed, dict):
            raise ValueError("provider JSON 响应必须为 object")
        return parsed

    async def stream_json(
        self,
        path: str,
        payload: dict[str, object],
        *,
        timeout_seconds: float,
    ) -> AsyncIterator[dict[str, object]]:
        """读取 SSE 中的 JSON data events。

        Args:
            path: provider endpoint 路径。
            payload: protocol 已生成的 payload。
            timeout_seconds: 单次 invocation 的有效 timeout。

        Yields:
            每个 provider SSE data 的 JSON object。
        """
        async with self._client.stream(
            "POST",
            f"{self._base_url}{path}",
            headers=self._headers,
            json=payload,
            timeout=timeout_seconds,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    yield parsed

    async def close(self) -> None:
        """关闭由本 transport 创建的 HTTP client。"""
        if self._owns_client:
            await self._client.aclose()
