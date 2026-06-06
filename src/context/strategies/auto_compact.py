"""临时 LLM 摘要压缩策略。"""

import logging
from collections.abc import Awaitable
from collections.abc import Callable

from src.context.budget import DefaultTokenCounter
from src.context.budget import TokenCounter
from src.context.schemas import ContextBundle
from src.context.schemas import ContextItem
from src.context.schemas import ContextItemType
from src.context.schemas import ContextSource

logger = logging.getLogger(__name__)

type SummaryFn = Callable[[list[ContextItem]], Awaitable[str]]


class AutoCompactStrategy:
    """将已驱逐上下文摘要为仅当前 run 可见的临时 summary。"""

    def __init__(
        self,
        *,
        enabled: bool = False,
        summarizer: SummaryFn | None = None,
        token_counter: TokenCounter | None = None,
    ) -> None:
        """初始化策略。"""
        self._enabled = enabled
        self._summarizer = summarizer
        self._token_counter = token_counter or DefaultTokenCounter()

    async def apply(self, bundle: ContextBundle) -> ContextBundle:
        """在启用且存在 evicted_items 时尝试生成临时摘要。"""
        if not self._enabled or not bundle.evicted_items or self._summarizer is None:
            return bundle
        try:
            summary = await self._summarizer(bundle.evicted_items)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("autoCompact summary failed", exc_info=True)
            return bundle.model_copy(
                update={
                    "diagnostics": {
                        **bundle.diagnostics,
                        "auto_compact_failed": True,
                        "auto_compact_error": exc.__class__.__name__,
                    }
                }
            )
        if not summary:
            return bundle
        item = ContextItem(
            source=ContextSource.SYSTEM,
            type=ContextItemType.SUMMARY,
            content={"summary": summary},
            priority=100,
            token_count=self._token_counter.count(summary),
            pinned=True,
            evictable=False,
            metadata={"temporary": True},
        )
        return bundle.model_copy(update={"memory_summary": item})


__all__ = ["AutoCompactStrategy", "SummaryFn"]
