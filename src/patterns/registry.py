"""Agent pattern 注册表。"""

from src.patterns.base import Pattern
from src.patterns.errors import PatternSelectionError


class PatternRegistry:
    """维护 pattern 名称到实现的显式映射。"""

    def __init__(self) -> None:
        self._patterns: dict[str, Pattern] = {}

    def register(self, pattern: Pattern) -> None:
        """注册或替换 pattern。

        Args:
            pattern: pattern 实现。
        """
        pattern.validate(self)
        self._patterns[pattern.name] = pattern

    def require(self, name: str) -> Pattern:
        """读取 pattern，不存在时失败。

        Args:
            name: pattern 名称。

        Returns:
            已注册 pattern。

        Raises:
            PatternSelectionError: pattern 未注册。
        """
        try:
            return self._patterns[name]
        except KeyError as exc:
            raise PatternSelectionError(data={"pattern": name}) from exc

    def has(self, name: str) -> bool:
        """检查 pattern 是否注册。

        Args:
            name: pattern 名称。

        Returns:
            已注册时返回 True。
        """
        return name in self._patterns

    def names(self) -> list[str]:
        """返回已注册 pattern 名称。

        Returns:
            按名称排序的 pattern 名称。
        """
        return sorted(self._patterns)


__all__ = ["PatternRegistry"]
