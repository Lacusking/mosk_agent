"""Runtime 最小工具动作端口契约。"""

from enum import StrEnum

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict
from pydantic import Field

from src.contracts.runtime import JsonValue


class _ToolSchema(PydanticBaseModel):
    """工具动作契约的共同校验配置。"""

    model_config = ConfigDict(extra="forbid")


class ToolActionStatus(StrEnum):
    """工具动作执行状态。"""

    SUCCESS = "success"
    VALIDATION_FAILED = "validation_failed"
    EXECUTION_FAILED = "execution_failed"


class ToolActionRequest(_ToolSchema):
    """Runtime 发给工具 executor 的动作请求。"""

    call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    agent_run_id: str = Field(min_length=1)
    step_id: str | None = None


class ToolActionResult(_ToolSchema):
    """工具 executor 返回的安全结果。"""

    call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: ToolActionStatus
    observation: JsonValue = None
    is_error: bool = False
    error_type: str | None = None


class ToolActionFailure(_ToolSchema):
    """工具动作失败的标准分类。"""

    call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: ToolActionStatus
    error_type: str = Field(min_length=1)
    message: str = Field(min_length=1)


__all__ = [
    "ToolActionFailure",
    "ToolActionRequest",
    "ToolActionResult",
    "ToolActionStatus",
]
