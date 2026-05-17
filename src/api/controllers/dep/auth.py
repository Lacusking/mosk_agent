"""
鉴权依赖
"""

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials

from src.core.config import settings
from src.core.errors import AuthenticationError
from src.core.errors import ForbiddenError


class InternalHTTPBearer(HTTPBearer):
    """内部服务 token 鉴权。"""

    def __init__(self) -> None:
        super().__init__(auto_error=False)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        if not getattr(settings.app, "INTERNAL_AUTH_TOKEN", None):
            return None

        expected_token = settings.app.INTERNAL_AUTH_TOKEN  # type: ignore[attr-defined]

        try:
            security = await super().__call__(request)
            if not security or security.credentials != expected_token:
                raise ForbiddenError(msg="Token无效")
            return security
        except HTTPException as e:
            if e.status_code == 401:
                raise AuthenticationError(msg="Token无效") from e
            if e.status_code == 403:
                raise ForbiddenError(msg="无权限") from e
            raise


InternalAuth = Depends(InternalHTTPBearer())
