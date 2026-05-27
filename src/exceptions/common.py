"""平台通用异常类型。"""

from src.exceptions.base import BaseError


class ValidationError(BaseError):
    """参数校验异常。"""

    code = 40000
    default_msg = "参数校验失败"


class NotFoundError(BaseError):
    """资源不存在异常。"""

    code = 40400
    default_msg = "资源不存在"


class AuthenticationError(BaseError):
    """认证异常。"""

    code = 40100
    default_msg = "认证失败"


class ForbiddenError(BaseError):
    """禁止访问异常。"""

    code = 40300
    default_msg = "禁止访问"


class ConfigurationError(BaseError):
    """配置异常。"""

    code = 50001
    default_msg = "配置错误"
