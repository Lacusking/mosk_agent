"""预留上下文策略测试。"""

import pytest

from src.context import ContextBundle
from src.context.strategies import AutoCompactStrategy
from src.context.strategies import ReactiveCompactStrategy


@pytest.mark.asyncio
async def test_reactive_compact_strategy_remains_reserved() -> None:
    """reactiveCompact 仍保留为 runtime 应急恢复的后续策略骨架。"""
    with pytest.raises(NotImplementedError):
        await ReactiveCompactStrategy().apply(
            ContextBundle(agent_run_id="run-1", session_id="session-1")
        )


@pytest.mark.asyncio
async def test_auto_compact_is_noop_when_disabled() -> None:
    """autoCompact 默认禁用时不调用摘要能力。"""
    bundle = ContextBundle(agent_run_id="run-1", session_id="session-1")

    result = await AutoCompactStrategy().apply(bundle)

    assert result == bundle
