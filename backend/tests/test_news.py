"""每日新闻管线（mock provider）测试。"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from app.db.session import get_session_factory
from app.models.news_article import NewsArticle
from app.models.news_program import NewsProgram
from app.models.news_source import NewsSource
from app.schemas.news import NewsScript
from app.services.agent import AgentArticle, LearningRadioAgent
from app.services.news.channels import CHANNELS
from app.services.news.generation import build_news_narration, generate_news_for_channel
from app.services.providers.llm import LLMResult


def _seed_sources(db) -> None:
    for channel in CHANNELS:
        for index in range(2):
            db.add(
                NewsSource(
                    name=f"{channel.name} 源 {index + 1}",
                    channel=channel.key,
                    url=f"https://mock.example/{channel.key}/{index}",
                    kind="mock",
                )
            )
    db.commit()


def test_generate_news_program(client, login):
    login()
    factory = get_session_factory()
    with factory() as db:
        _seed_sources(db)
        program = asyncio.run(generate_news_for_channel(db, "ai_frontier"))

        assert program.status == "completed"
        assert program.audio_key is not None
        assert program.audio_duration_seconds is not None
        assert program.agent_version == "learning_radio_agent_v1"
        assert program.prompt_version == "news_script_v2"
        assert program.llm_model == "mock"

        script = NewsScript.model_validate_json(program.transcript_json)
        assert 1 <= len(script.items) <= 6
        # 来源链接来自真实抓取数据，不是 mock LLM 占位
        assert all("mock.example" in item.source_url for item in script.items)
        assert all(item.title for item in script.items)
        # 不同源报道同一故事按内容去重，标题不重复
        titles = [item.title for item in script.items]
        assert len(titles) == len(set(titles))

    # 新闻节目对所有登录用户共享
    response = client.get("/api/v1/news/programs")
    assert response.status_code == 200
    channels = {p["channel"] for p in response.json()}
    assert "ai_frontier" in channels


def test_news_narration_matches_visible_transcript_in_order():
    script = NewsScript.model_validate(
        {
            "title": "不应朗读的节目标题",
            "summary": "页面展示的核心观点。",
            "items": [
                {
                    "title": "不应朗读的第一条标题",
                    "source_name": "测试来源",
                    "source_url": "https://example.com/1",
                    "narration": "页面展示的第一条口播。",
                },
                {
                    "title": "不应朗读的第二条标题",
                    "source_name": "测试来源",
                    "source_url": "https://example.com/2",
                    "narration": "页面展示的第二条口播！",
                },
            ],
        }
    )

    assert build_news_narration(script) == (
        "页面展示的核心观点。\n\n"
        "页面展示的第一条口播。\n\n"
        "页面展示的第二条口播！"
    )


def test_channels_listing(client, login):
    login()
    response = client.get("/api/v1/news/channels")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert {c["key"] for c in body} == {"ai_frontier", "tech_product", "startup_business"}
    assert all(c["has_program"] is False for c in body)


def test_channel_falls_back_to_latest_program_before_daily_update(client, login):
    login()
    factory = get_session_factory()
    with factory() as db:
        _seed_sources(db)
        program = asyncio.run(generate_news_for_channel(db, "ai_frontier"))
        program.program_date = (datetime.now(UTC) - timedelta(days=2)).strftime("%Y-%m-%d")
        db.commit()
        program_id = program.id

    channels = client.get("/api/v1/news/channels").json()
    ai_channel = next(item for item in channels if item["key"] == "ai_frontier")
    assert ai_channel["has_program"] is False
    assert ai_channel["program_id"] == program_id

    programs = client.get("/api/v1/news/programs?channel=ai_frontier").json()
    assert [item["id"] for item in programs] == [program_id]


def test_dedup_and_idempotency(client, login):
    login()
    factory = get_session_factory()
    with factory() as db:
        _seed_sources(db)
        asyncio.run(generate_news_for_channel(db, "ai_frontier"))
        count_articles = db.query(NewsArticle).filter_by(channel="ai_frontier").count()

        # 再次生成：文章不重复入库，节目不重复创建
        asyncio.run(generate_news_for_channel(db, "ai_frontier"))
        assert db.query(NewsArticle).filter_by(channel="ai_frontier").count() == count_articles
        assert db.query(NewsProgram).filter_by(channel="ai_frontier").count() == 1


def test_news_detail_and_audio(client, login):
    login()
    factory = get_session_factory()
    with factory() as db:
        _seed_sources(db)
        program = asyncio.run(generate_news_for_channel(db, "tech_product"))

    detail = client.get(f"/api/v1/news/programs/{program.id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["channel"] == "tech_product"
    assert len(body["items"]) >= 1
    assert body["audio_ready"] is True
    assert body["items"][0]["article_id"]
    assert body["items"][0]["excerpt"]
    assert body["title"] == "推理效率与工作流设计正在决定 AI 产品落地速度"
    assert body["title"] != body["summary"]
    assert body["voice_name"] == "儒雅青年 2.0"
    assert body["is_favorited"] is False

    article = client.get(f"/api/v1/news/articles/{body['items'][0]['article_id']}")
    assert article.status_code == 200
    article_body = article.json()
    assert article_body["title"] == body["items"][0]["title"]
    assert article_body["source_url"].startswith("https://mock.example/")
    assert article_body["content"]

    audio = client.get(f"/api/v1/news/programs/{program.id}/audio")
    assert audio.status_code == 200
    assert audio.headers["cache-control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert audio.headers["pragma"] == "no-cache"
    assert audio.headers["expires"] == "0"


def test_news_favorite_is_persistent_idempotent_and_user_scoped(client, login):
    code, _ = login()
    factory = get_session_factory()
    with factory() as db:
        _seed_sources(db)
        program = asyncio.run(generate_news_for_channel(db, "ai_frontier"))
        program_id = program.id

    favorite_url = f"/api/v1/news/programs/{program_id}/favorite"
    assert client.put(favorite_url).json() == {"is_favorited": True}
    assert client.put(favorite_url).json() == {"is_favorited": True}
    assert client.get(f"/api/v1/news/programs/{program_id}").json()["is_favorited"] is True

    favorites = client.get("/api/v1/news/favorites").json()
    assert len(favorites) == 1
    assert favorites[0]["program_id"] == program_id
    assert favorites[0]["title"] == "推理效率与工作流设计正在决定 AI 产品落地速度"

    login()
    assert client.get("/api/v1/news/favorites").json() == []
    assert client.delete(favorite_url).json() == {"is_favorited": False}

    client.post("/api/v1/auth/invite", json={"invite_code": code})
    assert len(client.get("/api/v1/news/favorites").json()) == 1
    assert client.delete(favorite_url).json() == {"is_favorited": False}
    assert client.get("/api/v1/news/favorites").json() == []


def test_news_requires_auth(client):
    assert client.get("/api/v1/news/channels").status_code == 401


def test_invalid_channel_is_rejected(client, login):
    login()
    response = client.get("/api/v1/news/programs?channel=not-a-channel")
    assert response.status_code == 404


def test_news_agent_rejects_reordered_or_missing_article_refs():
    class InvalidProvider:
        async def complete_json(self, *, system, user, json_schema):
            return LLMResult(
                data={
                    "title": "这是一条有效长度的观点标题",
                    "summary": "这是一段不会与标题重复的核心观点摘要。",
                    "items": [
                        {"article_ref": "A02", "narration": "第二篇口播。"},
                        {"article_ref": "A01", "narration": "第一篇口播。"},
                    ],
                },
                model="invalid-test",
            )

    articles = [
        AgentArticle(
            title=f"文章 {index}",
            source_name="测试来源",
            source_url=f"https://example.com/{index}",
            content="可信正文",
            published_at=None,
        )
        for index in range(2)
    ]
    with pytest.raises(ValueError, match="article_ref"):
        asyncio.run(
            LearningRadioAgent(provider=InvalidProvider()).produce_daily_news(
                channel_name="AI 前沿",
                program_date="2026-08-23",
                articles=articles,
            )
        )


def test_news_agent_rejects_duplicate_title_and_summary():
    duplicate = "AI 产品开始把稳定工作流放在能力展示之前"

    class DuplicateProvider:
        async def complete_json(self, *, system, user, json_schema):
            return LLMResult(
                data={
                    "title": duplicate,
                    "summary": duplicate,
                    "items": [{"article_ref": "A01", "narration": "一条可信口播。"}],
                },
                model="invalid-test",
            )

    article = AgentArticle(
        title="文章",
        source_name="测试来源",
        source_url="https://example.com/1",
        content="可信正文",
        published_at=None,
    )
    with pytest.raises(ValueError, match="title 与 summary"):
        asyncio.run(
            LearningRadioAgent(provider=DuplicateProvider()).produce_daily_news(
                channel_name="AI 前沿",
                program_date="2026-08-23",
                articles=[article],
            )
        )


def test_generation_rolls_back_articles_when_agent_fails(client, login, monkeypatch):
    login()
    from app.services.news import generation as gen

    async def fail_agent(*args, **kwargs):
        raise ValueError("agent output invalid")

    monkeypatch.setattr(gen.LearningRadioAgent, "produce_daily_news", fail_agent)
    factory = get_session_factory()
    with factory() as db:
        _seed_sources(db)
        with pytest.raises(ValueError, match="agent output invalid"):
            asyncio.run(gen.generate_news_for_channel(db, "ai_frontier"))
        assert db.query(NewsArticle).filter_by(channel="ai_frontier").count() == 0
        assert db.query(NewsProgram).filter_by(channel="ai_frontier").count() == 0


def test_news_tops_up_when_few_new_articles(client, login, monkeypatch):
    """新文章不足 6 条时，应复用最近文章补齐，避免节目只剩 1 条。"""
    login()
    from app.services.news import generation as gen

    factory = get_session_factory()
    with factory() as db:
        _seed_sources(db)
        # 第一次生成：mock 源各返回相同 5 篇，按内容去重后入库 5 篇
        asyncio.run(gen.generate_news_for_channel(db, "ai_frontier"))

        # 第二次生成：只返回 1 篇新文章
        def one_new_article(source):
            now = datetime.now(UTC)
            return [
                {
                    "title": "唯一新文章",
                    "url": f"https://mock.example/new/{source.id[:8]}",
                    "content": "新内容",
                    "published_at": now,
                }
            ]

        monkeypatch.setattr(gen, "fetch_source_articles", one_new_article)
        db.execute(delete(NewsProgram).where(NewsProgram.channel == "ai_frontier"))
        db.commit()

        program = asyncio.run(gen.generate_news_for_channel(db, "ai_frontier"))
        script = NewsScript.model_validate_json(program.transcript_json)
        # 1 新 + 5 已有 = 6 条
        assert len(script.items) == 6


def test_rss_fetcher_parses_entries(monkeypatch):
    from datetime import UTC, datetime

    from app.models.news_source import NewsSource
    from app.services.news import sources as news_sources

    class FakeEntry:
        def __init__(self, title, link, summary, published_parsed):
            self._d = {
                "title": title,
                "link": link,
                "summary": summary,
                "published_parsed": published_parsed,
            }

        def get(self, key, default=None):
            return self._d.get(key, default)

    class FakeFeed:
        entries = [
            FakeEntry(
                "标题一",
                "https://example.com/1",
                "<p>摘要<b>内容</b></p>",
                (2026, 8, 21, 0, 0, 0, 0, 0, 0),
            ),
            FakeEntry("标题二", "https://example.com/2", "普通摘要", None),
        ]

    monkeypatch.setattr(news_sources.feedparser, "parse", lambda url: FakeFeed())
    # 避免真实抓取原文，正文抽取返回空串（回退到摘要）
    monkeypatch.setattr(news_sources, "extract_article_page", lambda url: ("", None))
    source = NewsSource(
        name="测试", channel="ai_frontier", url="https://example.com/rss", kind="rss"
    )
    articles = news_sources._rss_articles(source)

    assert len(articles) == 2
    assert articles[0]["title"] == "标题一"
    assert articles[0]["content"] == "摘要 内容"  # HTML 标签已去除
    assert articles[0]["summary"] == "摘要 内容"
    assert articles[0]["image_url"] is None
    assert articles[0]["content_is_complete"] is False
    assert isinstance(articles[0]["published_at"], datetime)
    assert articles[0]["published_at"].tzinfo == UTC
    assert articles[1]["published_at"] is None


def test_article_page_extracts_og_image(monkeypatch):
    from app.services.news import sources as news_sources

    class Response:
        status_code = 200
        text = (
            '<html><head><meta content="https://cdn.example/cover.jpg" '
            'property="og:image"></head><body>正文</body></html>'
        )

    monkeypatch.setattr(news_sources.httpx, "get", lambda *args, **kwargs: Response())
    monkeypatch.setattr(news_sources.trafilatura, "extract", lambda *args, **kwargs: "完整正文")

    content, image_url = news_sources.extract_article_page("https://example.com/article")
    assert content == "完整正文"
    assert image_url == "https://cdn.example/cover.jpg"
