from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from app.models.enums import ProgramStatus


class Program(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "programs"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("learning_sources.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("generation_tasks.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 结构化讲稿（JSON 字符串）：分段、来源标记、知识点、回忆题
    transcript_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 稳定音色键 + 实际供应商音色快照
    voice_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tts_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_voice_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # 音频只存受控对象键，不存公开路径
    audio_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audio_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default=ProgramStatus.GENERATING.value, index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    user = relationship("User", back_populates="programs")
    task = relationship("GenerationTask", back_populates="programs")
    knowledge_points = relationship(
        "KnowledgePoint",
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="KnowledgePoint.position",
    )
    recall_questions = relationship(
        "RecallQuestion",
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="RecallQuestion.position",
    )
