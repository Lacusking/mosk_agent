"""
统一响应模型与响应构造工具。

所有 API 响应遵循 {code, msg, data} 结构。
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any
from typing import TypeAlias

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class CustomCodeBase(Enum):
    """自定义状态码基类。"""

    def __init__(self, code: int, msg_key: str):
        self._code = code
        self._msg_key = msg_key

    @property
    def code(self) -> int:
        return self._code

    @property
    def msg(self) -> str:
        return self._msg_key


class GeneralResponseCode(CustomCodeBase):
    """通用响应状态码。"""

    HTTP_200 = (20000, "Success")
    HTTP_400 = (40000, "Error")
    HTTP_500 = (50000, "UnknownError")


class StandardResponseCode:
    """标准 HTTP 状态码。"""

    HTTP_200 = 200
    HTTP_400 = 400
    HTTP_401 = 401
    HTTP_403 = 403
    HTTP_404 = 404
    HTTP_422 = 422
    HTTP_500 = 500


@dataclasses.dataclass
class CustomResponse:
    """开放式响应状态码，用于自定义响应信息。"""

    code: int
    msg: str


ResponseItem: TypeAlias = BaseModel | dict[str, Any]
ResponseData: TypeAlias = ResponseItem | list[ResponseItem] | None


class ResponseModel(BaseModel):
    """统一响应模型。"""

    model_config = ConfigDict(extra="forbid")

    code: int = Field(default=GeneralResponseCode.HTTP_200.code, description="返回状态码")
    msg: str = Field(default=GeneralResponseCode.HTTP_200.msg, description="返回信息")
    data: BaseModel | dict[str, Any] = Field(default_factory=dict, description="返回数据")


class ResponseBase:
    """统一返回构造器。"""

    @staticmethod
    def _normalize_data(data: ResponseData) -> BaseModel | dict[str, Any]:
        if data is None:
            return {}
        if isinstance(data, BaseModel):
            return data
        if isinstance(data, list):
            for index, item in enumerate(data):
                if not isinstance(item, (BaseModel, dict)):
                    raise TypeError(
                        f"Response data list items must be BaseModel or dict, "
                        f"but got {type(item).__name__} at index {index}.",
                    )
            return {"items": data}
        if isinstance(data, dict):
            return data
        raise TypeError(
            f"Response data must be one of: BaseModel, dict, list[BaseModel | dict], or None, "
            f"but got {type(data).__name__}.",
        )

    @classmethod
    def _response(cls, *, res: GeneralResponseCode, data: ResponseData = None) -> ResponseModel:
        return ResponseModel(code=res.code, msg=res.msg, data=cls._normalize_data(data))

    def success(
        self, *, res: GeneralResponseCode = GeneralResponseCode.HTTP_200, data: ResponseData = None
    ) -> ResponseModel:
        """构造成功响应。"""
        return self._response(res=res, data=data)

    def fail(
        self, *, res: GeneralResponseCode = GeneralResponseCode.HTTP_400, data: ResponseData = None
    ) -> ResponseModel:
        """构造失败响应。"""
        return self._response(res=res, data=data)


response_base = ResponseBase()
