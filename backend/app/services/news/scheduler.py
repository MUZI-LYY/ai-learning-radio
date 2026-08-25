"""每日新闻定时生成。

真实模式下由显式定时任务触发，避免 Worker 启动时意外产生费用；
mock 模式下 Worker 会自动补齐今日缺失的节目，便于本地测试。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.news_program import NewsProgram
from app.models.news_source import NewsSource
from app.services.generation.quota import shanghai_today
from app.services.news.channels import CHANNELS
from app.services.news.generation import generate_news_for_channel


def _mock_mode() -> bool:
    settings = get_settings()
    return settings.llm_provider == "mock" and settings.tts_provider == "mock"


async def ensure_daily_news(db: Session) -> int:
    """补齐今日缺失的新闻节目；返回本次生成的节目数。仅 mock 模式自动执行。"""
    if not _mock_mode():
        return 0

    # 开发便利：mock 模式下若未配置新闻源，自动补 2 个 mock 源
    has_sources = db.execute(select(NewsSource.id).limit(1)).scalar_one_or_none()
    if has_sources is None:
        for channel in CHANNELS:
            for index in range(2):
                db.add(
                    NewsSource(
                        name=f"{channel.name} mock 源 {index + 1}",
                        channel=channel.key,
                        url=f"https://mock.example/{channel.key}/{index}",
                        kind="mock",
                    )
                )
        db.commit()

    today = shanghai_today()
    generated = 0
    for channel in CHANNELS:
        existing = db.execute(
            select(NewsProgram.id).where(
                NewsProgram.channel == channel.key, NewsProgram.program_date == today
            )
        ).scalar_one_or_none()
        if existing is None:
            await generate_news_for_channel(db, channel.key)
            generated += 1
    return generated
