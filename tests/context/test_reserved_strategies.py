"""预留上下文策略测试。"""

import pytest

from src.context import ContextBundle
from src.context.strategies import AutoCompactStrategy
from src.context.strategies import MicroCompactStrategy
from src.context.strategies import ReactiveCompactStrategy
from src.context.strategies import ToolResultBudgetStrategy


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "strategy",
    [
        MicroCompactStrategy(),
        ToolResultBudgetStrategy(),
        AutoCompactStrategy(),
        ReactiveCompactStrategy(),
    ],
)
async def test_reserved_strategies_raise_not_implemented(strategy) -> None:
    """预留策略拥有完整类骨架但不在首期实现。"""
    with pytest.raises(NotImplementedError):
        await strategy.apply(ContextBundle(agent_run_id="run-1", session_id="session-1"))
