"""音色目录与试听。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser
from app.core.config import PROJECT_ROOT
from app.core.errors import ApiError, ErrorCode
from app.schemas.program import VoiceOption
from app.services.providers.voices import VOICES, get_voice

router = APIRouter(prefix="/tts", tags=["tts"])

_PREVIEW_DIR = PROJECT_ROOT / "data" / "previews"


@router.get("/voices", response_model=list[VoiceOption])
def list_voices(_: CurrentUser) -> list[VoiceOption]:
    return [
        VoiceOption(
            voice_key=v.key,
            display_name=v.display_name,
            description=v.description,
            preview_url=f"/api/v1/tts/voices/{v.key}/preview",
            is_default=v.is_default,
        )
        for v in VOICES
    ]


@router.get("/voices/{voice_key}/preview")
def preview(voice_key: str, _: CurrentUser) -> FileResponse:
    voice = get_voice(voice_key)
    if voice is None:
        raise ApiError(ErrorCode.INVALID_VOICE)
    mp3_path = Path(_PREVIEW_DIR) / f"{voice_key}.mp3"
    if mp3_path.exists():
        return FileResponse(mp3_path, media_type="audio/mpeg")
    wav_path = Path(_PREVIEW_DIR) / f"{voice_key}.wav"
    if wav_path.exists():
        return FileResponse(wav_path, media_type="audio/wav")
    raise ApiError(ErrorCode.RESOURCE_NOT_FOUND, "试听音频尚未生成。")
