"""Pattern 选择与配置异常。"""

from src.exceptions import ValidationError


class PatternSelectionError(ValidationError):
    """Pattern 选择失败。"""

    default_msg = "Pattern 不可用"


__all__ = ["PatternSelectionError"]
