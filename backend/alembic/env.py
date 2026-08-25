"""Alembic 迁移环境。

- 从应用配置读取 DATABASE_URL，避免在 alembic.ini 中硬编码。
- 自动导入所有 ORM 模型，保证 autogenerate 能发现全部表。
- SQLite 下启用外键约束。
"""

from __future__ import annotations

from logging.config import fileConfig

import app.models  # noqa: F401  # 注册所有模型到 Base.metadata
from alembic import context
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import build_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = build_engine(_get_url())
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
