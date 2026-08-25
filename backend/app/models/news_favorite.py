from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NewsFavorite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """用户收藏的共享每日资讯节目。"""

    __tablename__ = "news_favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "program_id", name="uq_news_favorite_user_program"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    program_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("news_programs.id", ondelete="CASCADE"), index=True
    )

    user = relationship("User", back_populates="news_favorites")
    program = relationship("NewsProgram", back_populates="favorites")
