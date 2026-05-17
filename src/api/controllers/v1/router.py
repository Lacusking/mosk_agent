"""
v1 路由汇聚
"""

from fastapi import APIRouter

from src.api.controllers.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/api/v1", tags=["health"])
