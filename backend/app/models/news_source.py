from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NewsSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """可信新闻源配置。"""

    __tablename__ = "news_sources"

    name: Mapped[str] = mapped_column(String(100))
    channel: Mapped[str] = mapped_column(String(32), index=True)
    url: Mapped[str] = mapped_column(String(500))
    # mock | rss | http
    kind: Mapped[str] = mapped_column(String(16), default="rss")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
