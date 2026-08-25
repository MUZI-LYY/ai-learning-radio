"""创建用户并生成邀请码（MVP 管理员 CLI）。

用法（在 backend/ 目录下）：
    uv run python -m scripts.create_invite --name "同学A"
    uv run python -m scripts.create_invite --name "同学A" --role admin --code "自定义长随机码"

邀请码只保存加 pepper 的摘要，明文仅在创建时打印一次。
"""

from __future__ import annotations

import argparse

from app.core.config import get_settings
from app.core.security import generate_invite_code, hash_credential
from app.db.session import get_session_factory
from app.models.enums import UserRole
from app.models.invite_credential import InviteCredential
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(description="创建用户并生成邀请码")
    parser.add_argument("--name", default="同学", help="用户展示名")
    parser.add_argument("--role", default=UserRole.USER.value, choices=["user", "admin"])
    parser.add_argument("--code", default=None, help="指定邀请码；不指定则自动生成随机码")
    args = parser.parse_args()

    settings = get_settings()
    code = args.code or generate_invite_code()
    factory = get_session_factory()
    with factory() as db:
        user = User(display_name=args.name, role=args.role)
        db.add(user)
        db.flush()
        db.add(
            InviteCredential(
                user_id=user.id,
                code_digest=hash_credential(code, settings.invite_code_pepper),
            )
        )
        db.commit()

    print("邀请码（仅显示一次，请妥善保存）:")
    print(code)
    print(f"用户 ID: {user.id}，展示名: {args.name}，角色: {args.role}")


if __name__ == "__main__":
    main()
