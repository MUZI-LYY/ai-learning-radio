from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from app.models.enums import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    display_name: Mapped[str] = mapped_column(String(100), default="同学")
    role: Mapped[str] = mapped_column(String(16), default=UserRole.USER.value, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    learning_sources = relationship(
        "LearningSource", back_populates="user", cascade="all, delete-orphan"
    )
    generation_tasks = relationship(
        "GenerationTask", back_populates="user", cascade="all, delete-orphan"
    )
    programs = relationship("Program", back_populates="user", cascade="all, delete-orphan")
    news_favorites = relationship(
        "NewsFavorite", back_populates="user", cascade="all, delete-orphan"
    )
