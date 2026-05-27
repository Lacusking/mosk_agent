"""模型 profile 定义。"""

from dataclasses import dataclass
from dataclasses import field

from src.contracts.runtime import ModelCapabilities
from src.contracts.runtime import ModelProtocol


@dataclass(frozen=True)
class ModelProfile:
    """将模型标识绑定至 protocol 与可用能力。"""

    name: str
    provider: str
    model: str
    protocol: ModelProtocol
    capabilities: ModelCapabilities
    allowed_options: frozenset[str] = field(default_factory=frozenset)
