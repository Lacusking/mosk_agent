"""Agent pattern 选择器。"""

from dataclasses import dataclass
from enum import StrEnum

from src.contracts.agent_runs import AgentMode
from src.core.config import AgentRuntimeConfig
from src.patterns.errors import PatternSelectionError
from src.patterns.modes import default_pattern_for_mode
from src.patterns.registry import PatternRegistry


class PatternSelectionSource(StrEnum):
    """Pattern 选择来源。"""

    EXPLICIT = "explicit"
    MODE_DEFAULT = "mode_default"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class PatternSelection:
    """Pattern selector 的选择结果。"""

    pattern: str
    source: PatternSelectionSource


class PatternSelector:
    """按显式 pattern、mode 默认、fallback 的顺序选择策略。"""

    def __init__(
        self,
        *,
        registry: PatternRegistry,
        config: AgentRuntimeConfig,
        fallback_pattern: str = "single_turn",
    ) -> None:
        """初始化 selector。

        Args:
            registry: pattern 注册表。
            config: runtime 配置。
            fallback_pattern: 系统兜底 pattern。
        """
        self._registry = registry
        self._config = config
        self._fallback_pattern = fallback_pattern

    def select(self, *, mode: AgentMode, requested_pattern: str | None = None) -> PatternSelection:
        """选择本次运行的 pattern。

        Args:
            mode: 请求 mode。
            requested_pattern: 可选显式 pattern。

        Returns:
            选择结果。

        Raises:
            PatternSelectionError: 显式 pattern 不可用，或无任何可用兜底。
        """
        if requested_pattern:
            if not self._registry.has(requested_pattern):
                raise PatternSelectionError(data={"pattern": requested_pattern, "source": "explicit"})
            return PatternSelection(requested_pattern, PatternSelectionSource.EXPLICIT)

        mode_default = default_pattern_for_mode(mode, self._config)
        if self._registry.has(mode_default):
            return PatternSelection(mode_default, PatternSelectionSource.MODE_DEFAULT)

        if self._registry.has(self._fallback_pattern):
            return PatternSelection(self._fallback_pattern, PatternSelectionSource.FALLBACK)

        raise PatternSelectionError(
            data={"mode": mode.value, "mode_default": mode_default, "fallback": self._fallback_pattern}
        )


__all__ = ["PatternSelection", "PatternSelectionSource", "PatternSelector"]
