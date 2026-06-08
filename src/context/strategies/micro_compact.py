"""无 LLM 调用的单项上下文截断策略。"""

import json

from src.context.budget import DefaultTokenCounter
from src.context.budget import TokenCounter
from src.context.errors import ContextStrategyError
from src.context.schemas import ContextBundle
from src.context.schemas import ContextItem
from src.contracts.runtime import JsonValue
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import TextContentBlock

_MARKER = "\n...[snipped middle content]...\n"


class MicroCompactStrategy:
    """将超过单项 token 上限的 ContextItem 压缩为首尾片段。"""

    def __init__(
        self,
        *,
        max_item_tokens: int,
        token_counter: TokenCounter | None = None,
    ) -> None:
        """初始化策略。"""
        if max_item_tokens <= 0:
            raise ContextStrategyError(msg="microCompact 单项 token 上限必须大于 0")
        self._max_item_tokens = max_item_tokens
        self._token_counter = token_counter or DefaultTokenCounter()

    async def apply(self, bundle: ContextBundle) -> ContextBundle:
        """截断过大的 session、summary、tool observation 和 artifact item。"""
        memory_summary = (
            self._compact_item(bundle.memory_summary) if bundle.memory_summary is not None else None
        )
        return bundle.model_copy(
            update={
                "session_messages": [self._compact_item(item) for item in bundle.session_messages],
                "memory_summary": memory_summary,
                "tool_observations": [
                    self._compact_item(item) for item in bundle.tool_observations
                ],
                "artifacts": [self._compact_item(item) for item in bundle.artifacts],
            }
        )

    def _compact_item(self, item: ContextItem) -> ContextItem:
        token_count = item.token_count
        if token_count is None:
            token_count = _count_item(item, self._token_counter)
        if token_count <= self._max_item_tokens:
            return item.model_copy(update={"token_count": token_count})

        compacted_content = _compact_content(
            item.content,
            max_chars=max(16, self._max_item_tokens * 4),
        )
        compacted = item.model_copy(
            update={
                "content": compacted_content,
                "metadata": {**item.metadata, "micro_compacted": True},
            }
        )
        compacted_tokens = min(_count_item(compacted, self._token_counter), self._max_item_tokens)
        return compacted.model_copy(update={"token_count": compacted_tokens})


def _compact_content(content: ModelMessage | dict[str, JsonValue], *, max_chars: int):
    if isinstance(content, ModelMessage):
        blocks = []
        for block in content.content:
            if isinstance(block, TextContentBlock):
                blocks.append(block.model_copy(update={"text": _snip_text(block.text, max_chars)}))
            else:
                blocks.append(block)
        return content.model_copy(update={"content": blocks})

    compacted = dict(content)
    for key in ("observation", "summary", "text", "output"):
        value = compacted.get(key)
        if isinstance(value, str):
            compacted[key] = _snip_text(value, max_chars)
            return compacted
        if value is not None:
            compacted[key] = _snip_text(
                json.dumps(value, ensure_ascii=False, separators=(",", ":")),
                max_chars,
            )
            return compacted
    return {"text": _snip_text(json.dumps(content, ensure_ascii=False), max_chars)}


def _snip_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    marker_len = len(_MARKER)
    available = max(2, max_chars - marker_len)
    head = max(1, available // 2)
    tail = max(1, available - head)
    return f"{text[:head]}{_MARKER}{text[-tail:]}"


def _count_item(item: ContextItem, token_counter: TokenCounter) -> int:
    content = item.content
    if isinstance(content, ModelMessage):
        return token_counter.count_message(content)
    return token_counter.count_json(content)


__all__ = ["MicroCompactStrategy"]
