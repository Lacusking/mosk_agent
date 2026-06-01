"""
v1 路由汇聚
"""

from fastapi import APIRouter

from src.api.controllers.v1 import agent_runs
from src.api.controllers.v1 import health
from src.api.controllers.v1 import sessions

api_router = APIRouter()
api_router.include_router(health.router, prefix="/api/v1", tags=["health"])
api_router.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
api_router.include_router(agent_runs.router, prefix="/api/v1", tags=["agent-runs"])
