"""
自定义 ORM 类型

提供枚举类型到数据库类型的映射。
"""

import logging
from enum import Enum
from typing import Any

import sqlalchemy
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)


class BaseEnumType(TypeDecorator):
    """自定义枚举类型装饰器基类。"""

    def __init__(self, enum_type: type[Enum], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not issubclass(enum_type, Enum):
            raise TypeError(f"'{enum_type.__name__}' is not a subclass of enum.Enum")
        self.enum_type = enum_type

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        """保存到数据库时转换枚举为原始值。"""
        if value is None:
            return None
        if isinstance(value, self.enum_type):
            return value.value
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        """从数据库读取时还原为枚举。"""
        if value is None:
            return None
        try:
            return self.enum_type(value)
        except ValueError as e:
            logger.error(
                "Database value '%s' is not a valid member of enum '%s'.",
                value,
                self.enum_type.__name__,
            )
            raise ValueError(f"{value} is not a valid {self.enum_type.__name__}") from e


class OrmIntEnum(BaseEnumType):
    """将 Enum 存储为 Integer。"""

    impl = sqlalchemy.Integer
    cache_ok = True


class OrmStringEnum(BaseEnumType):
    """将 Enum 存储为 String。"""

    impl = sqlalchemy.String
    cache_ok = True
