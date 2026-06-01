"""数据库时间边界转换工具。"""

from datetime import UTC
from datetime import datetime

from src.core.utils import utc_now


def naive_utc_now() -> datetime:
    """返回适配 TIMESTAMP WITHOUT TIME ZONE 的 UTC naive 当前时间。"""
    return utc_now().replace(microsecond=0, tzinfo=None)


def naive_utc_for_db(value: datetime | None) -> datetime | None:
    """将业务层时间转换为数据库列使用的 UTC naive 时间。"""
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def aware_utc_from_db(value: datetime | None) -> datetime | None:
    """将数据库 UTC 时间转换为对外 contract 使用的 aware UTC 时间。

    当前数据库列统一使用 ``TIMESTAMP WITHOUT TIME ZONE``，SQLAlchemy/asyncpg
    读取出来的是 naive datetime。对外 contract 和 API 响应应显式携带 UTC
    时区，避免 Pydantic 校验或序列化阶段出现不一致。
    """
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = ["aware_utc_from_db", "naive_utc_for_db", "naive_utc_now"]
