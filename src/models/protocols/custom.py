"""自定义协议的受控注册抽象边界。"""

from abc import ABC

from src.contracts.runtime import ModelProtocol
from src.models.base import ProtocolAdapter


class CustomProtocolAdapter(ProtocolAdapter, ABC):
    """需显式注册后方可执行的自定义协议抽象。"""

    protocol = ModelProtocol.CUSTOM
