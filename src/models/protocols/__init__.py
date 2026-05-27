"""模型 wire protocol 实现。"""

from src.models.protocols.openai_chat import OpenAIChatProtocolAdapter
from src.models.protocols.openai_responses import OpenAIResponsesProtocolAdapter

__all__ = ["OpenAIChatProtocolAdapter", "OpenAIResponsesProtocolAdapter"]
