"""跨模块契约命名空间。

数据库契约位于 ``src.contracts.database``，runtime 契约位于
``src.contracts.runtime``。以下导出仅保留既有 ORM 类型的兼容入口。
"""

from src.contracts.database import BaseModel
from src.contracts.database import PkModel
from src.contracts.database import TimestampedModel

__all__ = [
    "BaseModel",
    "PkModel",
    "TimestampedModel",
]
