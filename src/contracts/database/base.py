"""
基础数据模型

提供 ORM 基础模型，统一 UUID 主键、时间字段与序列化行为。
"""

from datetime import UTC
from datetime import datetime
from enum import IntEnum
from enum import StrEnum
from typing import Annotated
from typing import TypeVar
from uuid import uuid4

from sqlalchemy import MetaData
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import declared_attr
from sqlalchemy.orm import mapped_column
from sqlalchemy.types import BOOLEAN
from sqlalchemy.types import FLOAT
from sqlalchemy.types import INTEGER
from sqlalchemy.types import JSON
from sqlalchemy.types import TEXT
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.types import UUID
from sqlalchemy.types import VARCHAR

from src.contracts.database.orm_types import OrmIntEnum
from src.contracts.database.orm_types import OrmStringEnum
from src.core.utils import camel_to_snake

OrmTextType = TypeVar("OrmTextType", bound=str)
JsonbType = TypeVar("JsonbType", dict, list)

metadata = MetaData(
    naming_convention={
        "ix": "idx_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class BaseModel(DeclarativeBase):
    """ORM 基础模型，提供通用类型映射与表名自动生成。"""

    __abstract__ = True
    metadata = metadata

    type_annotation_map = {
        bool: BOOLEAN,
        datetime: TIMESTAMP(timezone=False),
        float: FLOAT,
        int: INTEGER,
        dict: JSON,
        JsonbType: JSONB,
        OrmTextType: TEXT,
        UUID: UUID,
        str: VARCHAR,
        Annotated[str, 32]: VARCHAR(32),
        Annotated[str, 64]: VARCHAR(64),
        Annotated[str, 255]: VARCHAR(255),
        IntEnum: OrmIntEnum,
        StrEnum: OrmStringEnum,
    }

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        return camel_to_snake(cls.__name__)


class PkModel(BaseModel):
    """带 UUID 主键的基础模型。"""

    __abstract__ = True

    id: Mapped[UUID | None] = mapped_column(
        primary_key=True,
        nullable=False,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )


class TimestampedModel(BaseModel):
    """带 created_at / updated_at 时间戳的基础模型。"""

    __abstract__ = True

    created_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=False),
        nullable=False,
        index=True,
        server_default=text("timezone('UTC', now())"),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=False),
        onupdate=lambda: datetime.now(UTC).replace(microsecond=0, tzinfo=UTC),
        nullable=False,
        index=True,
        server_default=text("timezone('UTC', now())"),
        server_onupdate=text("timezone('UTC', now())"),
    )
