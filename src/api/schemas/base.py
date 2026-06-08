"""
Pydantic Schema 基类

所有 API 请求/响应 Schema 继承此基类。
"""

from datetime import UTC
from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class SchemaBase(BaseModel):
    """基础 Schema 配置。"""

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda dt: (
                dt.replace(tzinfo=UTC).isoformat()
                if dt.tzinfo is None
                else dt.astimezone(UTC).isoformat()
            )
        },
    )
