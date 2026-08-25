from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin
from app.models.enums import StepStatus


class TaskStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "task_steps"

    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generation_tasks.id", ondelete="CASCADE"), index=True
    )
    step_name: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), default=StepStatus.PENDING.value, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    # 用于判断是否可复用已有结果（高成本步骤不重复调用）
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 步骤产出的结构化结果（JSON 字符串）
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    task = relationship("GenerationTask", back_populates="steps")
