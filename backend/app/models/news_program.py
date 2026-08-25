from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin


class NewsProgram(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """每日新闻共享节目（同频道所有用户共享同一份）。"""

    __tablename__ = "news_programs"
    __table_args__ = (UniqueConstraint("channel", "program_date", name="uq_news_channel_date"),)

    channel: Mapped[str] = mapped_column(String(32), index=True)
    # Asia/Shanghai 日期 YYYY-MM-DD
    program_date: Mapped[str] = mapped_column(String(10), index=True)
    title: Mapped[str] = mapped_column(String(255))
    # 结构化脚本（JSON）：摘要、新闻条目、来源链接
    transcript_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    voice_key: Mapped[str] = mapped_column(String(64))
    tts_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_voice_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    audio_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="generating", index=True)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    favorites = relationship(
        "NewsFavorite", back_populates="program", cascade="all, delete-orphan"
    )
