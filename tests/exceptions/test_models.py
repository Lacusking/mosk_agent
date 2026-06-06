"""模型专属结构化异常测试。"""

import pytest

from src.exceptions import ModelAuthenticationError
from src.exceptions import ModelCapabilityError
from src.exceptions import ModelContextLengthError
from src.exceptions import ModelError
from src.exceptions import ModelRateLimitError
from src.exceptions import ModelStreamInterruptedError
from src.exceptions import ModelTimeoutError


class TestModelErrors:
    def test_model_error_exposes_runtime_decision_data(self) -> None:
        err = ModelError(
            provider="openai",
            model="gpt-test",
            protocol="openai_responses",
            operation="invoke",
        )

        assert err.data == {
            "error_type": "ModelError",
            "retryable": False,
            "fallback_allowed": False,
            "provider": "openai",
            "model": "gpt-test",
            "protocol": "openai_responses",
            "operation": "invoke",
        }

    def test_rate_limit_is_retryable_and_preserves_retry_after(self) -> None:
        err = ModelRateLimitError(
            provider="openai",
            provider_status_code=429,
            retry_after_seconds=2.5,
        )

        assert err.retryable is True
        assert err.fallback_allowed is True
        assert err.data["retry_after_seconds"] == 2.5
        assert err.data["provider_status_code"] == 429

    def test_timeout_is_retryable(self) -> None:
        err = ModelTimeoutError(operation="stream")

        assert err.retryable is True
        assert err.fallback_allowed is True

    @pytest.mark.parametrize("error_cls", [ModelAuthenticationError, ModelCapabilityError])
    def test_non_retryable_errors_are_explicit(self, error_cls: type[ModelError]) -> None:
        err = error_cls(provider="openai")

        assert err.retryable is False
        assert err.fallback_allowed is False

    def test_stream_interruption_exposes_partial_state(self) -> None:
        err = ModelStreamInterruptedError(
            operation="stream",
            partial_content_received=True,
            pending_tool_call=True,
        )

        assert err.data["details"]["partial_content_received"] is True
        assert err.data["details"]["pending_tool_call"] is True

    def test_context_length_error_is_retryable_with_provider_tokens(self) -> None:
        err = ModelContextLengthError(
            provider="openai",
            model="gpt-test",
            protocol="openai_chat",
            prompt_tokens=150000,
            max_context_tokens=128000,
        )

        assert err.retryable is True
        assert err.data["details"]["provider_reported_tokens"] == {
            "prompt_tokens": 150000,
            "max_context_tokens": 128000,
        }

    def test_sensitive_data_is_redacted_recursively(self) -> None:
        err = ModelAuthenticationError(
            provider="openai",
            data={
                "api_key": "sk-secret",
                "authorization": "Bearer secret",
                "nested": {"raw_request": {"messages": ["private"]}},
                "request_id": "safe-id",
            },
        )
        serialized = str(err.to_dict())

        assert "sk-secret" not in serialized
        assert "Bearer secret" not in serialized
        assert "private" not in serialized
        assert err.data["details"]["request_id"] == "safe-id"
        assert err.data["details"]["api_key"] == "[REDACTED]"

    def test_negative_retry_after_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="不能小于零"):
            ModelRateLimitError(retry_after_seconds=-1)
