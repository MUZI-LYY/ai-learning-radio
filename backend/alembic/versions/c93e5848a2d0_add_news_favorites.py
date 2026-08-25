"""add news favorites

Revision ID: c93e5848a2d0
Revises: 7a21c61ad114
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c93e5848a2d0"  # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = "7a21c61ad114"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "news_favorites",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("program_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["news_programs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "program_id", name="uq_news_favorite_user_program"),
    )
    op.create_index("ix_news_favorites_program_id", "news_favorites", ["program_id"])
    op.create_index("ix_news_favorites_user_id", "news_favorites", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_news_favorites_user_id", table_name="news_favorites")
    op.drop_index("ix_news_favorites_program_id", table_name="news_favorites")
    op.drop_table("news_favorites")
