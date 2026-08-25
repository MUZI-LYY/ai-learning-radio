from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin


class LearningSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_sources"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    original_name: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(16))
    size_bytes: Mapped[int] = mapped_column(Integer)
    # 提取后的私有正文
    text: Mapped[str] = mapped_column(Text)
    text_sha256: Mapped[str] = mapped_column(String(64), index=True)
    # 解析清理后置空；只在解析成功前暂存原始上传文件路径
    raw_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    user = relationship("User", back_populates="learning_sources")
    generation_tasks = relationship("GenerationTask", back_populates="source")
