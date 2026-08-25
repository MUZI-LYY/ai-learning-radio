"""add article reading fields

Revision ID: 7a21c61ad114
Revises: f211a45e3d6e
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "7a21c61ad114"
down_revision: Union[str, Sequence[str], None] = "f211a45e3d6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("news_articles") as batch_op:
        batch_op.add_column(sa.Column("summary", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("image_url", sa.String(length=1000), nullable=True))
        batch_op.add_column(
            sa.Column(
                "content_is_complete", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("news_articles") as batch_op:
        batch_op.drop_column("content_is_complete")
        batch_op.drop_column("image_url")
        batch_op.drop_column("summary")
