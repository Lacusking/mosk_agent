"""AgentRun 上下文构造器。"""

from src.context.budget import estimate_message_tokens
from src.context.pipeline import ContextStrategyPipeline
from src.context.schemas import ContextBudget
from src.context.schemas import ContextBundle
from src.context.schemas import ContextItem
from src.context.schemas import ContextItemType
from src.context.schemas import ContextSource
from src.context.strategies import SnipCompactStrategy
from src.contracts.agent_runs import AgentRun
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
    ) -> None:
        """初始化上下文构造器。

        Args:
            session_manager: Session 业务服务。
            config: Agent runtime 配置。
            pipeline: 可选上下文策略管线；未提供时使用默认 snip 管线。
        """
        self._session_manager = session_manager
        self._config = config
        self._pipeline = pipeline or ContextStrategyPipeline(
            [
                SnipCompactStrategy(
                    threshold_messages=config.CONTEXT_SNIP_THRESHOLD_MESSAGES,
                    head_messages=config.CONTEXT_SNIP_HEAD_MESSAGES,
                    tail_messages=config.CONTEXT_SNIP_TAIL_MESSAGES,
                )
            ]
        )

    async def build(self, agent_run: AgentRun) -> ContextBundle:
        """构造 AgentRun 的上下文包。

        Args:
            agent_run: 当前 AgentRun。

        Returns:
            经策略管线处理后的 ContextBundle。
        """
        messages = await self._session_manager.visible_history(
            session_id=agent_run.session_id,
            through_sequence=agent_run.context_message_sequence,
            limit=self._config.CONTEXT_WINDOW_MESSAGES,
        )
        items = [
            ContextItem(
                source=ContextSource.SESSION,
                type=ContextItemType.MESSAGE,
                content=model_message,
                priority=0,
                token_count=estimate_message_tokens(model_message),
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
        bundle = ContextBundle(
            agent_run_id=agent_run.agent_run_id,
            session_id=agent_run.session_id,
            session_messages=items,
            budget=ContextBudget(
                max_messages=self._config.CONTEXT_WINDOW_MESSAGES,
                snip_threshold_messages=self._config.CONTEXT_SNIP_THRESHOLD_MESSAGES,
                snip_head_messages=self._config.CONTEXT_SNIP_HEAD_MESSAGES,
                snip_tail_messages=self._config.CONTEXT_SNIP_TAIL_MESSAGES,
            ),
        )
        return await self._pipeline.apply(bundle)


__all__ = ["ContextBuilder"]
