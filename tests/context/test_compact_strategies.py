"""高级上下文 compact 策略测试。"""

import pytest

from src.context import ContextBundle
from src.context import ContextItem
from src.context import ContextItemType
from src.context import ContextSource
from src.context.strategies import AutoCompactStrategy
from src.context.strategies import MicroCompactStrategy
from src.context.strategies import ToolResultBudgetStrategy
from src.contracts.runtime import ToolResultContentBlock


def _tool_item(
    call_id: str,
    *,
    tokens: int,
    order: int,
    priority: int = 0,
    pinned: bool = False,
) -> ContextItem:
    return ContextItem(
        source=ContextSource.TOOL,
        type=ContextItemType.OBSERVATION,
        content={
            "call_id": call_id,
            "status": "success",
            "observation": "x" * max(1, tokens * 4),
            "is_error": False,
        },
        token_count=tokens,
        priority=priority,
        pinned=pinned,
        evictable=not pinned,
        metadata={"call_id": call_id, "order": order},
    )


@pytest.mark.asyncio
async def test_micro_compact_truncates_oversized_tool_observation() -> None:
    """过大的 ContextItem 会被首尾截断。"""
    bundle = ContextBundle(
        agent_run_id="run-1",
        session_id="session-1",
        tool_observations=[_tool_item("call-1", tokens=50, order=1)],
    )

    result = await MicroCompactStrategy(max_item_tokens=10).apply(bundle)

    item = result.tool_observations[0]
    assert item.token_count == 10
    assert item.metadata["micro_compacted"] is True
    assert "[snipped middle content]" in str(item.content["observation"])


@pytest.mark.asyncio
async def test_micro_compact_keeps_short_content() -> None:
    """短内容不截断。"""
    item = _tool_item("call-1", tokens=3, order=1)
    bundle = ContextBundle(
        agent_run_id="run-1",
        session_id="session-1",
        tool_observations=[item],
    )

    result = await MicroCompactStrategy(max_item_tokens=10).apply(bundle)

    assert result.tool_observations == [item]


@pytest.mark.asyncio
async def test_tool_result_budget_drops_low_priority_old_items() -> None:
    """工具 observation 总量超预算时按优先级和时间裁剪。"""
    pinned = _tool_item("pinned", tokens=8, order=1, pinned=True)
    old_low = _tool_item("old-low", tokens=5, order=2)
    new_low = _tool_item("new-low", tokens=5, order=3)
    high = _tool_item("high", tokens=5, order=4, priority=10)
    bundle = ContextBundle(
        agent_run_id="run-1",
        session_id="session-1",
        tool_observations=[pinned, old_low, new_low, high],
    )

    result = await ToolResultBudgetStrategy(max_tokens=13).apply(bundle)

    assert [item.metadata["call_id"] for item in result.tool_observations] == [
        "pinned",
        "high",
    ]
    assert [item.metadata["call_id"] for item in result.evicted_items] == [
        "old-low",
        "new-low",
    ]


@pytest.mark.asyncio
async def test_auto_compact_inserts_temporary_summary() -> None:
    """启用 autoCompact 后被驱逐内容可被摘要为临时 summary。"""

    async def summarize(items: list[ContextItem]) -> str:
        return f"summary for {len(items)} items"

    bundle = ContextBundle(
        agent_run_id="run-1",
        session_id="session-1",
        evicted_items=[_tool_item("call-1", tokens=5, order=1)],
    )

    result = await AutoCompactStrategy(enabled=True, summarizer=summarize).apply(bundle)

    assert result.memory_summary is not None
    assert result.memory_summary.source == ContextSource.SYSTEM
    assert result.memory_summary.type == ContextItemType.SUMMARY
    assert result.memory_summary.metadata["temporary"] is True


@pytest.mark.asyncio
async def test_tool_observation_converts_to_tool_model_message() -> None:
    """tool observation item 可转换为模型 tool_result 消息。"""
    bundle = ContextBundle(
        agent_run_id="run-1",
        session_id="session-1",
        tool_observations=[_tool_item("call-1", tokens=3, order=1)],
    )

    message = bundle.to_model_messages()[0]

    assert len(message.content) == 1
    assert isinstance(message.content[0], ToolResultContentBlock)
    assert message.content[0].call_id == "call-1"
