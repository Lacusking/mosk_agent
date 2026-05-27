"""模型 adapter 与安全调用上下文基础类型。"""

from collections.abc import AsyncIterator
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Protocol

from src.contracts.runtime import JsonValue
from src.contracts.runtime import ModelCapabilities
from src.contracts.runtime import ModelProtocol
from src.contracts.runtime import ModelRequest
from src.contracts.runtime import ModelResponse
from src.contracts.runtime import ModelStreamEvent
from src.exceptions import ModelError

if TYPE_CHECKING:
    from src.models.profiles import ModelProfile


@dataclass(frozen=True)
class ProviderRegistration:
    """可执行 provider 的非敏感注册信息。"""

    name: str
    base_url: str
    default_timeout_seconds: float
    api_key: str | None = None


@dataclass(frozen=True)
class InvocationContext:
    """供 parser 与错误映射使用的安全调用上下文。"""

    invocation_id: str
    provider: str
    model: str
    protocol: ModelProtocol
    profile_name: str
    capabilities: ModelCapabilities
    streaming: bool
    effective_timeout_seconds: float
    started_at: datetime
    safe_metadata: Mapping[str, JsonValue]


class ProtocolAdapter(Protocol):
    """模型 wire protocol 编解码边界。"""

    protocol: ModelProtocol

    def build_payload(self, request: ModelRequest, profile: "ModelProfile") -> dict[str, object]:
        """构造 provider 请求 payload。

        Args:
            request: 已校验的统一模型请求。
            profile: 选定的模型 profile。

        Returns:
            不包含认证或 transport timeout 的 provider payload。
        """
        ...

    def parse_response(self, response: object, context: InvocationContext) -> ModelResponse:
        """解析 blocking 响应。

        Args:
            response: provider 返回的数据。
            context: 当前调用的安全上下文。

        Returns:
            统一模型响应。
        """
        ...

    def stream_events(
        self,
        events: AsyncIterator[dict[str, object]],
        context: InvocationContext,
    ) -> AsyncIterator[ModelStreamEvent]:
        """转换 provider SSE 数据事件。

        Args:
            events: transport 解码后的 provider 数据事件。
            context: 当前调用的安全上下文。

        Returns:
            标准化模型流事件迭代器。
        """
        ...

    def map_error(
        self, error: Exception, context: InvocationContext, *, operation: str
    ) -> ModelError:
        """将 provider 或 transport 错误映射为统一模型异常。

        Args:
            error: 原始失败。
            context: 当前调用的安全上下文。
            operation: 失败操作。

        Returns:
            标准化模型异常。
        """
        ...


class ModelAdapter(Protocol):
    """供后续 runtime 调用的统一模型适配接口。"""

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        """执行 blocking 调用。

        Args:
            request: 已校验的统一模型请求。

        Returns:
            统一模型最终响应。
        """
        ...

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]:
        """执行 streaming 调用。

        Args:
            request: 已校验的统一模型请求。

        Returns:
            类型化模型流事件迭代器。
        """
        ...
