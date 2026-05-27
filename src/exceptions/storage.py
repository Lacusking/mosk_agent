"""存储域异常类型。"""

from src.exceptions.base import BaseError


class StorageError(BaseError):
    """存储操作异常。"""

    code = 50002
    default_msg = "存储操作失败"
