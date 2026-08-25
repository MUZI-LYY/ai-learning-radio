from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin


class NewsArticle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """抓取到的新闻文章，按 URL 去重。"""

    __tablename__ = "news_articles"

    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("news_sources.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String(32), index=True)
    url: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    content_is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
