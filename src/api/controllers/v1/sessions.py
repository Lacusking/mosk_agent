"""Session API 路由。"""

from fastapi import APIRouter

from src.api.controllers.dep.auth import InternalAuth
from src.api.controllers.dep.db_session import CurrentSessionTransaction
from src.api.response import ResponseModel
from src.api.response import response_base
from src.contracts.sessions import CreateSessionRequest
from src.contracts.sessions import SessionMessagesResponse
from src.contracts.sessions import SessionResponse
from src.sessions import SessionManager
from src.storage.database.repositories.sessions import SessionRepository

router = APIRouter(dependencies=[InternalAuth])


@router.post("/sessions")
async def create_session(
    request: CreateSessionRequest,
    db: CurrentSessionTransaction,
) -> dict:
    """创建 Session。

    Args:
        request: 创建请求。
        db: 事务数据库会话。

    Returns:
        统一响应结构。
    """
    manager = SessionManager(SessionRepository(db))
    session = await manager.create_session(request)
    return response_base.success(data=SessionResponse(session=session)).model_dump()


@router.get("/sessions/{session_id}", response_model=ResponseModel[SessionResponse])
async def get_session(session_id: str, db: CurrentSessionTransaction):
    """读取 Session。

    Args:
        session_id: Session id。
        db: 事务数据库会话。

    Returns:
        统一响应结构。
    """
    manager = SessionManager(SessionRepository(db))
    session = await manager.require_session(session_id)
    return response_base.success(data=SessionResponse(session=session))


@router.get("/sessions/{session_id}/messages", response_model=ResponseModel[SessionMessagesResponse])
async def get_session_messages(session_id: str, db: CurrentSessionTransaction) -> dict:
    """读取 Session 可见消息历史。

    Args:
        session_id: Session id。
        db: 事务数据库会话。

    Returns:
        统一响应结构。
    """
    manager = SessionManager(SessionRepository(db))
    messages = await manager.visible_history(session_id=session_id)
    return response_base.success(
        data=SessionMessagesResponse(session_id=session_id, messages=messages)
    )

__all__ = ["router"]
