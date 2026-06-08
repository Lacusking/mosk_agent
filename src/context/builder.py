"""AgentRun 上下文构造器。"""

from collections.abc import Sequence

from src.context.budget import DefaultTokenCounter
from src.context.budget import TokenCounter
from src.context.errors import ContextBudgetError
from src.context.pipeline import ContextStrategyPipeline
from src.context.schemas import ContextBudget
from src.context.schemas import ContextBundle
from src.context.schemas import ContextItem
from src.context.schemas import ContextItemType
from src.context.schemas import ContextSource
from src.context.strategies import MicroCompactStrategy
from src.context.strategies import SnipCompactStrategy
from src.context.strategies import ToolResultBudgetStrategy
from src.contracts.agent_runs import AgentRun
from src.contracts.patterns import PatternObservation
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import ToolResultContentBlock
from src.core.config import AgentRuntimeConfig
from src.sessions import SessionManager
from src.sessions.messages import to_model_message


class ContextBuilder:
    """基于 AgentRun 水位构造 Runtime 可见上下文。"""

    def __init__(
        self,
        *,
        session_manager: SessionManager,
        config: AgentRuntimeConfig,
        pipeline: ContextStrategyPipeline | None = None,
        token_counter: TokenCounter | None = None,
    ) -> None:
        """初始化上下文构造器。

        Args:
            session_manager: Session 业务服务。
            config: Agent runtime 配置。
            pipeline: 可选上下文策略管线；未提供时使用默认 snip 管线。
        """
        self._session_manager = session_manager
        self._config = config
        self._token_counter = token_counter or DefaultTokenCounter()
        self._pipeline = pipeline or ContextStrategyPipeline(
            [
                SnipCompactStrategy(
                    threshold_messages=config.CONTEXT_SNIP_THRESHOLD_MESSAGES,
                    head_messages=config.CONTEXT_SNIP_HEAD_MESSAGES,
                    tail_messages=config.CONTEXT_SNIP_TAIL_MESSAGES,
                ),
                MicroCompactStrategy(
                    max_item_tokens=config.CONTEXT_MICRO_ITEM_MAX_TOKENS,
                    token_counter=self._token_counter,
                ),
                ToolResultBudgetStrategy(max_tokens=config.CONTEXT_TOOL_RESULT_BUDGET_TOKENS),
            ]
        )

    async def build(
        self,
        agent_run: AgentRun,
        *,
        observations: Sequence[PatternObservation] | None = None,
        context_window_tokens: int | None = None,
    ) -> ContextBundle:
        """构造 AgentRun 的上下文包。

        Args:
            agent_run: 当前 AgentRun。
            observations: 当前 pattern runtime 中已产生的 observation。
            context_window_tokens: 目标模型 profile 的 context window；为空时使用配置默认值。

        Returns:
            经策略管线处理后的 ContextBundle。
        """
        messages = await self._session_manager.visible_history(
            session_id=agent_run.session_id,
            through_sequence=agent_run.context_message_sequence,
            limit=self._config.CONTEXT_WINDOW_MESSAGES,
        )
        session_items = [
            ContextItem(
                source=ContextSource.SESSION,
                type=ContextItemType.MESSAGE,
                content=model_message,
                priority=0,
                token_count=self._token_counter.count_message(model_message),
                pinned=False,
                evictable=True,
                metadata={
                    "message_id": message.message_id,
                    "sequence": message.sequence,
                    "role": message.role.value,
                },
            )
            for message in messages
            for model_message in [to_model_message(message)]
        ]
        tool_observations = self._tool_observation_items(
            observations or [],
            seen_call_ids=_seen_tool_result_call_ids(
                [item.content for item in session_items if isinstance(item.content, ModelMessage)]
            ),
        )
        max_tokens = context_window_tokens or self._config.CONTEXT_TOKEN_BUDGET
        bundle = ContextBundle(
            agent_run_id=agent_run.agent_run_id,
            session_id=agent_run.session_id,
            session_messages=session_items,
            tool_observations=tool_observations,
            budget=ContextBudget(
                max_messages=self._config.CONTEXT_WINDOW_MESSAGES,
                snip_threshold_messages=self._config.CONTEXT_SNIP_THRESHOLD_MESSAGES,
                snip_head_messages=self._config.CONTEXT_SNIP_HEAD_MESSAGES,
                snip_tail_messages=self._config.CONTEXT_SNIP_TAIL_MESSAGES,
                max_tokens=max_tokens,
                token_reserve=self._config.CONTEXT_TOKEN_RESERVE,
                tool_result_budget_tokens=self._config.CONTEXT_TOOL_RESULT_BUDGET_TOKENS,
                micro_item_max_tokens=self._config.CONTEXT_MICRO_ITEM_MAX_TOKENS,
            ),
        )
        compacted = await self._pipeline.apply(bundle)
        return self._ensure_token_budget(compacted, max_tokens=max_tokens)

    def _tool_observation_items(
        self,
        observations: Sequence[PatternObservation],
        *,
        seen_call_ids: set[str],
    ) -> list[ContextItem]:
        items: list[ContextItem] = []
        for order, observation in enumerate(observations):
            if observation.kind != "tool_result":
                continue
            data = observation.data
            if data.get("is_error") is True:
                continue
            status = data.get("status")
            if isinstance(status, str) and status not in {"success", "completed"}:
                continue
            call_id = data.get("call_id")
            if not isinstance(call_id, str) or call_id in seen_call_ids:
                continue
            content = {
                "call_id": call_id,
                "name": data.get("name"),
                "status": status,
                "observation": data.get("observation"),
                "is_error": False,
            }
            items.append(
                ContextItem(
                    source=ContextSource.TOOL,
                    type=ContextItemType.OBSERVATION,
                    content=content,
                    priority=0,
                    token_count=self._token_counter.count_json(content),
                    pinned=False,
                    evictable=True,
                    metadata={"call_id": call_id, "order": order},
                )
            )
            seen_call_ids.add(call_id)
        return items

    def _ensure_token_budget(self, bundle: ContextBundle, *, max_tokens: int) -> ContextBundle:
        available_tokens = max_tokens - self._config.CONTEXT_TOKEN_RESERVE
        current = _refresh_used_tokens(bundle, self._token_counter)
        if current.budget is None or current.budget.used_tokens <= available_tokens:
            return current

        current = _drop_until_budget(
            current,
            available_tokens=available_tokens,
            token_counter=self._token_counter,
        )
        if current.budget is not None and current.budget.used_tokens <= available_tokens:
            return current
        used = current.budget.used_tokens if current.budget else 0
        raise ContextBudgetError(
            msg="上下文无法满足 token 预算",
            data={
                "used_tokens": used,
                "available_tokens": available_tokens,
                "max_tokens": max_tokens,
            },
        )


def _refresh_used_tokens(bundle: ContextBundle, token_counter: TokenCounter) -> ContextBundle:
    used = 0
    for item in _all_items(bundle):
        if item.token_count is None:
            content = item.content
            token_count = (
                token_counter.count_message(content)
                if isinstance(content, ModelMessage)
                else token_counter.count_json(content)
            )
            item = item.model_copy(update={"token_count": token_count})
        used += item.token_count or 0
    budget = (bundle.budget or ContextBudget()).model_copy(update={"used_tokens": used})
    return bundle.model_copy(update={"budget": budget})


def _drop_until_budget(
    bundle: ContextBundle,
    *,
    available_tokens: int,
    token_counter: TokenCounter,
) -> ContextBundle:
    current = bundle
    last_session = current.session_messages[-1] if current.session_messages else None
    candidates = sorted(
        [
            ("session_messages", index, item)
            for index, item in enumerate(current.session_messages)
            if item.evictable and not item.pinned and item != last_session
        ]
        + [
            ("tool_observations", index, item)
            for index, item in enumerate(current.tool_observations)
            if item.evictable and not item.pinned
        ]
        + [
            ("artifacts", index, item)
            for index, item in enumerate(current.artifacts)
            if item.evictable and not item.pinned
        ],
        key=lambda entry: (
            entry[2].priority,
            int(entry[2].metadata.get("order", entry[2].sequence or 0)),
        ),
    )
    evicted = list(current.evicted_items)
    for slot, index, item in candidates:
        if current.budget is not None and current.budget.used_tokens <= available_tokens:
            break
        values = list(getattr(current, slot))
        if index >= len(values) or values[index] != item:
            continue
        del values[index]
        evicted.append(item)
        current = current.model_copy(update={slot: values, "evicted_items": evicted})
        current = _refresh_used_tokens(current, token_counter)
    return current


def _all_items(bundle: ContextBundle) -> list[ContextItem]:
    items = [*bundle.session_messages, *bundle.tool_observations, *bundle.artifacts]
    if bundle.memory_summary is not None:
        items.append(bundle.memory_summary)
    return items


def _seen_tool_result_call_ids(messages: list[ModelMessage]) -> set[str]:
    seen: set[str] = set()
    for message in messages:
        for block in message.content:
            if isinstance(block, ToolResultContentBlock):
                seen.add(block.call_id)
    return seen


__all__ = ["ContextBuilder"]
