"""Runtime 依赖工厂。"""

from dataclasses import dataclass

from src.contracts.runtime import ModelCapabilities
from src.contracts.runtime import ModelProtocol
from src.core.config import ModelProviderConfig
from src.core.config import settings
from src.exceptions import ModelConfigurationError
from src.models import ModelProfile
from src.models import ModelSelector
from src.models import OpenAIModelAdapter
from src.models import ProfileRegistry
from src.models import ProtocolAdapter
from src.models import ProtocolRegistry
from src.models import ProviderRegistration
from src.models import ProviderRegistry
from src.models.protocols import OpenAIChatProtocolAdapter
from src.models.protocols import OpenAIResponsesProtocolAdapter
from src.models.providers.mock import MockModelAdapter
from src.models.providers.mock import MockProtocolAdapter
from src.runtime.model_invoker import RuntimeModelInvoker


@dataclass(frozen=True)
class RuntimeModelTarget:
    """AgentRuntimeKernel 默认模型目标。"""

    provider: str
    model: str
    protocol: ModelProtocol
    invoker: RuntimeModelInvoker


@dataclass(frozen=True)
class RuntimeModelSelection:
    """单次 AgentRun 的模型选择覆盖项。"""

    provider: str | None = None
    model: str | None = None
    protocol: ModelProtocol | None = None
    context_window_tokens: int | None = None


@dataclass(frozen=True)
class _ResolvedRuntimeModel:
    provider: str
    model: str
    protocol: ModelProtocol
    context_window_tokens: int | None


def build_runtime_model_target(
    config: ModelProviderConfig | None = None,
    selection: RuntimeModelSelection | None = None,
) -> RuntimeModelTarget:
    """根据配置构造 runtime 模型调用目标。"""
    model_config = config or settings.models
    resolved = _resolve_runtime_model(model_config, selection)
    if resolved.provider == "mock":
        return RuntimeModelTarget(
            provider="mock",
            model=resolved.model,
            protocol=ModelProtocol.MOCK,
            invoker=build_mock_model_invoker(model_config, selection),
        )
    if resolved.provider == "openai":
        return RuntimeModelTarget(
            provider="openai",
            model=resolved.model,
            protocol=resolved.protocol,
            invoker=build_openai_model_invoker(model_config, selection),
        )
    raise ModelConfigurationError(
        provider=resolved.provider,
        model=resolved.model,
        operation="runtime_factory",
        data={"reason": "unsupported_runtime_model_provider"},
    )


def build_runtime_model_invoker(
    config: ModelProviderConfig | None = None,
    selection: RuntimeModelSelection | None = None,
) -> RuntimeModelInvoker:
    """根据配置构造 runtime 模型 invoker。"""
    return build_runtime_model_target(config, selection).invoker


def build_mock_model_invoker(
    config: ModelProviderConfig | None = None,
    selection: RuntimeModelSelection | None = None,
) -> RuntimeModelInvoker:
    """构造 mock 模型 invoker。"""
    model_config = config or settings.models
    resolved = _resolve_runtime_model(model_config, selection)
    selector = _selector(
        provider=ProviderRegistration(
            name="mock",
            base_url="mock://local",
            default_timeout_seconds=model_config.MOCK_TIMEOUT_SECONDS,
        ),
        protocol_adapters=[MockProtocolAdapter()],
        profile=ModelProfile(
            name="mock-model-runtime",
            provider="mock",
            model=resolved.model,
            protocol=ModelProtocol.MOCK,
            capabilities=ModelCapabilities(tool_calling=True, streaming=True),
            context_window_tokens=resolved.context_window_tokens,
        ),
    )
    return RuntimeModelInvoker(MockModelAdapter(selector=selector))


def build_openai_model_invoker(
    config: ModelProviderConfig | None = None,
    selection: RuntimeModelSelection | None = None,
) -> RuntimeModelInvoker:
    """构造 OpenAI 模型 invoker。"""
    model_config = config or settings.models
    resolved = _resolve_runtime_model(model_config, selection)
    if not model_config.OPENAI_API_KEY:
        raise ModelConfigurationError(
            provider="openai",
            model=resolved.model,
            operation="runtime_factory",
            data={"reason": "missing_openai_api_key"},
        )
    selector = _selector(
        provider=ProviderRegistration(
            name="openai",
            base_url=model_config.OPENAI_BASE_URL,
            default_timeout_seconds=model_config.OPENAI_TIMEOUT_SECONDS,
            api_key=model_config.OPENAI_API_KEY,
        ),
        protocol_adapters=[
            OpenAIChatProtocolAdapter(),
            OpenAIResponsesProtocolAdapter(),
        ],
        profile=ModelProfile(
            name=f"openai-{resolved.model}-{resolved.protocol.value}",
            provider="openai",
            model=resolved.model,
            protocol=resolved.protocol,
            capabilities=ModelCapabilities(
                tool_calling=True,
                streaming=True,
                structured_output=True,
                vision=True,
            ),
            context_window_tokens=resolved.context_window_tokens,
        ),
    )
    return RuntimeModelInvoker(OpenAIModelAdapter(selector=selector))


def _selector(
    *,
    provider: ProviderRegistration,
    protocol_adapters: list[ProtocolAdapter],
    profile: ModelProfile,
) -> ModelSelector:
    providers = ProviderRegistry()
    providers.register(provider)
    protocols = ProtocolRegistry()
    for adapter in protocol_adapters:
        protocols.register(adapter)
    profiles = ProfileRegistry()
    profiles.register(profile)
    return ModelSelector(providers=providers, profiles=profiles, protocols=protocols)


def _resolve_runtime_model(
    config: ModelProviderConfig,
    selection: RuntimeModelSelection | None,
) -> _ResolvedRuntimeModel:
    provider = (selection.provider if selection and selection.provider else config.RUNTIME_MODEL_PROVIDER)
    model = selection.model if selection and selection.model else config.RUNTIME_MODEL_NAME
    protocol = selection.protocol if selection and selection.protocol else ModelProtocol(config.RUNTIME_MODEL_PROTOCOL)
    context_window_tokens = (
        selection.context_window_tokens
        if selection and selection.context_window_tokens is not None
        else config.RUNTIME_MODEL_CONTEXT_WINDOW_TOKENS
    )
    if provider not in {"mock", "openai"}:
        raise ModelConfigurationError(
            provider=provider,
            model=model,
            operation="runtime_factory",
            data={"reason": "unsupported_runtime_model_provider"},
        )
    if provider == "mock" and protocol != ModelProtocol.MOCK:
        raise ModelConfigurationError(
            provider=provider,
            model=model,
            protocol=protocol.value,
            operation="runtime_factory",
            data={"reason": "mock_provider_requires_mock_protocol"},
        )
    if provider == "openai" and protocol == ModelProtocol.MOCK:
        raise ModelConfigurationError(
            provider=provider,
            model=model,
            protocol=protocol.value,
            operation="runtime_factory",
            data={"reason": "openai_provider_requires_openai_protocol"},
        )
    return _ResolvedRuntimeModel(
        provider=provider,
        model=model,
        protocol=protocol,
        context_window_tokens=context_window_tokens,
    )


__all__ = [
    "RuntimeModelTarget",
    "RuntimeModelSelection",
    "build_mock_model_invoker",
    "build_openai_model_invoker",
    "build_runtime_model_invoker",
    "build_runtime_model_target",
]
