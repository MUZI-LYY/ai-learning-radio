from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from app.models.enums import TaskStatus


class GenerationTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "generation_tasks"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("learning_sources.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default=TaskStatus.QUEUED.value, index=True)
    current_step: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # 用户提交的「这次特别想理解什么」
    focus: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 创建时冻结所选音色；任务恢复与 TTS 重试始终使用该音色
    voice_key: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    user = relationship("User", back_populates="generation_tasks")
    source = relationship("LearningSource", back_populates="generation_tasks")
    steps = relationship(
        "TaskStep",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskStep.created_at",
    )
    programs = relationship("Program", back_populates="task")
