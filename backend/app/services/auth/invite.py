"""邀请码验证。

只保存加 pepper 的摘要，验证时先算摘要再查询，避免明文入库。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ErrorCode
from app.core.security import hash_credential, verify_credential
from app.models.invite_credential import InviteCredential
from app.models.user import User


def _load_user_by_invite_digest(session: Session, digest: str) -> User | None:
    row = session.execute(
        select(InviteCredential, User)
        .join(User, User.id == InviteCredential.user_id)
        .where(InviteCredential.code_digest == digest)
    ).first()
    if row is None:
        return None
    return row.User


def verify_invite_code(
    session: Session, code: str, pepper: str
) -> tuple[User | None, str | None]:
    """验证邀请码，返回 (用户, 错误码)。错误码用于区分「无效」与「已作废」。"""
    digest = hash_credential(code, pepper)
    credential = session.execute(
        select(InviteCredential).where(InviteCredential.code_digest == digest)
    ).scalar_one_or_none()
    if credential is None:
        return None, ErrorCode.INVALID_INVITE
    if credential.revoked_at is not None:
        return None, ErrorCode.REVOKED_INVITE

    user = session.get(User, credential.user_id)
    if user is None or user.deleted_at is not None:
        return None, ErrorCode.INVALID_INVITE

    # 常量时间再校验一次摘要，防止时序差异泄露是否存在该摘要
    if not verify_credential(code, credential.code_digest, pepper):
        return None, ErrorCode.INVALID_INVITE
    return user, None
