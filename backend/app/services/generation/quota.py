"""每日额度计算。

额度按 Asia/Shanghai 日期计算。第一阶段每人每天最多 2 期私人节目；
管理员可以为指定用户增加额度（bonus_count）。
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.daily_quota_usage import DailyQuotaUsage

_SHANGHAI = ZoneInfo("Asia/Shanghai")


def shanghai_today() -> str:
    return datetime.now(_SHANGHAI).strftime("%Y-%m-%d")


def get_quota_record(db: Session, user_id: str, usage_date: str | None = None) -> DailyQuotaUsage:
    """读取当日额度记录；不存在则返回未持久化的空记录。"""
    usage_date = usage_date or shanghai_today()
    record = db.execute(
        select(DailyQuotaUsage).where(
            DailyQuotaUsage.user_id == user_id,
            DailyQuotaUsage.usage_date == usage_date,
        )
    ).scalar_one_or_none()
    if record is None:
        record = DailyQuotaUsage(
            user_id=user_id, usage_date=usage_date, used_count=0, bonus_count=0
        )
    return record


def quota_limit() -> int:
    return get_settings().daily_private_program_limit


def remaining_quota(db: Session, user_id: str) -> int:
    record = get_quota_record(db, user_id)
    return max(0, quota_limit() + record.bonus_count - record.used_count)
