"""
健康检查端点
"""

from fastapi import APIRouter

from src.api.response import response_base

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """
    健康检查端点。

    Returns:
        统一响应结构 {code, msg, data}。
    """
    return response_base.success(data={"status": "healthy"}).model_dump()
