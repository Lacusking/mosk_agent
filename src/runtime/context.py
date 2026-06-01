"""AgentRun 模型上下文构造。"""

from src.contracts.runtime import ModelMessage
from src.sessions import SessionManager


class RuntimeContextBuilder:
    """基于 Session 固定水位构造模型上下文。"""

    def __init__(self, session_manager: SessionManager) -> None:
        """初始化上下文构造器。

        Args:
            session_manager: Session 编排服务。
        """
        self._session_manager = session_manager

    async def visible_context(
        self,
        *,
        session_id: str,
        context_message_sequence: int,
    ) -> list[ModelMessage]:
        """读取 AgentRun 创建时固定水位内的可见上下文。

        Args:
            session_id: Session id。
            context_message_sequence: AgentRun 上下文水位。

        Returns:
            模型输入消息列表。
        """
        return await self._session_manager.model_context(
            session_id=session_id,
            through_sequence=context_message_sequence,
        )


__all__ = ["RuntimeContextBuilder"]
