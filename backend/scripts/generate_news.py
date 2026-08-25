"""手动生成今日新闻节目（所有频道）。

用法（在 backend/ 目录下）：
    uv run python -m scripts.generate_news
"""

from __future__ import annotations

import asyncio

from app.db.session import get_session_factory
from app.services.news.generation import generate_all_channels


def main() -> None:
    factory = get_session_factory()
    with factory() as db:
        programs = asyncio.run(generate_all_channels(db))
        for program in programs:
            print(
                f"[{program.channel}] {program.title} -> {program.status} "
                f"({program.audio_duration_seconds}s)"
            )


if __name__ == "__main__":
    main()
