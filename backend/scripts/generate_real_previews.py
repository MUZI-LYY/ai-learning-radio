"""用真实 TTS 生成 3 个音色的试听 MP3。

试听使用预生成固定音频，不发起实时 TTS。配置好 TTS_API_KEY 并切到 volc 后运行：

    uv run python -m scripts.generate_real_previews

输出到 data/previews/{voice_key}.mp3。
"""

from __future__ import annotations

import asyncio

from app.core.config import PROJECT_ROOT, get_settings
from app.services.providers.tts import get_tts_provider
from app.services.providers.voices import VOICES

_PREVIEW_TEXT = "你好，这里是 AI 学习电台，用几分钟时间，把知识讲给你听。"


async def main() -> None:
    settings = get_settings()
    preview_dir = PROJECT_ROOT / "data" / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    provider = get_tts_provider()
    for voice in VOICES:
        result = await provider.synthesize(_PREVIEW_TEXT, voice.key)
        path = preview_dir / f"{voice.key}.mp3"
        path.write_bytes(result.audio_bytes)
        print(f"已生成 {voice.key}.mp3（{voice.display_name}，{len(result.audio_bytes)} 字节）")
    print("provider:", settings.tts_provider)


if __name__ == "__main__":
    asyncio.run(main())
