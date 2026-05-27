"""模型错误映射、安全边界与 lifecycle 互操作测试。"""

import httpx
import pytest

from src.contracts.runtime import ModelInvocationCompletedPayload
from src.contracts.runtime import ModelInvocationFailedPayload
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelResponseStatus
from src.contracts.runtime import ModelStopReason
from src.contracts.runtime import ModelUsage
from src.exceptions import ModelAuthenticationError
from src.exceptions import ModelAuthorizationError
from src.exceptions import ModelInvalidRequestError
from src.exceptions import ModelRateLimitError
from src.exceptions import ModelStreamInterruptedError
from src.exceptions import ModelTimeoutError
from src.exceptions import ModelUnavailableError
from src.models.parsers.errors import map_provider_error
from src.models.protocols import OpenAIChatProtocolAdapter
from tests.models.helpers import request
from tests.models.helpers import selector


def _context():
    return (
        selector(
            protocol=ModelProtocol.OPENAI_CHAT,
            adapter=OpenAIChatProtocolAdapter(),
        )
        .select(request(protocol=ModelProtocol.OPENAI_CHAT))
        .context
    )


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, ModelAuthenticationError),
        (403, ModelAuthorizationError),
        (400, ModelInvalidRequestError),
        (429, ModelRateLimitError),
        (503, ModelUnavailableError),
    ],
)
def test_openai_error_mapping_exposes_decision_fields_without_wire_body(
    status: int,
    error_type: type,
) -> None:
    response = httpx.Response(
        status,
        json={"error": {"code": "safe_code", "message": "authorization Bearer sk-private"}},
        headers={"retry-after": "2"},
        request=httpx.Request("POST", "https://provider.test/v1/responses"),
    )
    original = httpx.HTTPStatusError("raw secret", request=response.request, response=response)

    error = map_provider_error(original, _context(), operation="invoke")

    assert isinstance(error, error_type)
    serialized = str(error.to_dict())
    assert "safe_code" in serialized
    assert "sk-private" not in serialized
    if status == 429:
        assert error.retryable is True
        assert error.retry_after_seconds == 2


def test_openai_error_timeout_maps_to_retryable_model_timeout() -> None:
    original = httpx.ReadTimeout(
        "timeout", request=httpx.Request("POST", "https://provider.test/v1/responses")
    )

    error = map_provider_error(original, _context(), operation="invoke")

    assert isinstance(error, ModelTimeoutError)
    assert error.retryable is True


def test_openai_error_interrupted_stream_preserves_partial_state() -> None:
    original = httpx.ReadError(
        "closed", request=httpx.Request("POST", "https://provider.test/v1/responses")
    )

    error = map_provider_error(
        original,
        _context(),
        operation="stream",
        partial_content_received=True,
        pending_tool_call=True,
    )

    assert isinstance(error, ModelStreamInterruptedError)
    assert error.data["details"]["partial_content_received"] is True
    assert error.data["details"]["pending_tool_call"] is True


def test_lifecycle_completed_payload_accepts_normalized_tool_success() -> None:
    payload = ModelInvocationCompletedPayload(
        invocation_id="invoke-1",
        provider="mock",
        model="mock-model",
        protocol=ModelProtocol.MOCK,
        status=ModelResponseStatus.COMPLETED,
        stop_reason=ModelStopReason.TOOL_USE,
        usage=ModelUsage(input_tokens=1, output_tokens=2, total_tokens=3),
        latency_ms=1,
        tool_call_count=1,
    )

    assert payload.stop_reason == ModelStopReason.TOOL_USE


def test_lifecycle_failure_payload_uses_model_error_retry_semantics() -> None:
    error = ModelRateLimitError(
        provider="openai",
        model="gpt-test",
        protocol=ModelProtocol.OPENAI_CHAT.value,
        provider_status_code=429,
    )
    payload = ModelInvocationFailedPayload(
        invocation_id="invoke-1",
        provider=error.provider,
        model=error.model,
        protocol=ModelProtocol.OPENAI_CHAT,
        error_type=type(error).__name__,
        retryable=error.retryable,
        fallback_allowed=error.fallback_allowed,
        provider_status_code=error.provider_status_code,
        latency_ms=3,
    )

    assert payload.retryable is True
    assert "authorization" not in str(payload.model_dump())
