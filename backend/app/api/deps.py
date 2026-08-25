"""FastAPI 依赖：数据库会话与本地用户。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models.user import User

DbSession = Annotated[Session, Depends(get_session)]
LOCAL_USER_ID = "00000000-0000-0000-0000-000000000001"


def get_current_user(db: DbSession) -> User:
    """返回本地单用户；首次访问时自动创建。"""
    user = db.execute(
        select(User)
        .where(User.deleted_at.is_(None))
        .order_by(User.created_at.asc(), User.id.asc())
        .limit(1)
    ).scalar_one_or_none()
    if user is not None:
        return user

    user = db.get(User, LOCAL_USER_ID)
    if user is None:
        user = User(id=LOCAL_USER_ID, display_name="本地用户")
        db.add(user)
    else:
        user.deleted_at = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        user = db.get(User, LOCAL_USER_ID)
        if user is None:
            raise
    db.refresh(user)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
