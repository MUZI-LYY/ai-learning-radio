"""FastAPI 依赖：数据库会话、当前用户、限流器。"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.db.session import get_session
from app.models.user import User
from app.services.auth.rate_limit import SlidingWindowRateLimiter
from app.services.auth.session import COOKIE_NAME, get_user_by_token

DbSession = Annotated[Session, Depends(get_session)]


def get_current_user(request: Request, db: DbSession) -> User:
    """从会话 Cookie 解析当前用户；无效/过期/越权统一返回 UNAUTHORIZED。"""
    token = request.cookies.get(COOKIE_NAME, "")
    settings = get_settings()
    user = get_user_by_token(db, token, settings.app_secret)
    if user is None:
        raise ApiError(ErrorCode.UNAUTHORIZED)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@lru_cache
def get_rate_limiter() -> SlidingWindowRateLimiter:
    settings = get_settings()
    return SlidingWindowRateLimiter(
        window_seconds=settings.invite_rate_limit_window_seconds,
        max_attempts=settings.invite_rate_limit_max_attempts,
    )


def client_ip(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host
