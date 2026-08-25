from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProviderUsage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """记录 LLM/TTS 用量和费用，不保存私人输入原文。"""

    __tablename__ = "provider_usage"

    task_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("generation_tasks.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    operation: Mapped[str] = mapped_column(String(64))
    input_units: Mapped[int] = mapped_column(Integer, default=0)
    output_units: Mapped[int] = mapped_column(Integer, default=0)
    # 供应商未立即返回费用时按配置单价计算保守估值
    estimated_cost_cny: Mapped[float] = mapped_column(Float, default=0.0)
    actual_cost_cny: Mapped[float | None] = mapped_column(Float, nullable=True)
