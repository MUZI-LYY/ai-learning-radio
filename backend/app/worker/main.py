"""Worker 主循环：轮询领取任务并执行，进程重启后从最后成功步骤继续。

mock 模式下同时补齐今日缺失的新闻节目（真实模式由显式定时任务触发）。
"""

from __future__ import annotations

import asyncio
import logging
import time

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_session_factory
from app.services.generation.workflow import claim_next_task, run_task
from app.services.news.scheduler import ensure_daily_news

logger = logging.getLogger("app.worker")

_NEWS_CHECK_INTERVAL_SECONDS = 60


def _run_news_scheduler(factory) -> None:
    db = factory()
    try:
        asyncio.run(ensure_daily_news(db))
    except Exception:  # noqa: BLE001
        logger.exception("news scheduler failed")
    finally:
        db.close()


def main() -> None:
    configure_logging()
    settings = get_settings()
    factory = get_session_factory()
    logger.info("worker started, poll every %ss", settings.worker_poll_seconds)

    last_news_check = 0.0
    while True:
        db = factory()
        task_id = None
        try:
            task_id = claim_next_task(db)
        except Exception:  # noqa: BLE001
            logger.exception("claim failed")
            db.rollback()
        finally:
            db.close()

        if task_id is not None:
            logger.info("processing task %s", task_id)
            try:
                asyncio.run(run_task(task_id))
            except Exception:  # noqa: BLE001
                logger.exception("task %s failed unexpectedly", task_id)
            continue

        now = time.monotonic()
        if now - last_news_check >= _NEWS_CHECK_INTERVAL_SECONDS:
            last_news_check = now
            _run_news_scheduler(factory)

        time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
