"""add news agent trace fields

Revision ID: 3e1f2a4b5c6d
Revises: c93e5848a2d0
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "3e1f2a4b5c6d"  # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = "c93e5848a2d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("news_programs") as batch_op:
        batch_op.add_column(sa.Column("agent_version", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("prompt_version", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("llm_model", sa.String(length=128), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("news_programs") as batch_op:
        batch_op.drop_column("llm_model")
        batch_op.drop_column("prompt_version")
        batch_op.drop_column("agent_version")
