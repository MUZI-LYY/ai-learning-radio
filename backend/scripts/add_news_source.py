"""添加新闻源（RSS 或 mock）。

用法（在 backend/ 目录下）：
    uv run python -m scripts.add_news_source --channel ai_frontier \\
        --name "机器之心" --url "https://rss.example.com" --kind rss
"""

from __future__ import annotations

import argparse

from app.db.session import get_session_factory
from app.models.news_source import NewsSource
from app.services.news.channels import CHANNELS


def main() -> None:
    parser = argparse.ArgumentParser(description="添加新闻源")
    parser.add_argument("--channel", required=True, choices=[c.key for c in CHANNELS])
    parser.add_argument("--name", required=True, help="来源显示名")
    parser.add_argument("--url", required=True, help="RSS/Atom 地址")
    parser.add_argument("--kind", default="rss", choices=["rss", "mock"])
    args = parser.parse_args()

    factory = get_session_factory()
    with factory() as db:
        db.add(
            NewsSource(
                name=args.name,
                channel=args.channel,
                url=args.url,
                kind=args.kind,
            )
        )
        db.commit()
    print(f"已添加新闻源: [{args.channel}] {args.name} ({args.kind}) {args.url}")


if __name__ == "__main__":
    main()
