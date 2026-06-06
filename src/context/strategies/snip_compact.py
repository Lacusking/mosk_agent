"""无 LLM 调用的头尾裁剪策略。"""

from src.context.errors import ContextStrategyError
from src.context.schemas import ContextBundle
from src.context.schemas import ContextItem


class SnipCompactStrategy:
    """保留头部、尾部和关键 item，裁剪中间可驱逐消息。"""

    def __init__(
        self,
        *,
        threshold_messages: int,
        head_messages: int,
        tail_messages: int,
        priority_floor: int = 100,
    ) -> None:
        """初始化策略。

        Args:
            threshold_messages: 触发和目标消息数阈值。
            head_messages: 固定保留的头部消息数。
            tail_messages: 固定保留的尾部消息数。
            priority_floor: 达到该优先级的 item 视为关键上下文。

        Raises:
            ContextStrategyError: 配置非法。
        """
        if threshold_messages <= 0:
            raise ContextStrategyError(msg="snip threshold 必须大于 0")
        if head_messages < 0 or tail_messages < 0:
            raise ContextStrategyError(msg="snip head/tail 必须大于等于 0")
        self._threshold_messages = threshold_messages
        self._head_messages = head_messages
        self._tail_messages = tail_messages
        self._priority_floor = priority_floor

    async def apply(self, bundle: ContextBundle) -> ContextBundle:
        """裁剪上下文包中的 session message items。

        Args:
            bundle: 输入上下文包。

        Returns:
            裁剪后的上下文包。
        """
        messages = sorted(
            bundle.session_messages,
            key=lambda item: item.sequence if item.sequence is not None else 0,
        )
        if len(messages) <= self._threshold_messages:
            return bundle.model_copy(update={"session_messages": messages})

        protected_indexes = self._protected_indexes(messages)
        keep_indexes = set(protected_indexes)

        for index in range(len(messages) - 1, -1, -1):
            if len(keep_indexes) >= self._threshold_messages:
                break
            keep_indexes.add(index)

        compacted: list[ContextItem] = []
        evicted: list[ContextItem] = []
        for index, item in enumerate(messages):
            if index in keep_indexes or not _can_evict(item):
                compacted.append(item)
            else:
                evicted.append(item)
        return bundle.model_copy(
            update={
                "session_messages": compacted,
                "evicted_items": [*bundle.evicted_items, *evicted],
            }
        )

    def _protected_indexes(self, messages: list[ContextItem]) -> set[int]:
        indexes = set(range(min(self._head_messages, len(messages))))
        if self._tail_messages:
            indexes.update(range(max(0, len(messages) - self._tail_messages), len(messages)))
        for index, item in enumerate(messages):
            if item.pinned or not item.evictable or item.priority >= self._priority_floor:
                indexes.add(index)
        return indexes


def _can_evict(item: ContextItem) -> bool:
    return item.evictable and not item.pinned


__all__ = ["SnipCompactStrategy"]
