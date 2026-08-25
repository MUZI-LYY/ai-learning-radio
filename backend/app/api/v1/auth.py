"""邀请码登录与注销。"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.api.deps import CurrentUser, DbSession, client_ip, get_rate_limiter
from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.models.analytics_event import AnalyticsEvent
from app.schemas.auth import AuthResponse, InviteRequest, UserSummary
from app.services.auth.invite import verify_invite_code
from app.services.auth.session import COOKIE_NAME, create_session, revoke_session

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.post("/invite", response_model=AuthResponse)
def invite(
    body: InviteRequest, request: Request, response: Response, db: DbSession
) -> AuthResponse:
    settings = get_settings()
    limiter = get_rate_limiter()
    if not limiter.allow(client_ip(request)):
        raise ApiError(ErrorCode.RATE_LIMITED)

    user, error_code = verify_invite_code(db, body.invite_code, settings.invite_code_pepper)
    if error_code is not None:
        raise ApiError(error_code)

    token, _ = create_session(
        db, user.id, settings.session_ttl_seconds, settings.app_secret
    )
    db.add(AnalyticsEvent(user_id=user.id, event_name="invite_verified"))
    db.commit()

    _set_session_cookie(response, token)
    return AuthResponse(
        user=UserSummary(id=user.id, display_name=user.display_name, role=user.role)
    )


@router.post("/logout")
def logout(request: Request, response: Response, db: DbSession, _: CurrentUser) -> dict:
    token = request.cookies.get(COOKIE_NAME, "")
    if token:
        revoke_session(db, token, get_settings().app_secret)
        db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}
