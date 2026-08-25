"""新闻节目结构化输出契约。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

MAX_NEWS_ITEMS = 6


class NewsItem(BaseModel):
    title: str = Field(min_length=1)
    source_name: str
    source_url: str
    narration: str = Field(min_length=1)


class NewsScript(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    items: list[NewsItem] = Field(min_length=1)

    @field_validator("items")
    @classmethod
    def _at_most_six(cls, v: list[NewsItem]) -> list[NewsItem]:
        if len(v) > MAX_NEWS_ITEMS:
            raise ValueError(f"新闻条目最多 {MAX_NEWS_ITEMS} 条，当前 {len(v)} 条")
        return v


# ---- API 输出 ----


class ChannelOut(BaseModel):
    key: str
    name: str
    has_program: bool
    program_id: str | None = None


class NewsItemOut(BaseModel):
    article_id: str | None
    title: str
    source_name: str
    source_url: str
    narration: str
    excerpt: str
    image_url: str | None
    content_is_complete: bool


class NewsProgramSummary(BaseModel):
    id: str
    channel: str
    channel_name: str
    program_date: str
    title: str
    status: str
    audio_duration_seconds: float | None
    published_at: datetime | None


class NewsProgramDetail(BaseModel):
    id: str
    channel: str
    channel_name: str
    program_date: str
    title: str
    summary: str
    items: list[NewsItemOut]
    audio_ready: bool
    audio_duration_seconds: float | None
    status: str
    voice_key: str
    voice_name: str
    is_favorited: bool


class NewsFavoriteState(BaseModel):
    is_favorited: bool


class NewsFavoriteSummary(BaseModel):
    program_id: str
    channel: str
    channel_name: str
    program_date: str
    title: str
    summary: str
    image_url: str | None
    audio_duration_seconds: float | None
    favorited_at: datetime


class NewsArticleDetailOut(BaseModel):
    id: str
    channel: str
    title: str
    source_name: str
    source_url: str
    summary: str
    content: str
    image_url: str | None
    content_is_complete: bool
    published_at: datetime | None
