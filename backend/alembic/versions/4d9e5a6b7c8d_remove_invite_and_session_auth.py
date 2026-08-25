"""remove invite and session authentication tables

Revision ID: 4d9e5a6b7c8d
Revises: 3e1f2a4b5c6d
Create Date: 2026-08-25 21:45:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4d9e5a6b7c8d"
down_revision: Union[str, Sequence[str], None] = "3e1f2a4b5c6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove tables that are no longer used by the local single-user app."""
    table_names = set(sa.inspect(op.get_bind()).get_table_names())
    if "sessions" in table_names:
        op.drop_table("sessions")
    if "invite_credentials" in table_names:
        op.drop_table("invite_credentials")


def downgrade() -> None:
    """Restore the former invite and session tables for rollback compatibility."""
    table_names = set(sa.inspect(op.get_bind()).get_table_names())
    if "invite_credentials" not in table_names:
        op.create_table(
            "invite_credentials",
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("code_digest", sa.String(length=64), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_invite_credentials_code_digest",
            "invite_credentials",
            ["code_digest"],
            unique=True,
        )
        op.create_index(
            "ix_invite_credentials_user_id",
            "invite_credentials",
            ["user_id"],
            unique=False,
        )

    if "sessions" not in table_names:
        op.create_table(
            "sessions",
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("token_digest", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"], unique=False)
        op.create_index(
            "ix_sessions_token_digest", "sessions", ["token_digest"], unique=True
        )
        op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)
