"""OpenAI Responses adapter 离线测试。"""

import json

import httpx

from src.contracts.runtime import ModelCapabilities
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelResponseStatus
from src.contracts.runtime import ModelStopReason
from src.models.protocols import OpenAIResponsesProtocolAdapter
from src.models.providers.openai import OpenAIModelAdapter
from src.models.streaming import ModelStreamReducer
from src.models.transport import HttpModelTransport
from tests.models.helpers import request
from tests.models.helpers import selector


def _selector():
    return selector(
        protocol=ModelProtocol.OPENAI_RESPONSES,
        adapter=OpenAIResponsesProtocolAdapter(),
        capabilities=ModelCapabilities(tool_calling=True, streaming=True),
    )


async def test_openai_responses_blocking_text_parses_output_items() -> None:
    observed: dict[str, object] = {}

    def handler(raw_request: httpx.Request) -> httpx.Response:
        observed["payload"] = json.loads(raw_request.content)
        return httpx.Response(
            200,
            json={
                "model": "gpt-wire",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "answer"}],
                    }
                ],
                "usage": {"input_tokens": 3, "output_tokens": 2, "total_tokens": 5},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAIModelAdapter(
            selector=_selector(),
            transport_factory=lambda provider: HttpModelTransport(
                base_url=provider.base_url, api_key=provider.api_key or "", client=client
            ),
        )
        response = await adapter.invoke(request(protocol=ModelProtocol.OPENAI_RESPONSES))

    assert observed["payload"] == {
        "model": "gpt-test",
        "input": [{"role": "user", "content": [{"type": "input_text", "text": "hello"}]}],
    }
    assert response.content[0].text == "answer"
    assert response.stop_reason == ModelStopReason.COMPLETED


async def test_openai_responses_blocking_function_and_refusal_semantics() -> None:
    responses = [
        {
            "status": "completed",
            "output": [
                {
                    "type": "function_call",
                    "call_id": "call-1",
                    "name": "lookup",
                    "arguments": '{"query":"docs"}',
                }
            ],
        },
        {
            "status": "completed",
            "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}],
        },
        {
            "status": "incomplete",
            "incomplete_details": {"reason": "max_output_tokens"},
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "partial"}],
                }
            ],
        },
    ]

    def handler(raw_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=responses.pop(0))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAIModelAdapter(
            selector=_selector(),
            transport_factory=lambda provider: HttpModelTransport(
                base_url=provider.base_url, api_key=provider.api_key or "", client=client
            ),
        )
        tool = await adapter.invoke(request(protocol=ModelProtocol.OPENAI_RESPONSES))
        refusal = await adapter.invoke(request(protocol=ModelProtocol.OPENAI_RESPONSES))
        incomplete = await adapter.invoke(request(protocol=ModelProtocol.OPENAI_RESPONSES))

    assert tool.stop_reason == ModelStopReason.TOOL_USE
    assert tool.tool_calls[0].arguments == {"query": "docs"}
    assert refusal.status == ModelResponseStatus.REFUSED
    assert refusal.stop_reason == ModelStopReason.REFUSED
    assert incomplete.status == ModelResponseStatus.INCOMPLETE
    assert incomplete.stop_reason == ModelStopReason.MAX_TOKENS


async def test_openai_responses_streaming_text_reducer_preserves_usage() -> None:
    completed = {
        "model": "gpt-test",
        "status": "completed",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": "hello"}]}],
        "usage": {"input_tokens": 2, "output_tokens": 1, "total_tokens": 3},
    }
    body = "\n\n".join(
        [
            'data: {"type":"response.created"}',
            'data: {"type":"response.output_text.delta","delta":"hel"}',
            'data: {"type":"response.output_text.delta","delta":"lo"}',
            f"data: {json.dumps({'type': 'response.completed', 'response': completed})}",
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
        async for event in adapter.stream(
            request(protocol=ModelProtocol.OPENAI_RESPONSES, stream=True)
        ):
            reducer.consume(event)

    response = reducer.response()
    assert response.content[0].text == "hello"
    assert response.usage is not None and response.usage.total_tokens == 3


async def test_openai_responses_streaming_function_arguments_reduce_to_tool_use() -> None:
    completed = {
        "status": "completed",
        "output": [
            {
                "type": "function_call",
                "call_id": "call-1",
                "name": "lookup",
                "arguments": '{"query":"docs"}',
            }
        ],
    }
    body = "\n\n".join(
        [
            'data: {"type":"response.output_item.added","item":{"type":"function_call","call_id":"call-1","name":"lookup"}}',
            'data: {"type":"response.function_call_arguments.delta","call_id":"call-1","delta":"{\\"query\\":"}',
            'data: {"type":"response.function_call_arguments.done","call_id":"call-1","arguments":"{\\"query\\":\\"docs\\"}"}',
            f"data: {json.dumps({'type': 'response.completed', 'response': completed})}",
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
        async for event in adapter.stream(
            request(protocol=ModelProtocol.OPENAI_RESPONSES, stream=True)
        ):
            reducer.consume(event)

    response = reducer.response()
    assert response.stop_reason == ModelStopReason.TOOL_USE
    assert response.tool_calls[0].arguments == {"query": "docs"}
