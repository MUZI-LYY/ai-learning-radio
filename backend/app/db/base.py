"""SQLAlchemy 声明式基类与通用 Mixin。

所有主键使用不可猜测的 UUID 字符串，时间统一存 UTC。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import DateTime, TypeDecorator


def utcnow() -> datetime:
    return datetime.now(UTC)


def uuid_str() -> str:
    return str(uuid.uuid4())


class UTCDateTime(TypeDecorator):
    """带时区的 DateTime：写入时统一转 UTC，读取时始终返回 tz-aware UTC。

    SQLite 不保存时区信息，本类型保证读写一致；迁移到 PostgreSQL 后行为不变。
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ANN001, ARG002
        if value is not None and value.tzinfo is not None:
            return value.astimezone(UTC)
        return value

    def process_result_value(self, value, dialect):  # noqa: ANN001, ARG002
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""


class UUIDPrimaryKeyMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)
