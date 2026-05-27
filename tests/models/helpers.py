"""模型 adapter 测试共享构造器。"""

from src.contracts.runtime import ModelCapabilities
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelRequest
from src.contracts.runtime import ModelRole
from src.contracts.runtime import TextContentBlock
from src.models.base import ProtocolAdapter
from src.models.base import ProviderRegistration
from src.models.profiles import ModelProfile
from src.models.registry import ProfileRegistry
from src.models.registry import ProtocolRegistry
from src.models.registry import ProviderRegistry
from src.models.selector import ModelSelector


def request(
    *,
    protocol: ModelProtocol,
    provider: str = "openai",
    model: str = "gpt-test",
    stream: bool = False,
    **changes: object,
) -> ModelRequest:
    """构造标准请求。

    Args:
        protocol: 目标协议。
        provider: provider 身份。
        model: 模型身份。
        stream: 是否流式。
        **changes: 其他字段覆盖。

    Returns:
        标准请求。
    """
    values: dict[str, object] = {
        "invocation_id": "invoke-1",
        "provider": provider,
        "model": model,
        "protocol": protocol,
        "messages": [
            ModelMessage(
                role=ModelRole.USER,
                content=[TextContentBlock(text="hello")],
            )
        ],
        "stream": stream,
    }
    values.update(changes)
    return ModelRequest.model_validate(values)


def selector(
    *,
    protocol: ModelProtocol,
    adapter: ProtocolAdapter,
    provider: str = "openai",
    model: str = "gpt-test",
    timeout: float = 30.0,
    capabilities: ModelCapabilities | None = None,
    allowed_options: frozenset[str] = frozenset(),
) -> ModelSelector:
    """创建含单一 profile 的 selector。

    Args:
        protocol: profile protocol。
        adapter: 已注册协议 adapter。
        provider: provider 名称。
        model: model 名称。
        timeout: provider 默认 timeout。
        capabilities: profile 能力。
        allowed_options: 可用 options。

    Returns:
        可执行 selector。
    """
    providers = ProviderRegistry()
    providers.register(
        ProviderRegistration(
            name=provider,
            base_url="https://provider.test/v1",
            default_timeout_seconds=timeout,
            api_key="sk-test-secret",
        )
    )
    protocols = ProtocolRegistry()
    protocols.register(adapter)
    profiles = ProfileRegistry()
    profiles.register(
        ModelProfile(
            name=f"{model}-{protocol.value}",
            provider=provider,
            model=model,
            protocol=protocol,
            capabilities=capabilities
            or ModelCapabilities(tool_calling=True, streaming=True, structured_output=True),
            allowed_options=allowed_options,
        )
    )
    return ModelSelector(providers=providers, profiles=profiles, protocols=protocols)
