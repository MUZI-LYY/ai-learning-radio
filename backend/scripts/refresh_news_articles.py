"""补齐现有新闻文章的主图与可阅读正文。

默认只刷新数据库中已有节目的来源文章，避免无边界抓取历史数据。
"""

from __future__ import annotations

import json

from sqlalchemy import select

from app.core.security import sha256_hex
from app.db.session import get_session_factory
from app.models.news_article import NewsArticle
from app.models.news_program import NewsProgram
from app.schemas.news import NewsScript
from app.services.news.sources import extract_article_page

_MAX_CONTENT_CHARS = 30_000


def main() -> None:
    factory = get_session_factory()
    with factory() as db:
        programs = db.execute(
            select(NewsProgram).where(NewsProgram.transcript_json.is_not(None))
        ).scalars()
        urls: set[str] = set()
        for program in programs:
            script = NewsScript.model_validate(json.loads(program.transcript_json or "{}"))
            urls.update(item.source_url for item in script.items)

        articles = db.execute(select(NewsArticle).where(NewsArticle.url.in_(urls))).scalars()
        updated = 0
        for article in articles:
            content, image_url = extract_article_page(article.url)
            if not content and not image_url:
                continue
            article.summary = article.summary or article.content
            if content:
                stored_content = content[:_MAX_CONTENT_CHARS]
                article.content = stored_content
                article.content_hash = sha256_hex(stored_content)
                article.content_is_complete = len(content) <= _MAX_CONTENT_CHARS
            if image_url:
                article.image_url = image_url
            updated += 1
            print(f"[{updated}] {article.title}")

        db.commit()
        print(f"已刷新 {updated} 篇节目来源文章。")


if __name__ == "__main__":
    main()
