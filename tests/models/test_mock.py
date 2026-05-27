"""Mock provider 执行路径测试。"""

import pytest

from src.contracts.runtime import ModelCapabilities
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelStopReason
from src.exceptions import ModelUnavailableError
from src.models.providers.mock import MockModelAdapter
from src.models.providers.mock import MockProtocolAdapter
from src.models.streaming import ModelStreamReducer
from tests.models.helpers import request
from tests.models.helpers import selector


def _adapter() -> MockModelAdapter:
    selected = selector(
        protocol=ModelProtocol.MOCK,
        adapter=MockProtocolAdapter(),
        provider="mock",
        model="mock-model",
        capabilities=ModelCapabilities(tool_calling=True, streaming=True),
    )
    return MockModelAdapter(selector=selected)


async def test_mock_blocking_returns_deterministic_standard_response() -> None:
    response = await _adapter().invoke(
        request(protocol=ModelProtocol.MOCK, provider="mock", model="mock-model")
    )

    assert response.content[0].text == "mock response"
    assert response.usage is not None
    assert response.stop_reason == ModelStopReason.COMPLETED


async def test_mock_blocking_tool_response_returns_normalized_intent() -> None:
    response = await _adapter().invoke(
        request(
            protocol=ModelProtocol.MOCK,
            provider="mock",
            model="mock-model",
            metadata={"mode": "tool"},
        )
    )

    assert response.stop_reason == ModelStopReason.TOOL_USE
    assert response.tool_calls[0].name == "lookup"


async def test_mock_streaming_text_reduces_to_final_response() -> None:
    reducer = ModelStreamReducer()

    async for event in _adapter().stream(
        request(
            protocol=ModelProtocol.MOCK,
            provider="mock",
            model="mock-model",
            stream=True,
        )
    ):
        reducer.consume(event)

    assert reducer.response().content[0].text == "mock response"


async def test_mock_streaming_tool_response_reduces_to_tool_use() -> None:
    reducer = ModelStreamReducer()
    stream_request = request(
        protocol=ModelProtocol.MOCK,
        provider="mock",
        model="mock-model",
        stream=True,
        metadata={"mode": "tool"},
    )

    async for event in _adapter().stream(stream_request):
        reducer.consume(event)
    response = reducer.response()

    assert response.stop_reason == ModelStopReason.TOOL_USE
    assert response.tool_calls[0].arguments == {"query": "mock"}


async def test_mock_configured_failure_is_standard_model_error() -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        await _adapter().invoke(
            request(
                protocol=ModelProtocol.MOCK,
                provider="mock",
                model="mock-model",
                metadata={"mode": "fail"},
            )
        )

    assert raised.value.retryable is True
