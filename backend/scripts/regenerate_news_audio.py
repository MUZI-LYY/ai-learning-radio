"""用现有节目脚本重新合成各频道最新音轨，不重新调用 LLM。

用法（在 backend/ 目录下）：
    uv run python -m scripts.regenerate_news_audio --apply

脚本为新音轨使用版本化文件名并保留旧文件，数据库提交失败时会删除新文件。
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import sha256_hex
from app.db.session import get_session_factory
from app.models.news_program import NewsProgram
from app.schemas.news import NewsScript
from app.services.news.channels import CHANNELS
from app.services.news.generation import NEWS_VOICE_KEY, build_news_narration
from app.services.providers.budget import check_budget, estimate_tts_cost, record_usage
from app.services.providers.tts import get_tts_provider
from app.services.storage.local import get_storage


async def regenerate_latest_audio() -> None:
    settings = get_settings()
    provider = get_tts_provider()
    storage = get_storage()
    factory = get_session_factory()

    with factory() as db:
        for channel in CHANNELS:
            program = db.execute(
                select(NewsProgram)
                .where(
                    NewsProgram.channel == channel.key,
                    NewsProgram.status == "completed",
                    NewsProgram.transcript_json.is_not(None),
                    NewsProgram.audio_key.is_not(None),
                )
                .order_by(NewsProgram.program_date.desc(), NewsProgram.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            if program is None:
                print(f"[{channel.key}] 没有可重新合成的节目，跳过。")
                continue

            script = NewsScript.model_validate_json(program.transcript_json or "{}")
            narration = build_news_narration(script)
            sync_version = sha256_hex(
                f"{settings.tts_provider}\0{NEWS_VOICE_KEY}\0{narration}"
            )[:16]
            extension = "wav" if settings.tts_provider == "mock" else "mp3"
            new_audio_key = (
                f"{channel.key}/{program.program_date}.sync-{sync_version}.{extension}"
            )
            if program.audio_key == new_audio_key and storage.exists("news", new_audio_key):
                print(f"[{channel.key}] 当前音轨已与文字稿同步，跳过。")
                continue

            if settings.tts_provider != "mock":
                check_budget(db)
            result = await provider.synthesize(narration, NEWS_VOICE_KEY)

            # Provider 调用已经产生费用，先独立记账；后续文件或节目更新失败也不能回滚费用。
            if settings.tts_provider != "mock":
                record_usage(
                    db,
                    provider="volc",
                    model=result.model,
                    operation="news_tts_resync",
                    input_units=result.input_chars,
                    estimated_cost_cny=estimate_tts_cost(result.input_chars),
                )
                db.commit()

            try:
                storage.save("news", new_audio_key, result.audio_bytes)
                program.audio_key = new_audio_key
                program.audio_duration_seconds = result.duration_seconds
                program.voice_key = NEWS_VOICE_KEY
                program.tts_model = result.model
                program.provider_voice_id = result.provider_voice_id
                db.commit()
            except Exception:
                db.rollback()
                storage.delete("news", new_audio_key)
                raise

            print(
                f"[{channel.key}] 已重新合成 {result.input_chars} 字，"
                f"时长约 {result.duration_seconds:.1f} 秒。"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="重新合成最新每日资讯音轨")
    parser.add_argument("--apply", action="store_true", help="确认写入新音轨并更新数据库")
    args = parser.parse_args()
    if not args.apply:
        parser.error("该操作会产生 TTS 调用；确认后请添加 --apply")
    asyncio.run(regenerate_latest_audio())


if __name__ == "__main__":
    main()
