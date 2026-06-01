"""Runtime 依赖工厂。"""

from src.contracts.runtime import ModelCapabilities
from src.contracts.runtime import ModelProtocol
from src.models import ModelProfile
from src.models import ModelSelector
from src.models import ProfileRegistry
from src.models import ProviderRegistration
from src.models import ProviderRegistry
from src.models import ProtocolRegistry
from src.models.providers.mock import MockModelAdapter
from src.models.providers.mock import MockProtocolAdapter
from src.runtime.model_invoker import RuntimeModelInvoker


def build_mock_model_invoker() -> RuntimeModelInvoker:
    """构造当前 AgentRuntime 使用的 mock 模型 invoker。

    Returns:
        RuntimeModelInvoker。
    """
    providers = ProviderRegistry()
    providers.register(
        ProviderRegistration(
            name="mock",
            base_url="mock://local",
            default_timeout_seconds=30.0,
        )
    )
    protocols = ProtocolRegistry()
    protocols.register(MockProtocolAdapter())
    profiles = ProfileRegistry()
    profiles.register(
        ModelProfile(
            name="mock-model-runtime",
            provider="mock",
            model="mock-model",
            protocol=ModelProtocol.MOCK,
            capabilities=ModelCapabilities(tool_calling=True, streaming=True),
        )
    )
    selector = ModelSelector(providers=providers, profiles=profiles, protocols=protocols)
    return RuntimeModelInvoker(MockModelAdapter(selector=selector))


__all__ = ["build_mock_model_invoker"]
