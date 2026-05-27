"""Provider、protocol 与 model profile 注册表。"""

from src.contracts.runtime import ModelProtocol
from src.exceptions import ModelCapabilityError
from src.exceptions import ModelConfigurationError
from src.models.base import ProtocolAdapter
from src.models.base import ProviderRegistration
from src.models.profiles import ModelProfile


class ProviderRegistry:
    """以显式身份注册可执行 provider 配置。"""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderRegistration] = {}

    def register(self, provider: ProviderRegistration) -> None:
        """注册或替换 provider。

        Args:
            provider: provider 注册项。
        """
        self._providers[provider.name] = provider

    def require(self, name: str) -> ProviderRegistration:
        """获取 provider，不存在时失败。

        Args:
            name: provider 身份。

        Returns:
            已注册 provider。

        Raises:
            ModelConfigurationError: provider 未注册。
        """
        try:
            return self._providers[name]
        except KeyError as exc:
            raise ModelConfigurationError(provider=name, operation="select") from exc


class ProtocolRegistry:
    """维护 protocol identity 到具体实现的显式映射。"""

    def __init__(self) -> None:
        self._adapters: dict[ModelProtocol, ProtocolAdapter] = {}

    def register(self, adapter: ProtocolAdapter) -> None:
        """注册可执行 protocol adapter。

        Args:
            adapter: protocol 实例。
        """
        self._adapters[adapter.protocol] = adapter

    def require(
        self,
        protocol: ModelProtocol,
        *,
        provider: str,
        model: str,
    ) -> ProtocolAdapter:
        """解析可执行 protocol。

        Args:
            protocol: profile 指定的协议身份。
            provider: provider 身份。
            model: 模型身份。

        Returns:
            已注册协议 adapter。

        Raises:
            ModelCapabilityError: 该协议仅保留身份或尚未注册实现。
        """
        try:
            return self._adapters[protocol]
        except KeyError as exc:
            raise ModelCapabilityError(
                provider=provider,
                model=model,
                protocol=protocol.value,
                operation="select",
                data={"reason": "protocol_not_registered"},
            ) from exc


class ProfileRegistry:
    """以 provider/model 组合解析模型 profile。"""

    def __init__(self) -> None:
        self._profiles: dict[tuple[str, str], ModelProfile] = {}

    def register(self, profile: ModelProfile) -> None:
        """注册或替换模型 profile。

        Args:
            profile: 模型 profile。
        """
        self._profiles[(profile.provider, profile.model)] = profile

    def require(self, *, provider: str | None, model: str) -> ModelProfile:
        """解析请求目标 profile。

        Args:
            provider: 可选显式 provider。
            model: 请求模型身份。

        Returns:
            唯一匹配的 profile。

        Raises:
            ModelConfigurationError: 无匹配或 provider 未明确且存在歧义。
        """
        matches = [
            profile
            for (profile_provider, profile_model), profile in self._profiles.items()
            if profile_model == model and (provider is None or provider == profile_provider)
        ]
        if len(matches) != 1:
            raise ModelConfigurationError(
                provider=provider,
                model=model,
                operation="select",
                data={"reason": "profile_not_found_or_ambiguous"},
            )
        return matches[0]
