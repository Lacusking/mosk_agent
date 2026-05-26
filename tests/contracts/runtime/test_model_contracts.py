"""模型请求与响应公开契约测试。"""

import pytest
from pydantic import ValidationError

from src.contracts.runtime import ModelMessage
from src.contracts.runtime import ModelOptions
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelRequest
from src.contracts.runtime import ModelResponse
from src.contracts.runtime import ModelResponseStatus
from src.contracts.runtime import ModelRole
from src.contracts.runtime import ModelStopReason
from src.contracts.runtime import ModelToolCall
from src.contracts.runtime import ModelToolChoice
from src.contracts.runtime import ModelToolChoiceMode
from src.contracts.runtime import ModelToolDeclaration
from src.contracts.runtime import TextContentBlock


def _request(**changes: object) -> ModelRequest:
    values: dict[str, object] = {
        "invocation_id": "invoke-1",
        "provider": "openai",
        "model": "gpt-test",
        "protocol": ModelProtocol.OPENAI_RESPONSES,
        "messages": [
            ModelMessage(
                role=ModelRole.USER,
                content=[TextContentBlock(text="hello")],
            )
        ],
    }
    values.update(changes)
    return ModelRequest.model_validate(values)


def _response(**changes: object) -> ModelResponse:
    values: dict[str, object] = {
        "invocation_id": "invoke-1",
        "provider": "openai",
        "model": "gpt-test",
        "protocol": ModelProtocol.OPENAI_RESPONSES,
        "content": [TextContentBlock(text="answer")],
        "status": ModelResponseStatus.COMPLETED,
        "stop_reason": ModelStopReason.COMPLETED,
    }
    values.update(changes)
    return ModelResponse.model_validate(values)


class TestModelRequest:
    def test_serializes_standard_input_without_wire_payload(self) -> None:
        request = _request(
            tools=[
                ModelToolDeclaration(
                    name="lookup",
                    parameters_schema={"type": "object"},
                )
            ],
            tool_choice=ModelToolChoice(mode=ModelToolChoiceMode.NAMED, name="lookup"),
            options=ModelOptions(max_output_tokens=256),
            timeout_seconds=4.5,
            stream=True,
        )

        serialized = request.model_dump(mode="json")

        assert serialized["messages"][0]["content"][0] == {"kind": "text", "text": "hello"}
        assert serialized["timeout_seconds"] == 4.5
        assert "timeout_seconds" not in serialized["options"]
        assert "wire_payload" not in serialized

    @pytest.mark.parametrize("timeout_seconds", [0, -1])
    def test_rejects_non_positive_invocation_timeout(self, timeout_seconds: float) -> None:
        with pytest.raises(ValidationError, match="timeout_seconds"):
            _request(timeout_seconds=timeout_seconds)

    def test_rejects_named_tool_choice_without_declaration(self) -> None:
        with pytest.raises(ValidationError, match="已声明工具"):
            _request(tool_choice=ModelToolChoice(mode=ModelToolChoiceMode.NAMED, name="missing"))

    def test_rejects_empty_message_content(self) -> None:
        with pytest.raises(ValidationError, match="content"):
            _request(messages=[{"role": "user", "content": []}])


class TestModelResponse:
    def test_accepts_completed_tool_use_response(self) -> None:
        response = _response(
            content=[],
            tool_calls=[ModelToolCall(call_id="call-1", name="lookup", arguments={"q": "x"})],
            stop_reason=ModelStopReason.TOOL_USE,
        )

        assert response.status == ModelResponseStatus.COMPLETED
        assert response.tool_calls[0].arguments == {"q": "x"}

    @pytest.mark.parametrize(
        ("status", "stop_reason"),
        [
            (ModelResponseStatus.COMPLETED, ModelStopReason.MAX_TOKENS),
            (ModelResponseStatus.COMPLETED, ModelStopReason.REFUSED),
            (ModelResponseStatus.REFUSED, ModelStopReason.TOOL_USE),
            (ModelResponseStatus.INCOMPLETE, ModelStopReason.COMPLETED),
        ],
    )
    def test_rejects_illegal_status_stop_reason_mapping(
        self, status: ModelResponseStatus, stop_reason: ModelStopReason
    ) -> None:
        with pytest.raises(ValidationError, match="组合非法"):
            _response(status=status, stop_reason=stop_reason)

    def test_rejects_tool_use_without_completed_tool_call(self) -> None:
        with pytest.raises(ValidationError, match="必须包含已完成工具调用"):
            _response(stop_reason=ModelStopReason.TOOL_USE)
