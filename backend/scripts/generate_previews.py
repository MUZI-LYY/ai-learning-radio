"""生成 3 个音色的试听占位音频（静音 WAV）。

试听使用预生成固定音频，不发起实时 TTS。真实试听音频应在真实验收前
用豆包语音各合成一次并替换 data/previews/ 下的占位文件。

用法（在 backend/ 目录下）：
    uv run python -m scripts.generate_previews
"""

from __future__ import annotations

import io
import wave

from app.core.config import PROJECT_ROOT
from app.services.providers.voices import VOICES


def _silent_wav(seconds: float) -> bytes:
    sample_rate = 16_000
    num_samples = int(sample_rate * seconds)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * num_samples)
    return buffer.getvalue()


def main() -> None:
    preview_dir = PROJECT_ROOT / "data" / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    for voice in VOICES:
        (preview_dir / f"{voice.key}.wav").write_bytes(_silent_wav(2.0))
        print(f"已生成占位试听: {voice.key}.wav（{voice.display_name}）")


if __name__ == "__main__":
    main()
