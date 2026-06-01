"""从公开模型请求选择 provider、profile 与协议实现。"""

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime

from src.contracts.runtime import JsonValue
from src.contracts.runtime import ModelRequest
from src.exceptions import ModelCapabilityError
from src.models.base import InvocationContext
from src.models.base import ProtocolAdapter
from src.models.base import ProviderRegistration
from src.models.capabilities import validate_request_capabilities
from src.models.profiles import ModelProfile
from src.models.registry import ProfileRegistry
from src.models.registry import ProtocolRegistry
from src.models.registry import ProviderRegistry

_SAFE_METADATA_KEYS = frozenset(
    {"request_id", "trace_id", "agent_run_id", "step_id", "mode"}
)


@dataclass(frozen=True)
class SelectedInvocation:
    """一次已解析且可执行的模型调用。"""

    provider: ProviderRegistration
    profile: ModelProfile
    protocol_adapter: ProtocolAdapter
    context: InvocationContext


class ModelSelector:
    """解析请求并在任何远程调用前完成能力验证。"""

    def __init__(
        self,
        *,
        providers: ProviderRegistry,
        profiles: ProfileRegistry,
        protocols: ProtocolRegistry,
    ) -> None:
        self.providers = providers
        self.profiles = profiles
        self.protocols = protocols

    def select(self, request: ModelRequest) -> SelectedInvocation:
        """解析可执行 invocation。

        Args:
            request: 标准模型请求。

        Returns:
            可供 adapter 执行的调用选择结果。

        Raises:
            ModelCapabilityError: 显式协议与 profile 约束冲突。
        """
        profile = self.profiles.require(provider=request.provider, model=request.model)
        if request.protocol is not None and request.protocol != profile.protocol:
            raise ModelCapabilityError(
                provider=profile.provider,
                model=profile.model,
                protocol=request.protocol.value,
                operation="select",
                data={"reason": "request_protocol_conflicts_with_profile"},
            )
        validate_request_capabilities(request, profile)
        provider = self.providers.require(profile.provider)
        adapter = self.protocols.require(
            profile.protocol, provider=profile.provider, model=profile.model
        )
        metadata: dict[str, JsonValue] = {
            key: value for key, value in request.metadata.items() if key in _SAFE_METADATA_KEYS
        }
        timeout = request.timeout_seconds or provider.default_timeout_seconds
        return SelectedInvocation(
            provider=provider,
            profile=profile,
            protocol_adapter=adapter,
            context=InvocationContext(
                invocation_id=request.invocation_id,
                provider=profile.provider,
                model=profile.model,
                protocol=profile.protocol,
                profile_name=profile.name,
                capabilities=profile.capabilities,
                streaming=request.stream,
                effective_timeout_seconds=timeout,
                started_at=datetime.now(UTC),
                safe_metadata=metadata,
            ),
        )
