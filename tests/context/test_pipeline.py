"""上下文策略管线测试。"""

import pytest

from src.context import ContextBundle
from src.context import ContextStrategyPipeline
from src.context.schemas import ContextBundle as Bundle


class _AppendArtifactStrategy:
    def __init__(self, marker: str) -> None:
        self._marker = marker

    async def apply(self, bundle: Bundle) -> Bundle:
        current = list(bundle.artifacts)
        return bundle.model_copy(update={"artifacts": [*current, self._marker]})


class _FailingStrategy:
    async def apply(self, bundle: Bundle) -> Bundle:
        raise RuntimeError("strategy failed")


@pytest.mark.asyncio
async def test_pipeline_applies_strategies_in_order() -> None:
    """pipeline 使用上一个策略的输出作为下一个策略输入。"""
    pipeline = ContextStrategyPipeline(
        [_AppendArtifactStrategy("first"), _AppendArtifactStrategy("second")]
    )

    result = await pipeline.apply(ContextBundle(agent_run_id="run-1", session_id="session-1"))

    assert result.artifacts == ["first", "second"]


@pytest.mark.asyncio
async def test_pipeline_stops_on_strategy_failure() -> None:
    """策略失败时 pipeline 停止并向上传递错误。"""
    pipeline = ContextStrategyPipeline([_FailingStrategy(), _AppendArtifactStrategy("never")])

    with pytest.raises(RuntimeError, match="strategy failed"):
        await pipeline.apply(ContextBundle(agent_run_id="run-1", session_id="session-1"))
