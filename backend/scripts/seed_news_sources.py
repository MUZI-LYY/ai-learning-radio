"""初始化 mock 新闻源（每个频道 2 个 mock 源）。

用法（在 backend/ 目录下）：
    uv run python -m scripts.seed_news_sources
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.news_source import NewsSource
from app.services.news.channels import CHANNELS


def main() -> None:
    factory = get_session_factory()
    created = 0
    with factory() as db:
        for channel in CHANNELS:
            for index in range(2):
                url = f"https://mock.example/{channel.key}/{index}"
                exists = db.execute(
                    select(NewsSource).where(
                        NewsSource.channel == channel.key, NewsSource.url == url
                    )
                ).scalar_one_or_none()
                if exists is not None:
                    continue
                db.add(
                    NewsSource(
                        name=f"{channel.name} mock 源 {index + 1}",
                        channel=channel.key,
                        url=url,
                        kind="mock",
                    )
                )
                created += 1
        db.commit()
    print(f"已创建 {created} 个 mock 新闻源")


if __name__ == "__main__":
    main()
