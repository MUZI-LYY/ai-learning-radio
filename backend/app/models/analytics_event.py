from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AnalyticsEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """只允许 PRD 定义的必要匿名事件。"""

    __tablename__ = "analytics_events"

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_name: Mapped[str] = mapped_column(String(64), index=True)
    program_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("programs.id", ondelete="SET NULL"), nullable=True
    )
