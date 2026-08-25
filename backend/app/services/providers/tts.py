"""TTS provider：mock 与豆包语音真实适配器。

统一入口 `get_tts_provider()`。真实实现只允许白名单音色，供应商 Voice ID 由服务端映射。
"""

from __future__ import annotations

import io
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import get_settings
from app.services.providers.voices import to_volc_voice_id


@dataclass
class TTSResult:
    audio_bytes: bytes
    duration_seconds: float
    model: str
    provider_voice_id: str
    input_chars: int


class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, voice_key: str) -> TTSResult:
        """合成音频并返回结果；voice_key 必须来自服务端白名单。"""


def _estimate_duration(text: str) -> float:
    # 中文口播约 4.5 字/秒，用于 mock 时长估算
    return round(len(text) / 4.5, 2)


def _silent_wav(duration_seconds: float) -> bytes:
    """生成可播放的静音 WAV（mock 音频）。"""
    sample_rate = 16_000
    num_samples = int(sample_rate * duration_seconds)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * num_samples)
    return buffer.getvalue()


class MockTTSProvider(TTSProvider):
    async def synthesize(self, text: str, voice_key: str) -> TTSResult:
        duration = _estimate_duration(text)
        return TTSResult(
            audio_bytes=_silent_wav(duration),
            duration_seconds=duration,
            model="mock-tts",
            provider_voice_id=to_volc_voice_id(voice_key),
            input_chars=len(text),
        )


class VolcTTSProvider(TTSProvider):
    """豆包语音（语音技术新版 API Key 接入，流式单向合成）。

    使用语音技术控制台创建的 API Key；响应为拼接的 JSON 对象流，
    每个对象的 data 为 base64 编码的 MP3 分片，最后以 code=20000000 结束。
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    async def synthesize(self, text: str, voice_key: str) -> TTSResult:

        import httpx

        provider_voice_id = to_volc_voice_id(voice_key)
        headers = {
            "x-api-key": self.settings.tts_api_key,
            "X-Api-Resource-Id": self.settings.tts_resource_id,
            "Content-Type": "application/json",
        }
        payload = {
            "req_params": {
                "text": text,
                "speaker": provider_voice_id,
                "audio_params": {"format": "mp3", "sample_rate": 24000},
            }
        }
        async with httpx.AsyncClient(timeout=self.settings.tts_timeout_seconds) as client:
            response = await client.post(
                self.settings.tts_base_url.rstrip("/"),
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            audio = self._parse_stream(response.text)

        return TTSResult(
            audio_bytes=audio,
            duration_seconds=_estimate_duration(text),
            model="seed-tts-2.0",
            provider_voice_id=provider_voice_id,
            input_chars=len(text),
        )

    @staticmethod
    def _parse_stream(body: str) -> bytes:
        import base64
        import json

        decoder = json.JSONDecoder()
        index = 0
        chunks: list[bytes] = []
        while index < len(body):
            while index < len(body) and body[index] in " \n\r":
                index += 1
            if index >= len(body):
                break
            obj, end = decoder.raw_decode(body, index)
            index = end
            if obj.get("data"):
                chunks.append(base64.b64decode(obj["data"]))
            if obj.get("code") == 20000000:
                break
        return b"".join(chunks)


def get_tts_provider() -> TTSProvider:
    provider = get_settings().tts_provider
    if provider == "volc":
        return VolcTTSProvider()
    return MockTTSProvider()
