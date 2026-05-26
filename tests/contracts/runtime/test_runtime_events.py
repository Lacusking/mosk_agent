"""模型生命周期 runtime event 契约测试。"""

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.contracts.runtime import ModelInvocationCompletedPayload
from src.contracts.runtime import ModelInvocationFailedPayload
from src.contracts.runtime import ModelInvocationStartedPayload
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelResponseStatus
from src.contracts.runtime import ModelStopReason
from src.contracts.runtime import ModelToolCallsProducedPayload
from src.contracts.runtime import ModelUsage
from src.contracts.runtime import ProducedToolCallFact
from src.contracts.runtime import RuntimeActorType
from src.contracts.runtime import RuntimeEvent
from src.contracts.runtime import RuntimeEventType
from src.events import RuntimeEvent as DiscoverableRuntimeEvent


def _event(
    *,
    event_type: RuntimeEventType,
    payload: object,
) -> RuntimeEvent:
    values: dict[str, object] = {
        "event_id": "event-1",
        "event_type": event_type,
        "task_id": "task-1",
        "step_id": "step-1",
        "session_id": "session-1",
        "trace_id": "trace-1",
        "span_id": "span-1",
        "actor_type": RuntimeActorType.RUNTIME,
        "payload": payload,
        "created_at": datetime(2026, 5, 26, 12, tzinfo=UTC),
    }
    return RuntimeEvent.model_validate(values)


class TestRuntimeEvent:
    def test_event_serializes_started_lifecycle_envelope(self) -> None:
        event = _event(
            event_type=RuntimeEventType.MODEL_INVOCATION_STARTED,
            payload=ModelInvocationStartedPayload(
                invocation_id="invoke-1",
                provider="openai",
                model="gpt-test",
                protocol=ModelProtocol.OPENAI_RESPONSES,
                profile="gpt-test-responses",
                streaming=True,
            ),
        )

        serialized = event.model_dump(mode="json")

        assert serialized["event_type"] == "model_invocation_started"
        assert serialized["event_version"] == 1
        assert serialized["trace_id"] == "trace-1"
        assert serialized["payload"]["profile"] == "gpt-test-responses"
        assert DiscoverableRuntimeEvent is RuntimeEvent

    def test_event_rejects_mismatched_lifecycle_payload(self) -> None:
        with pytest.raises(ValidationError, match="payload 类型不匹配"):
            _event(
                event_type=RuntimeEventType.MODEL_INVOCATION_STARTED,
                payload=ModelInvocationFailedPayload(
                    invocation_id="invoke-1",
                    error_type="ModelTimeoutError",
                    retryable=True,
                    fallback_allowed=True,
                    latency_ms=200,
                ),
            )

    def test_event_rejects_completed_payload_without_usage(self) -> None:
        with pytest.raises(ValidationError, match="usage"):
            ModelInvocationCompletedPayload.model_validate(
                {
                    "invocation_id": "invoke-1",
                    "provider": "openai",
                    "model": "gpt-test",
                    "protocol": "openai_responses",
                    "status": "completed",
                    "stop_reason": "completed",
                    "latency_ms": 80,
                    "tool_call_count": 0,
                }
            )

    def test_event_rejects_naive_created_at(self) -> None:
        with pytest.raises(ValidationError, match="时区"):
            RuntimeEvent.model_validate(
                {
                    "event_id": "event-1",
                    "event_type": RuntimeEventType.MODEL_INVOCATION_STARTED,
                    "trace_id": "trace-1",
                    "span_id": "span-1",
                    "actor_type": RuntimeActorType.RUNTIME,
                    "created_at": datetime(2026, 5, 26, 12),
                    "payload": ModelInvocationStartedPayload(
                        invocation_id="invoke-1",
                        provider="openai",
                        model="gpt-test",
                        protocol=ModelProtocol.OPENAI_RESPONSES,
                        profile="profile-1",
                        streaming=False,
                    ),
                }
            )


class TestModelLifecyclePayloads:
    def test_event_lifecycle_tool_use_is_successful_completion(self) -> None:
        payload = ModelInvocationCompletedPayload(
            invocation_id="invoke-1",
            provider="openai",
            model="gpt-test",
            protocol=ModelProtocol.OPENAI_RESPONSES,
            status=ModelResponseStatus.COMPLETED,
            stop_reason=ModelStopReason.TOOL_USE,
            usage=ModelUsage(input_tokens=4, output_tokens=2, total_tokens=6),
            latency_ms=31.5,
            tool_call_count=1,
        )

        assert payload.status == ModelResponseStatus.COMPLETED
        assert payload.stop_reason == ModelStopReason.TOOL_USE

    def test_event_lifecycle_failure_exposes_decision_fields(self) -> None:
        payload = ModelInvocationFailedPayload(
            invocation_id="invoke-1",
            provider="openai",
            model="gpt-test",
            protocol=ModelProtocol.OPENAI_CHAT,
            error_type="ModelRateLimitError",
            retryable=True,
            fallback_allowed=True,
            provider_status_code=429,
            latency_ms=12,
        )

        assert payload.retryable is True
        assert payload.provider_status_code == 429


class TestEventSecurity:
    def test_event_security_completed_payload_contains_no_content_or_wire_body(self) -> None:
        event = _event(
            event_type=RuntimeEventType.MODEL_INVOCATION_COMPLETED,
            payload=ModelInvocationCompletedPayload(
                invocation_id="invoke-1",
                provider="openai",
                model="gpt-test",
                protocol=ModelProtocol.OPENAI_RESPONSES,
                status=ModelResponseStatus.COMPLETED,
                stop_reason=ModelStopReason.COMPLETED,
                usage=ModelUsage(input_tokens=2, output_tokens=1),
                latency_ms=20,
                tool_call_count=0,
            ),
        )

        serialized = event.model_dump(mode="json")
        as_text = str(serialized)

        assert "content" not in serialized["payload"]
        assert "raw_request" not in as_text
        assert "raw_response" not in as_text
        assert "prompt" not in as_text

    def test_event_security_tool_intent_does_not_accept_arguments(self) -> None:
        payload = ModelToolCallsProducedPayload(
            invocation_id="invoke-1",
            calls=[
                ProducedToolCallFact(
                    call_id="call-1",
                    name="lookup",
                    arguments_validated=True,
                )
            ],
        )

        assert payload.model_dump() == {
            "invocation_id": "invoke-1",
            "calls": [
                {
                    "call_id": "call-1",
                    "name": "lookup",
                    "arguments_validated": True,
                }
            ],
        }

        with pytest.raises(ValidationError, match="arguments"):
            ProducedToolCallFact.model_validate(
                {
                    "call_id": "call-1",
                    "name": "lookup",
                    "arguments_validated": True,
                    "arguments": {"api_key": "secret"},
                }
            )
