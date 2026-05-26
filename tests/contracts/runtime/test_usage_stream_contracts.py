"""模型 usage 与统一流事件契约测试。"""

import pytest
from pydantic import ValidationError

from src.contracts.runtime import ContentDeltaPayload
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelResponseStatus
from src.contracts.runtime import ModelStopReason
from src.contracts.runtime import ModelStreamEvent
from src.contracts.runtime import ModelStreamEventType
from src.contracts.runtime import ModelUsage
from src.contracts.runtime import ResponseCompletedPayload
from src.contracts.runtime import ToolCallDeltaPayload
from src.contracts.runtime import UsageUpdatedPayload


class TestModelUsage:
    def test_preserves_missing_dimensions_as_not_provided(self) -> None:
        usage = ModelUsage(input_tokens=7, provider_details={"source": "provider"})

        serialized = usage.model_dump(exclude_none=True)

        assert usage.output_tokens is None
        assert usage.reasoning_tokens is None
        assert "output_tokens" not in serialized
        assert "reasoning_tokens" not in serialized

    def test_accepts_phase_specific_token_dimensions(self) -> None:
        usage = ModelUsage(
            input_tokens=20,
            output_tokens=8,
            total_tokens=28,
            cached_input_tokens=10,
            cache_creation_input_tokens=3,
            reasoning_tokens=2,
        )

        assert usage.cached_input_tokens == 10
        assert usage.reasoning_tokens == 2

    def test_rejects_negative_token_count(self) -> None:
        with pytest.raises(ValidationError, match="input_tokens"):
            ModelUsage(input_tokens=-1)


class TestModelStreamEvent:
    def test_serializes_typed_text_and_usage_events(self) -> None:
        delta = ModelStreamEvent(
            invocation_id="invoke-1",
            event_type=ModelStreamEventType.CONTENT_DELTA,
            sequence=1,
            payload=ContentDeltaPayload(delta="hi"),
        )
        usage = ModelStreamEvent(
            invocation_id="invoke-1",
            event_type=ModelStreamEventType.USAGE_UPDATED,
            sequence=2,
            payload=UsageUpdatedPayload(usage=ModelUsage(output_tokens=1)),
        )

        assert delta.model_dump(mode="json")["payload"] == {"delta": "hi"}
        assert usage.payload.usage.output_tokens == 1

    def test_rejects_event_type_with_wrong_payload(self) -> None:
        with pytest.raises(ValidationError, match="payload 类型不匹配"):
            ModelStreamEvent(
                invocation_id="invoke-1",
                event_type=ModelStreamEventType.CONTENT_DELTA,
                sequence=1,
                payload=ToolCallDeltaPayload(call_id="call-1", arguments_delta='{"q":'),
            )

    def test_completion_payload_rejects_invalid_response_mapping(self) -> None:
        with pytest.raises(ValidationError, match="组合非法"):
            ResponseCompletedPayload(
                status=ModelResponseStatus.COMPLETED,
                stop_reason=ModelStopReason.REFUSED,
            )

    def test_started_payload_requires_protocol_identity(self) -> None:
        event = ModelStreamEvent.model_validate(
            {
                "invocation_id": "invoke-1",
                "event_type": "invocation_started",
                "sequence": 0,
                "payload": {
                    "provider": "openai",
                    "model": "gpt-test",
                    "protocol": ModelProtocol.OPENAI_CHAT,
                },
            }
        )

        assert event.payload.protocol == ModelProtocol.OPENAI_CHAT
