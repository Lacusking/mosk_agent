"""Session 业务编排服务。"""

from collections.abc import Sequence

from src.contracts.runtime import ModelContentBlock
from src.contracts.runtime import ModelMessage
from src.contracts.sessions import CreateSessionRequest
from src.contracts.sessions import Session
from src.contracts.sessions import SessionMessage
from src.contracts.sessions import SessionMessageRole
from src.exceptions import NotFoundError
from src.sessions.messages import assistant_text_content
from src.sessions.messages import to_model_messages
from src.sessions.messages import user_text_content
from src.storage.database.repositories.sessions import SessionRepository


class SessionManager:
    """协调 Session 创建、历史读取与可见消息提交。"""

    def __init__(self, repository: SessionRepository) -> None:
        """初始化 manager。

        Args:
            repository: Session 持久化访问对象。
        """
        self._repository = repository

    async def create_session(self, request: CreateSessionRequest) -> Session:
        """创建会话。

        Args:
            request: 创建 Session 请求。

        Returns:
            创建后的 Session。
        """
        return await self._repository.create_session(
            title=request.title,
            metadata=request.metadata,
        )

    async def require_session(self, session_id: str) -> Session:
        """读取会话，不存在则抛出 NotFoundError。

        Args:
            session_id: 会话 id。

        Returns:
            Session 契约对象。

        Raises:
            NotFoundError: 会话不存在。
        """
        session = await self._repository.get_session(session_id)
        if session is None:
            raise NotFoundError(msg="Session 不存在", data={"session_id": session_id})
        return session

    async def append_user_text(self, *, session_id: str, text: str) -> SessionMessage:
        """追加用户可见文本消息。

        Args:
            session_id: 会话 id。
            text: 用户输入。

        Returns:
            新增消息。
        """
        role, content = user_text_content(text)
        return await self.append_message(session_id=session_id, role=role, content=content)

    async def append_final_assistant_text(
        self,
        *,
        session_id: str,
        agent_run_id: str,
        text: str,
    ) -> SessionMessage:
        """仅在 run 成功完成后追加 assistant 最终文本。

        Args:
            session_id: 会话 id。
            agent_run_id: 产生该输出的 AgentRun id。
            text: 最终 assistant 文本。

        Returns:
            新增消息。
        """
        role, content = assistant_text_content(text)
        return await self.append_message(
            session_id=session_id,
            role=role,
            content=content,
            agent_run_id=agent_run_id,
        )

    async def append_message(
        self,
        *,
        session_id: str,
        role: SessionMessageRole,
        content: Sequence[ModelContentBlock],
        agent_run_id: str | None = None,
    ) -> SessionMessage:
        """追加一条用户可见消息。

        Args:
            session_id: 会话 id。
            role: user 或 assistant。
            content: 可见内容块。
            agent_run_id: 可选关联 AgentRun。

        Returns:
            新增消息。
        """
        return await self._repository.append_message(
            session_id=session_id,
            role=role,
            content=content,
            agent_run_id=agent_run_id,
        )

    async def visible_history(
        self,
        *,
        session_id: str,
        through_sequence: int | None = None,
        limit: int | None = None,
    ) -> list[SessionMessage]:
        """读取会话可见历史。

        Args:
            session_id: 会话 id。
            through_sequence: 可选上下文水位。
            limit: 可选最近消息数量限制。

        Returns:
            按 sequence 升序排列的 SessionMessage 列表。
        """
        await self.require_session(session_id)
        return await self._repository.list_messages(
            session_id,
            through_sequence=through_sequence,
            limit=limit,
        )

    async def model_context(
        self,
        *,
        session_id: str,
        through_sequence: int,
        limit: int | None = None,
    ) -> list[ModelMessage]:
        """读取固定水位下的模型上下文。

        Args:
            session_id: 会话 id。
            through_sequence: AgentRun 创建时固定的上下文水位。
            limit: 可选最近消息数量限制。

        Returns:
            可交给模型 adapter 的消息列表。
        """
        messages = await self.visible_history(
            session_id=session_id,
            through_sequence=through_sequence,
            limit=limit,
        )
        return to_model_messages(messages)


__all__ = ["SessionManager"]
