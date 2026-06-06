"""模型 selector、registry、配置和保留协议测试。"""

import pytest

from src.contracts.runtime import ModelCapabilities
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelToolDeclaration
from src.exceptions import ModelCapabilityError
from src.models.base import ProviderRegistration
from src.models.profiles import ModelProfile
from src.models.protocols import OpenAIChatProtocolAdapter
from src.models.protocols import OpenAIResponsesProtocolAdapter
from src.models.registry import ProfileRegistry
from src.models.registry import ProtocolRegistry
from src.models.registry import ProviderRegistry
from src.models.selector import ModelSelector
from src.models.transport import build_openai_headers
from tests.models.helpers import request


def test_selector_profile_supports_multiple_protocols_for_provider() -> None:
    providers = ProviderRegistry()
    providers.register(ProviderRegistration("openai", "https://api.test/v1", 20, "secret"))
    protocols = ProtocolRegistry()
    protocols.register(OpenAIChatProtocolAdapter())
    protocols.register(OpenAIResponsesProtocolAdapter())
    profiles = ProfileRegistry()
    profiles.register(
        ModelProfile(
            "chat-profile",
            "openai",
            "chat-model",
            ModelProtocol.OPENAI_CHAT,
            ModelCapabilities(),
        )
    )
    profiles.register(
        ModelProfile(
            "responses-profile",
            "openai",
            "responses-model",
            ModelProtocol.OPENAI_RESPONSES,
            ModelCapabilities(),
        )
    )
    selector = ModelSelector(providers=providers, profiles=profiles, protocols=protocols)

    chat = selector.select(request(protocol=ModelProtocol.OPENAI_CHAT, model="chat-model"))
    responses = selector.select(
        request(protocol=ModelProtocol.OPENAI_RESPONSES, model="responses-model")
    )

    assert chat.context.protocol == ModelProtocol.OPENAI_CHAT
    assert responses.context.protocol == ModelProtocol.OPENAI_RESPONSES


def test_selector_context_filters_sensitive_metadata_and_uses_request_timeout() -> None:
    protocol = OpenAIChatProtocolAdapter()
    providers = ProviderRegistry()
    providers.register(ProviderRegistration("openai", "https://api.test/v1", 20, "sk-secret"))
    protocols = ProtocolRegistry()
    protocols.register(protocol)
    profiles = ProfileRegistry()
    profiles.register(
        ModelProfile(
            "chat-profile",
            "openai",
            "gpt-test",
            ModelProtocol.OPENAI_CHAT,
            ModelCapabilities(),
        )
    )
    selector = ModelSelector(providers=providers, profiles=profiles, protocols=protocols)

    selected = selector.select(
        request(
            protocol=ModelProtocol.OPENAI_CHAT,
            timeout_seconds=2.5,
            metadata={
                "trace_id": "trace-1",
                "agent_run_id": "agent-run-1",
                "task_id": "legacy-task-1",
                "prompt": "private",
                "api_key": "sk-secret",
            },
        )
    )

    assert selected.context.effective_timeout_seconds == 2.5
    assert selected.context.safe_metadata == {
        "trace_id": "trace-1",
        "agent_run_id": "agent-run-1",
    }
    assert "secret" not in str(selected.context)
    assert "private" not in str(selected.context)


def test_selector_profile_rejects_unsupported_tool_capability_before_transport() -> None:
    providers = ProviderRegistry()
    providers.register(ProviderRegistration("openai", "https://api.test/v1", 20, "secret"))
    protocols = ProtocolRegistry()
    protocols.register(OpenAIChatProtocolAdapter())
    profiles = ProfileRegistry()
    profiles.register(
        ModelProfile(
            "limited",
            "openai",
            "gpt-test",
            ModelProtocol.OPENAI_CHAT,
            ModelCapabilities(tool_calling=False),
        )
    )
    selector = ModelSelector(providers=providers, profiles=profiles, protocols=protocols)

    with pytest.raises(ModelCapabilityError):
        selector.select(
            request(
                protocol=ModelProtocol.OPENAI_CHAT,
                tools=[ModelToolDeclaration(name="lookup")],
            )
        )


@pytest.mark.parametrize("protocol", [ModelProtocol.ANTHROPIC_MESSAGES, ModelProtocol.CUSTOM])
def test_reserved_anthropic_or_custom_protocol_cannot_execute_unregistered(
    protocol: ModelProtocol,
) -> None:
    providers = ProviderRegistry()
    providers.register(ProviderRegistration("future", "https://never-called.test", 20))
    protocols = ProtocolRegistry()
    profiles = ProfileRegistry()
    profiles.register(ModelProfile("reserved", "future", "model", protocol, ModelCapabilities()))
    selector = ModelSelector(providers=providers, profiles=profiles, protocols=protocols)

    with pytest.raises(ModelCapabilityError, match="模型能力"):
        selector.select(request(provider="future", model="model", protocol=protocol))


def test_auth_config_builds_header_only_at_transport_boundary() -> None:
    headers = build_openai_headers("sk-private")

    assert headers["Authorization"] == "Bearer sk-private"
    assert "sk-private" not in str(request(protocol=ModelProtocol.OPENAI_CHAT))


def test_config_exposes_model_transport_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "4.5")
    from src.core.config import ModelProviderConfig

    config = ModelProviderConfig()

    assert config.OPENAI_TIMEOUT_SECONDS == 4.5
    assert config.OPENAI_BASE_URL.endswith("/v1")


def test_model_profile_context_window_tokens_is_optional() -> None:
    """ModelProfile 可声明 context window，也可保持默认空值。"""
    profile = ModelProfile(
        "openai:gpt-test",
        "openai",
        "gpt-test",
        ModelProtocol.OPENAI_CHAT,
        ModelCapabilities(),
        context_window_tokens=128000,
    )
    default_profile = ModelProfile(
        "mock:mock-model",
        "mock",
        "mock-model",
        ModelProtocol.MOCK,
        ModelCapabilities(),
    )

    assert profile.context_window_tokens == 128000
    assert default_profile.context_window_tokens is None
