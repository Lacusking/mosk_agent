"""
基础工具函数

纯函数优先，提供 ID 生成、时间处理、字符串转换等通用工具。
"""

import hashlib
import re
import uuid
from datetime import UTC
from datetime import datetime


def generate_uuid() -> str:
    """
    生成 UUID v4 字符串。

    Returns:
        32 位十六进制 UUID 字符串。
    """
    return str(uuid.uuid4())


def generate_uuid7() -> str:
    """
    生成 UUID v7 字符串（时间有序）。

    Returns:
        UUID v7 字符串。
    """
    return str(uuid.uuid7())


def utc_now() -> datetime:
    """
    获取当前 UTC 时间（带时区信息）。

    Returns:
        当前 UTC 时间。
    """
    return datetime.now(UTC)


def camel_to_snake(camel_str: str) -> str:
    """
    将驼峰命名转换为下划线命名。

    Args:
        camel_str: 驼峰格式字符串，如 "CamelCaseExample"。

    Returns:
        下划线格式字符串，如 "camel_case_example"。
    """
    if not camel_str:
        raise ValueError("输入字符串不能为空")
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel_str).lower()


def calculate_md5(data: bytes | str) -> str:
    """
    计算文本或二进制数据的 MD5 哈希值。

    Args:
        data: 需要计算哈希值的数据。

    Returns:
        32 位十六进制 MD5 字符串。
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.md5(data).hexdigest()


def format_datetime(dt: datetime) -> str:
    """
    将 datetime 格式化为 ISO 8601 字符串。

    Args:
        dt: 待格式化的 datetime 对象。

    Returns:
        ISO 8601 格式字符串。
    """
    return dt.isoformat()
