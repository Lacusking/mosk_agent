"""Agent pattern registry 与内置实现。"""

from src.patterns.base import Pattern
from src.patterns.chaining import ChainingPattern
from src.patterns.errors import PatternSelectionError
from src.patterns.planning import PlanningPattern
from src.patterns.react import ReactPattern
from src.patterns.reflection import ReflectionPattern
from src.patterns.registry import PatternRegistry
from src.patterns.routing import RoutingPattern
from src.patterns.selector import PatternSelection
from src.patterns.selector import PatternSelectionSource
from src.patterns.selector import PatternSelector
from src.patterns.single_turn import SingleTurnPattern


def default_pattern_registry() -> PatternRegistry:
    """创建包含首期内置 pattern 的注册表。

    Returns:
        已注册内置 pattern 的注册表。
    """
    registry = PatternRegistry()
    registry.register(SingleTurnPattern())
    registry.register(PlanningPattern())
    registry.register(ChainingPattern())
    registry.register(ReflectionPattern())
    registry.register(ReactPattern())
    registry.register(RoutingPattern())
    return registry


__all__ = [
    "ChainingPattern",
    "Pattern",
    "PatternRegistry",
    "PatternSelection",
    "PatternSelectionError",
    "PatternSelectionSource",
    "PatternSelector",
    "PlanningPattern",
    "ReactPattern",
    "ReflectionPattern",
    "RoutingPattern",
    "SingleTurnPattern",
    "default_pattern_registry",
]
