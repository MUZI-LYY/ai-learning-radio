"""每日新闻节目生成：抓取、去重、选择、脚本生成、合成与落库。

复用 LLM/TTS provider、预算熔断、用量账本与本地存储；新闻固定使用品牌音色，
同频道所有用户共享同一份音频（不按用户重复合成）。
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode
from app.core.security import sha256_hex
from app.db.base import utcnow
from app.models.enums import ProgramStatus
from app.models.news_article import NewsArticle
from app.models.news_program import NewsProgram
from app.models.news_source import NewsSource
from app.schemas.news import NewsScript
from app.services.agent import AgentArticle, LearningRadioAgent
from app.services.generation.quota import shanghai_today
from app.services.news.channels import CHANNELS, get_channel
from app.services.news.sources import fetch_source_articles
from app.services.providers.budget import check_budget, estimate_tts_cost, record_usage
from app.services.providers.tts import get_tts_provider
from app.services.storage.local import get_storage

NEWS_VOICE_KEY = "elegant_youth"  # 新闻固定品牌音色
MAX_PROMPT_ARTICLE_CHARS = 3_000


def _llm_is_real() -> bool:
    return get_settings().llm_provider != "mock"


def _tts_is_real() -> bool:
    return get_settings().tts_provider != "mock"


async def generate_news_for_channel(
    db: Session, channel_key: str, program_date: str | None = None
) -> NewsProgram:
    """运行每日资讯管线；任何失败都回滚本次数据库变更。"""
    try:
        return await _generate_news_for_channel(db, channel_key, program_date)
    except Exception:
        db.rollback()
        raise


async def _generate_news_for_channel(
    db: Session, channel_key: str, program_date: str | None = None
) -> NewsProgram:
    """为一个频道生成指定日期的新闻节目；已完成的节目幂等返回。"""
    channel = get_channel(channel_key)
    program_date = program_date or shanghai_today()

    existing = db.execute(
        select(NewsProgram).where(
            NewsProgram.channel == channel_key, NewsProgram.program_date == program_date
        )
    ).scalar_one_or_none()
    if existing is not None and existing.status == ProgramStatus.COMPLETED.value:
        return existing

    # 1. 抓取 + 按 URL 去重
    sources = (
        db.execute(
            select(NewsSource).where(
                NewsSource.enabled.is_(True), NewsSource.channel == channel_key
            )
        )
        .scalars()
        .all()
    )
    # URL 在数据库中是全局唯一键，因此去重范围也必须保持全局一致。
    known_urls = set(db.execute(select(NewsArticle.url)).scalars().all())
    known_hashes = set(
        db.execute(select(NewsArticle.content_hash).where(NewsArticle.channel == channel_key))
        .scalars()
        .all()
    )
    articles: list[NewsArticle] = []
    for source in sources:
        for item in fetch_source_articles(source):
            if item["url"] in known_urls:
                continue
            content_hash = sha256_hex(item["content"])
            # 不同来源报道同一故事时按内容哈希去重
            if content_hash in known_hashes:
                continue
            article = NewsArticle(
                source_id=source.id,
                channel=channel_key,
                url=item["url"],
                title=item["title"],
                summary=item.get("summary"),
                content=item["content"],
                image_url=item.get("image_url"),
                content_is_complete=item.get("content_is_complete", False),
                content_hash=content_hash,
                published_at=item.get("published_at"),
                fetched_at=utcnow(),
            )
            db.add(article)
            db.flush()
            known_urls.add(item["url"])
            known_hashes.add(content_hash)
            articles.append(article)

    # 新文章不足 6 条时，用该频道最近抓取的文章补齐（保证节目长度稳定）
    if len(articles) < 6:
        recent = (
            db.execute(
                select(NewsArticle)
                .where(NewsArticle.channel == channel_key)
                .order_by(NewsArticle.fetched_at.desc())
                .limit(12)
            )
            .scalars()
            .all()
        )
        seen = {a.url for a in articles}
        for article in recent:
            if article.url in seen:
                continue
            articles.append(article)
            seen.add(article.url)
            if len(articles) >= 6:
                break
    if not articles:
        raise ApiError(ErrorCode.RESOURCE_NOT_FOUND, "该频道暂无可用新闻。")

    # 2. 最多 6 条，按发布时间倒序
    articles = sorted(articles, key=lambda a: a.published_at or a.fetched_at, reverse=True)[:6]

    # 3. 单 Agent 生成：模型只写观点与口播，来源绑定由代码负责。
    if _llm_is_real():
        check_budget(db)
    selected_source_ids = {article.source_id for article in articles}
    selected_sources = (
        db.execute(select(NewsSource).where(NewsSource.id.in_(selected_source_ids)))
        .scalars()
        .all()
    )
    source_names = {source.id: source.name for source in selected_sources}
    agent_run = await LearningRadioAgent().produce_daily_news(
        channel_name=channel.name,
        program_date=program_date,
        articles=[
            AgentArticle(
                title=article.title,
                source_name=source_names.get(article.source_id, "未知来源"),
                source_url=article.url,
                content=article.content[:MAX_PROMPT_ARTICLE_CHARS],
                published_at=article.published_at.isoformat() if article.published_at else None,
            )
            for article in articles
        ],
    )
    script = agent_run.script

    # 防御式二次校验：持久化结构仍由稳定的领域契约控制。
    script = NewsScript.model_validate(script.model_dump())

    # 4. TTS（固定品牌音色）
    if _tts_is_real():
        check_budget(db)
    tts_result = await get_tts_provider().synthesize(build_news_narration(script), NEWS_VOICE_KEY)

    # 5. 落库（共享节目）
    program = existing or NewsProgram(
        channel=channel_key, program_date=program_date, title=script.title, voice_key=NEWS_VOICE_KEY
    )
    program.title = script.title
    program.transcript_json = json.dumps(script.model_dump(), ensure_ascii=False)
    program.agent_version = agent_run.agent_version
    program.prompt_version = agent_run.prompt_version
    program.llm_model = agent_run.llm_result.model
    program.voice_key = NEWS_VOICE_KEY
    program.tts_model = tts_result.model
    program.provider_voice_id = tts_result.provider_voice_id
    ext = "wav" if tts_result.model.startswith("mock") else "mp3"
    audio_key = f"{channel_key}/{program_date}.{ext}"
    storage = get_storage()
    try:
        storage.save("news", audio_key, tts_result.audio_bytes)
        program.audio_key = audio_key
        program.audio_duration_seconds = tts_result.duration_seconds
        program.status = ProgramStatus.COMPLETED.value
        program.published_at = utcnow()
        db.add(program)

        if _llm_is_real():
            record_usage(
                db,
                provider="volcark",
                model=agent_run.llm_result.model,
                operation="news_script",
                input_units=agent_run.llm_result.input_tokens,
                output_units=agent_run.llm_result.output_tokens,
                estimated_cost_cny=agent_run.llm_result.estimated_cost_cny,
            )
        if _tts_is_real():
            record_usage(
                db,
                provider="volc",
                model=tts_result.model,
                operation="tts_synthesize",
                input_units=tts_result.input_chars,
                output_units=0,
                estimated_cost_cny=estimate_tts_cost(tts_result.input_chars),
            )

        db.commit()
    except Exception:
        storage.delete("news", audio_key)
        raise
    return program


async def generate_all_channels(db: Session) -> list[NewsProgram]:
    """为所有频道生成今日新闻节目。"""
    programs = []
    for channel in CHANNELS:
        programs.append(await generate_news_for_channel(db, channel.key))
    return programs


def build_news_narration(script: NewsScript) -> str:
    return "\n\n".join([script.summary, *(item.narration for item in script.items)])
