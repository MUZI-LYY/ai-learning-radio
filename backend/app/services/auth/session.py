"""会话创建与校验。

浏览器只持有 HttpOnly Cookie 中的原始令牌；服务端保存令牌摘要。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import generate_session_token, hash_credential
from app.models.session import Session as SessionModel
from app.models.user import User

COOKIE_NAME = "ai_radio_session"


def create_session(
    db: Session, user_id: str, ttl_seconds: int, pepper: str
) -> tuple[str, SessionModel]:
    """创建会话记录，返回 (原始令牌, 会话模型)。原始令牌只返回这一次。"""
    token = generate_session_token()
    now = datetime.now(UTC)
    session_model = SessionModel(
        user_id=user_id,
        token_digest=hash_credential(token, pepper),
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    db.add(session_model)
    db.flush()
    return token, session_model


def get_user_by_token(db: Session, token: str, pepper: str) -> User | None:
    """按原始令牌解析有效用户；令牌无效、过期或已作废均返回 None。"""
    if not token:
        return None
    digest = hash_credential(token, pepper)
    now = datetime.now(UTC)
    session_model = db.execute(
        select(SessionModel).where(SessionModel.token_digest == digest)
    ).scalar_one_or_none()
    if session_model is None or session_model.revoked_at is not None:
        return None
    if session_model.expires_at <= now:
        return None
    user = db.get(User, session_model.user_id)
    if user is None or user.deleted_at is not None:
        return None
    return user


def revoke_session(db: Session, token: str, pepper: str) -> None:
    """作废指定会话。"""
    if not token:
        return
    digest = hash_credential(token, pepper)
    session_model = db.execute(
        select(SessionModel).where(SessionModel.token_digest == digest)
    ).scalar_one_or_none()
    if session_model is not None and session_model.revoked_at is None:
        session_model.revoked_at = datetime.now(UTC)
        db.flush()
