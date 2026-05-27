"""模型 transport 边界。"""

from src.models.transport.auth import build_openai_headers
from src.models.transport.http import HttpModelTransport

__all__ = ["HttpModelTransport", "build_openai_headers"]
