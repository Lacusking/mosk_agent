"""
HTTP 客户端服务枚举
"""

from enum import Enum


class ServiceClient(str, Enum):
    """业务服务客户端名称清单。"""

    DEFAULT = "default"
