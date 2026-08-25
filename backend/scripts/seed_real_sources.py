"""配置真实新闻源（幂等）。

用法（在 backend/ 目录下）：
    uv run python -m scripts.seed_real_sources
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.news_source import NewsSource

# 各频道的可信新闻源（RSS/Atom）
REAL_SOURCES: dict[str, list[tuple[str, str]]] = {
    "ai_frontier": [
        ("量子位", "https://www.qbitai.com/feed"),
        ("AIHot", "https://aihot.virxact.com/rss"),
        ("HuggingFace", "https://huggingface.co/blog/feed.xml"),
    ],
    "tech_product": [
        ("少数派", "https://sspai.com/feed"),
        ("爱范儿", "https://www.ifanr.com/feed"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ],
    "startup_business": [
        ("TechCrunch", "https://techcrunch.com/feed/"),
    ],
}


def main() -> None:
    factory = get_session_factory()
    added = 0
    with factory() as db:
        for channel, sources in REAL_SOURCES.items():
            for name, url in sources:
                exists = db.execute(
                    select(NewsSource).where(
                        NewsSource.channel == channel, NewsSource.url == url
                    )
                ).scalar_one_or_none()
                if exists is not None:
                    continue
                db.add(NewsSource(name=name, channel=channel, url=url, kind="rss"))
                added += 1
        db.commit()
    print(f"已添加 {added} 个真实新闻源")


if __name__ == "__main__":
    main()
