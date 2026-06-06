"""snip compact 策略测试。"""

import pytest

from src.context import ContextBundle
from src.context import ContextItem
from src.context import ContextItemType
from src.context import ContextSource
from src.context import ContextStrategyError
from src.context.strategies import SnipCompactStrategy
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import ModelRole
from src.contracts.runtime import TextContentBlock


def _item(
    sequence: int,
    *,
    pinned: bool = False,
    evictable: bool = True,
    priority: int = 0,
) -> ContextItem:
    return ContextItem(
        source=ContextSource.SESSION,
        type=ContextItemType.MESSAGE,
        content=ModelMessage(
            role=ModelRole.USER,
            content=[TextContentBlock(text=f"message {sequence}")],
        ),
        priority=priority,
        pinned=pinned,
        evictable=evictable,
        metadata={"sequence": sequence},
    )


def _bundle(count: int) -> ContextBundle:
    return ContextBundle(
        agent_run_id="run-1",
        session_id="session-1",
        session_messages=[_item(sequence) for sequence in range(1, count + 1)],
    )


@pytest.mark.asyncio
async def test_snip_compact_keeps_head_tail_and_priority_items() -> None:
    """长上下文裁剪时保留头部、尾部和高优先级 item。"""
    bundle = _bundle(10)
    messages = list(bundle.session_messages)
    messages[4] = _item(5, priority=100)
    bundle = bundle.model_copy(update={"session_messages": messages})

    result = await SnipCompactStrategy(
        threshold_messages=6,
        head_messages=2,
        tail_messages=3,
    ).apply(bundle)

    assert [item.sequence for item in result.session_messages] == [1, 2, 5, 8, 9, 10]


@pytest.mark.asyncio
async def test_snip_compact_does_not_change_short_context() -> None:
    """未超过阈值的上下文不裁剪。"""
    bundle = _bundle(3)

    result = await SnipCompactStrategy(
        threshold_messages=6,
        head_messages=2,
        tail_messages=3,
    ).apply(bundle)

    assert result.session_messages == bundle.session_messages


@pytest.mark.asyncio
async def test_snip_compact_does_not_drop_non_evictable_items() -> None:
    """无可驱逐 item 时不强行满足阈值。"""
    bundle = ContextBundle(
        agent_run_id="run-1",
        session_id="session-1",
        session_messages=[_item(sequence, evictable=False) for sequence in range(1, 6)],
    )

    result = await SnipCompactStrategy(
        threshold_messages=2,
        head_messages=0,
        tail_messages=0,
    ).apply(bundle)

    assert [item.sequence for item in result.session_messages] == [1, 2, 3, 4, 5]


def test_snip_compact_rejects_invalid_threshold() -> None:
    """非法 snip 配置在策略初始化时失败。"""
    with pytest.raises(ContextStrategyError):
        SnipCompactStrategy(threshold_messages=0, head_messages=0, tail_messages=0)
