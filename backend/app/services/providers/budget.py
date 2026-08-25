"""Provider 预算熔断与用量账本。

每次真实 Provider 调用前由确定性代码检查开关与当月预算；达到上限立即熔断。
调用后记录实际用量；供应商未立即返回费用时按配置单价计算保守估值。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.models.provider_usage import ProviderUsage


def _month_start_utc() -> datetime:
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def check_budget(db: Session) -> None:
    """真实 Provider 调用前检查；未允许或超预算时抛 BUDGET_BLOCKED。"""
    settings = get_settings()
    if not settings.real_provider_allowed:
        raise ApiError(ErrorCode.BUDGET_BLOCKED, "真实服务调用未开启或月度预算未配置。")

    total = db.execute(
        select(func.coalesce(func.sum(ProviderUsage.estimated_cost_cny), 0.0)).where(
            ProviderUsage.created_at >= _month_start_utc()
        )
    ).scalar_one()
    if total >= settings.project_monthly_budget_cny:
        raise ApiError(ErrorCode.BUDGET_BLOCKED, "本月预算已达上限，暂停真实生成。")


def estimate_tts_cost(input_chars: int) -> float:
    """按配置单价保守估算 TTS 费用（元）。计费单价待供应商确认后校准。"""
    price = get_settings().tts_cost_per_1k_chars_cny
    return round(input_chars / 1000.0 * price, 6)


def record_usage(
    db: Session,
    *,
    provider: str,
    model: str,
    operation: str,
    input_units: int = 0,
    output_units: int = 0,
    estimated_cost_cny: float = 0.0,
    actual_cost_cny: float | None = None,
    task_id: str | None = None,
) -> ProviderUsage:
    usage = ProviderUsage(
        task_id=task_id,
        provider=provider,
        model=model,
        operation=operation,
        input_units=input_units,
        output_units=output_units,
        estimated_cost_cny=estimated_cost_cny,
        actual_cost_cny=actual_cost_cny,
    )
    db.add(usage)
    db.flush()
    return usage
