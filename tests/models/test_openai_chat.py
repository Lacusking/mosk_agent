"""OpenAI Chat Completions adapter 离线测试。"""

import json

import httpx
import pytest

from src.contracts.runtime import ModelCapabilities
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelStopReason
from src.contracts.runtime import ModelToolDeclaration
from src.exceptions import ModelResponseParseError
from src.models.protocols import OpenAIChatProtocolAdapter
from src.models.providers.openai import OpenAIModelAdapter
from src.models.streaming import ModelStreamReducer
from src.models.transport import HttpModelTransport
from tests.models.helpers import request
from tests.models.helpers import selector


def _selector():
    return selector(
        protocol=ModelProtocol.OPENAI_CHAT,
        adapter=OpenAIChatProtocolAdapter(),
        capabilities=ModelCapabilities(tool_calling=True, streaming=True),
    )


async def test_openai_chat_blocking_text_encodes_request_without_timeout() -> None:
    observed: dict[str, object] = {}

    def handler(raw_request: httpx.Request) -> httpx.Response:
        observed["path"] = raw_request.url.path
        observed["headers"] = raw_request.headers
        observed["timeout"] = raw_request.extensions["timeout"]["read"]
        observed["payload"] = json.loads(raw_request.content)
        return httpx.Response(
            200,
            json={
                "model": "gpt-wire",
                "choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAIModelAdapter(
            selector=_selector(),
            transport_factory=lambda provider: HttpModelTransport(
                base_url=provider.base_url, api_key=provider.api_key or "", client=client
            ),
        )
        response = await adapter.invoke(
            request(protocol=ModelProtocol.OPENAI_CHAT, timeout_seconds=1.25)
        )

    assert observed["path"] == "/v1/chat/completions"
    assert observed["payload"] == {
        "model": "gpt-test",
        "messages": [{"role": "user", "content": "hello"}],
    }
    assert observed["timeout"] == 1.25
    assert response.model == "gpt-wire"
    assert response.content[0].text == "answer"
    assert response.usage is not None and response.usage.total_tokens == 5


async def test_openai_chat_blocking_tool_call_is_normalized() -> None:
    def handler(raw_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {
                                        "name": "lookup",
                                        "arguments": '{"query":"docs"}',
                                    },
                                }
                            ]
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAIModelAdapter(
            selector=_selector(),
            transport_factory=lambda provider: HttpModelTransport(
                base_url=provider.base_url, api_key=provider.api_key or "", client=client
            ),
        )
        response = await adapter.invoke(
            request(
                protocol=ModelProtocol.OPENAI_CHAT,
                tools=[ModelToolDeclaration(name="lookup")],
            )
        )

    assert response.stop_reason == ModelStopReason.TOOL_USE
    assert response.tool_calls[0].arguments == {"query": "docs"}


async def test_openai_chat_streaming_text_reducer_matches_blocking_semantics() -> None:
    body = "\n\n".join(
        [
            'data: {"choices":[{"delta":{"content":"hel"},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"content":"lo"},"finish_reason":"stop"}]}',
            'data: {"choices":[],"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}',
            "data: [DONE]",
        ]
    )

    async def run() -> ModelStreamReducer:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, text=body))
        ) as client:
            adapter = OpenAIModelAdapter(
                selector=_selector(),
                transport_factory=lambda provider: HttpModelTransport(
                    base_url=provider.base_url, api_key=provider.api_key or "", client=client
                ),
            )
            reducer = ModelStreamReducer()
            async for event in adapter.stream(
                request(protocol=ModelProtocol.OPENAI_CHAT, stream=True)
            ):
                reducer.consume(event)
            return reducer

    response = (await run()).response()

    assert response.content[0].text == "hello"
    assert response.stop_reason == ModelStopReason.COMPLETED
    assert response.usage is not None and response.usage.total_tokens == 3


async def test_openai_chat_streaming_tool_arguments_complete_only_after_valid_json() -> None:
    body = "\n\n".join(
        [
            'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call-1","function":{"name":"lookup","arguments":"{\\"query\\":"}}]},"finish_reason":null}]}',
            'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\\"docs\\"}"}}]},"finish_reason":"tool_calls"}]}',
            "data: [DONE]",
        ]
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text=body))
    ) as client:
        adapter = OpenAIModelAdapter(
            selector=_selector(),
            transport_factory=lambda provider: HttpModelTransport(
                base_url=provider.base_url, api_key=provider.api_key or "", client=client
            ),
        )
        reducer = ModelStreamReducer()
        async for event in adapter.stream(request(protocol=ModelProtocol.OPENAI_CHAT, stream=True)):
            reducer.consume(event)

    response = reducer.response()
    assert response.stop_reason == ModelStopReason.TOOL_USE
    assert response.tool_calls[0].arguments == {"query": "docs"}


async def test_openai_chat_streaming_reducer_rejects_invalid_completed_tool_json() -> None:
    body = "\n\n".join(
        [
            "data: "
            + json.dumps(
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call-1",
                                        "function": {"name": "lookup", "arguments": "{"},
                                    }
                                ]
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                }
            ),
            "data: [DONE]",
        ]
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text=body))
    ) as client:
        adapter = OpenAIModelAdapter(
            selector=_selector(),
            transport_factory=lambda provider: HttpModelTransport(
                base_url=provider.base_url, api_key=provider.api_key or "", client=client
            ),
        )
        with pytest.raises(ModelResponseParseError):
            async for _ in adapter.stream(request(protocol=ModelProtocol.OPENAI_CHAT, stream=True)):
                pass
