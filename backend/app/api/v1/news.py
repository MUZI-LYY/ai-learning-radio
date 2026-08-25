"""每日新闻：频道、今日节目与鉴权音频。"""

from __future__ import annotations

import re

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import ApiError, ErrorCode
from app.models.news_article import NewsArticle
from app.models.news_favorite import NewsFavorite
from app.models.news_program import NewsProgram
from app.models.news_source import NewsSource
from app.schemas.news import (
    ChannelOut,
    NewsArticleDetailOut,
    NewsFavoriteState,
    NewsFavoriteSummary,
    NewsItemOut,
    NewsProgramDetail,
    NewsProgramSummary,
    NewsScript,
)
from app.services.generation.quota import shanghai_today
from app.services.news.channels import CHANNELS, get_channel
from app.services.providers.voices import get_voice
from app.services.storage.local import get_storage

router = APIRouter(prefix="/news", tags=["news"])


def _playable_programs_query():
    return select(NewsProgram).where(
        NewsProgram.status == "completed",
        NewsProgram.transcript_json.is_not(None),
        NewsProgram.audio_key.is_not(None),
    )


@router.get("/channels", response_model=list[ChannelOut])
def list_channels(user: CurrentUser, db: DbSession) -> list[ChannelOut]:
    today = shanghai_today()
    latest_by_channel: dict[str, NewsProgram] = {}
    for channel in CHANNELS:
        latest = db.execute(
            _playable_programs_query()
            .where(NewsProgram.channel == channel.key)
            .order_by(NewsProgram.program_date.desc(), NewsProgram.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if latest is not None:
            latest_by_channel[channel.key] = latest

    return [
        ChannelOut(
            key=channel.key,
            name=channel.name,
            has_program=(latest := latest_by_channel.get(channel.key)) is not None
            and latest.program_date == today,
            program_id=latest.id if latest else None,
        )
        for channel in CHANNELS
    ]


@router.get("/programs", response_model=list[NewsProgramSummary])
def list_today_programs(
    user: CurrentUser, db: DbSession, channel: str | None = Query(default=None)
) -> list[NewsProgramSummary]:
    query = _playable_programs_query().where(NewsProgram.program_date == shanghai_today())
    if channel is not None:
        get_channel(channel)
        query = query.where(NewsProgram.channel == channel)
    programs = db.execute(query.order_by(NewsProgram.channel)).scalars().all()

    # 每日节目在 7:30 发布；午夜到新节目完成前继续展示该频道最近一期。
    if channel is not None and not programs:
        latest = db.execute(
            _playable_programs_query()
            .where(NewsProgram.channel == channel)
            .order_by(NewsProgram.program_date.desc(), NewsProgram.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if latest is not None:
            programs = [latest]

    return [_summary(program) for program in programs]


@router.get("/programs/{program_id}", response_model=NewsProgramDetail)
def get_program(program_id: str, user: CurrentUser, db: DbSession) -> NewsProgramDetail:
    program = db.get(NewsProgram, program_id)
    if program is None:
        raise ApiError(ErrorCode.RESOURCE_NOT_FOUND)
    if program.transcript_json is None:
        raise ApiError(ErrorCode.RESOURCE_NOT_FOUND, "节目脚本尚未生成。")
    script = NewsScript.model_validate_json(program.transcript_json)
    channel = get_channel(program.channel)
    voice = get_voice(program.voice_key)
    urls = [item.source_url for item in script.items]
    articles = db.execute(select(NewsArticle).where(NewsArticle.url.in_(urls))).scalars().all()
    by_url = {article.url: article for article in articles}
    return NewsProgramDetail(
        id=program.id,
        channel=program.channel,
        channel_name=channel.name,
        program_date=program.program_date,
        title=_display_title(program.title, script.summary),
        summary=script.summary,
        items=[_item_out(i, by_url.get(i.source_url)) for i in script.items],
        audio_ready=program.audio_key is not None,
        audio_duration_seconds=program.audio_duration_seconds,
        status=program.status,
        voice_key=program.voice_key,
        voice_name=voice.display_name if voice else "默认音色",
        is_favorited=_is_favorited(db, user.id, program.id),
    )


@router.get("/favorites", response_model=list[NewsFavoriteSummary])
def list_favorites(user: CurrentUser, db: DbSession) -> list[NewsFavoriteSummary]:
    favorites = db.execute(
        select(NewsFavorite)
        .where(NewsFavorite.user_id == user.id)
        .order_by(NewsFavorite.created_at.desc())
    ).scalars().all()
    result: list[NewsFavoriteSummary] = []
    for favorite in favorites:
        program = db.get(NewsProgram, favorite.program_id)
        if program is None or program.transcript_json is None:
            continue
        script = NewsScript.model_validate_json(program.transcript_json)
        urls = [item.source_url for item in script.items]
        articles = db.execute(
            select(NewsArticle).where(NewsArticle.url.in_(urls))
        ).scalars().all()
        by_url = {article.url: article for article in articles}
        image_url = next(
            (by_url[url].image_url for url in urls if url in by_url and by_url[url].image_url),
            None,
        )
        result.append(
            NewsFavoriteSummary(
                program_id=program.id,
                channel=program.channel,
                channel_name=get_channel(program.channel).name,
                program_date=program.program_date,
                title=_display_title(program.title, script.summary),
                summary=script.summary,
                image_url=image_url,
                audio_duration_seconds=program.audio_duration_seconds,
                favorited_at=favorite.created_at,
            )
        )
    return result


@router.put("/programs/{program_id}/favorite", response_model=NewsFavoriteState)
def favorite_program(
    program_id: str, user: CurrentUser, db: DbSession
) -> NewsFavoriteState:
    if db.get(NewsProgram, program_id) is None:
        raise ApiError(ErrorCode.RESOURCE_NOT_FOUND)
    existing = db.execute(
        select(NewsFavorite).where(
            NewsFavorite.user_id == user.id, NewsFavorite.program_id == program_id
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(NewsFavorite(user_id=user.id, program_id=program_id))
        db.commit()
    return NewsFavoriteState(is_favorited=True)


@router.delete("/programs/{program_id}/favorite", response_model=NewsFavoriteState)
def unfavorite_program(
    program_id: str, user: CurrentUser, db: DbSession
) -> NewsFavoriteState:
    favorite = db.execute(
        select(NewsFavorite).where(
            NewsFavorite.user_id == user.id, NewsFavorite.program_id == program_id
        )
    ).scalar_one_or_none()
    if favorite is not None:
        db.delete(favorite)
        db.commit()
    return NewsFavoriteState(is_favorited=False)


@router.get("/articles/{article_id}", response_model=NewsArticleDetailOut)
def get_article(article_id: str, user: CurrentUser, db: DbSession) -> NewsArticleDetailOut:
    article = db.get(NewsArticle, article_id)
    if article is None:
        raise ApiError(ErrorCode.RESOURCE_NOT_FOUND)
    source = db.get(NewsSource, article.source_id)
    return NewsArticleDetailOut(
        id=article.id,
        channel=article.channel,
        title=article.title,
        source_name=source.name if source else "未知来源",
        source_url=article.url,
        summary=article.summary or _excerpt(article.content),
        content=article.content,
        image_url=article.image_url,
        content_is_complete=article.content_is_complete,
        published_at=article.published_at,
    )


def _item_out(item, article: NewsArticle | None) -> NewsItemOut:
    return NewsItemOut(
        article_id=article.id if article else None,
        title=item.title,
        source_name=item.source_name,
        source_url=item.source_url,
        narration=item.narration,
        excerpt=(article.summary if article else None)
        or _excerpt(article.content if article else item.narration),
        image_url=article.image_url if article else None,
        content_is_complete=article.content_is_complete if article else False,
    )


def _excerpt(text: str, limit: int = 180) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else f"{clean[:limit].rstrip()}…"


@router.get("/programs/{program_id}/audio")
def get_audio(program_id: str, user: CurrentUser, db: DbSession) -> FileResponse:
    program = db.get(NewsProgram, program_id)
    if program is None or program.audio_key is None:
        raise ApiError(ErrorCode.AUDIO_NOT_READY)
    path = get_storage().path("news", program.audio_key)
    if not path.exists():
        raise ApiError(ErrorCode.AUDIO_NOT_READY)
    media_type = "audio/mpeg" if program.audio_key.endswith(".mp3") else "audio/wav"
    return FileResponse(
        path,
        media_type=media_type,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


def _summary(program: NewsProgram) -> NewsProgramSummary:
    channel = get_channel(program.channel)
    script = (
        NewsScript.model_validate_json(program.transcript_json)
        if program.transcript_json
        else None
    )
    return NewsProgramSummary(
        id=program.id,
        channel=program.channel,
        channel_name=channel.name,
        program_date=program.program_date,
        title=_display_title(program.title, script.summary) if script else program.title,
        status=program.status,
        audio_duration_seconds=program.audio_duration_seconds,
        published_at=program.published_at,
    )


def _is_favorited(db: DbSession, user_id: str, program_id: str) -> bool:
    return (
        db.execute(
            select(NewsFavorite.id).where(
                NewsFavorite.user_id == user_id, NewsFavorite.program_id == program_id
            )
        ).scalar_one_or_none()
        is not None
    )


def _display_title(generated_title: str, summary: str) -> str:
    """优先使用 Agent 标题；仅为历史通用栏目标题提供兼容降级。"""
    title = " ".join(generated_title.split()).strip()
    generic_titles = {"今日资讯", "今日资讯速递", "新闻速递", "每日资讯"}
    if title and title not in generic_titles:
        return title
    return _core_title(summary, title or "今日资讯")


def _core_title(summary: str, fallback: str) -> str:
    """从历史节目的核心观点中收敛出一句兼容标题。"""
    clean = " ".join(summary.split()).strip()
    if not clean:
        return fallback
    first_sentence = re.split(r"(?<=[。！？!?])", clean, maxsplit=1)[0].strip()
    if len(first_sentence) <= 42:
        return first_sentence
    cut = max(first_sentence.rfind(mark, 0, 39) for mark in "，、；：")
    if cut < 18:
        cut = 39
    return f"{first_sentence[:cut].rstrip('，、；：')}…"
