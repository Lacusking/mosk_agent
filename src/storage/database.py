"""
SQLAlchemy 异步数据库初始化

提供异步引擎、会话工厂与会话获取函数。
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.config import settings

logger = logging.getLogger(__name__)


def create_async_engine_and_session() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """
    创建异步数据库引擎与会话工厂。

    Returns:
        (engine, session_factory) 元组。
    """
    try:
        engine = create_async_engine(
            settings.db.database_url,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
            pool_use_lifo=True,
        )
    except Exception as e:
        logger.error("数据库连接失败: %s", e)
        raise

    db_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )
    return engine, db_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话（手动管理事务）。

    Yields:
        AsyncSession 实例。
    """
    async with async_db_session() as session:
        yield session


async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    获取带事务的数据库会话（自动 commit / rollback）。

    Yields:
        AsyncSession 实例。
    """
    async with async_db_session.begin() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async_engine, async_db_session = create_async_engine_and_session()
