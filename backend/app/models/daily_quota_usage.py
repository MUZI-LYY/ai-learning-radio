from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DailyQuotaUsage(Base):
    """每日额度使用记录，按 Asia/Shanghai 日期计算。

    复合主键 (user_id, usage_date)，创建任务时原子扣减。
    """

    __tablename__ = "daily_quota_usage"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    usage_date: Mapped[str] = mapped_column(String(10), primary_key=True)  # YYYY-MM-DD
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    bonus_count: Mapped[int] = mapped_column(Integer, default=0)
