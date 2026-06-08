"""工具结果上下文总量预算策略。"""

from src.context.errors import ContextStrategyError
from src.context.schemas import ContextBundle
from src.context.schemas import ContextItem


class ToolResultBudgetStrategy:
    """限制 tool observation items 的 token 总占用。"""

    def __init__(self, *, max_tokens: int) -> None:
        """初始化策略。"""
        if max_tokens <= 0:
            raise ContextStrategyError(msg="toolResultBudget token 上限必须大于 0")
        self._max_tokens = max_tokens

    async def apply(self, bundle: ContextBundle) -> ContextBundle:
        """按优先级和时间顺序裁剪可驱逐 tool observation。"""
        observations = list(bundle.tool_observations)
        if _total_tokens(observations) <= self._max_tokens:
            return bundle

        keep = set(range(len(observations)))
        evicted: list[ContextItem] = []
        candidates = sorted(
            [
                (index, item)
                for index, item in enumerate(observations)
                if item.evictable and not item.pinned
            ],
            key=lambda pair: (
                pair[1].priority,
                int(pair[1].metadata.get("order", 0)),
            ),
        )
        for index, item in candidates:
            if _total_tokens([observations[i] for i in keep]) <= self._max_tokens:
                break
            keep.remove(index)
            evicted.append(item)

        compacted = [item for index, item in enumerate(observations) if index in keep]
        return bundle.model_copy(
            update={
                "tool_observations": compacted,
                "evicted_items": [*bundle.evicted_items, *evicted],
            }
        )


def _total_tokens(items: list[ContextItem]) -> int:
    return sum(item.token_count or 0 for item in items)


__all__ = ["ToolResultBudgetStrategy"]
