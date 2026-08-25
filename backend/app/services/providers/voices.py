"""私人节目音色目录（版本控制下的静态配置）。

客户端只提交稳定 voice_key；供应商 Voice ID 只能由服务端白名单映射，
绝不接受客户端传入的任意音色 ID。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import ApiError, ErrorCode


@dataclass(frozen=True)
class Voice:
    key: str
    display_name: str
    volc_voice_id: str
    description: str
    is_default: bool = False


VOICES: tuple[Voice, ...] = (
    Voice(
        key="elegant_youth",
        display_name="儒雅青年 2.0",
        volc_voice_id="zh_male_ruyaqingnian_mars_bigtts",
        description="自然克制的老师式讲解，新闻固定品牌音色",
        is_default=True,
    ),
    Voice(
        key="intellectual_cancan",
        display_name="知性灿灿 2.0",
        volc_voice_id="zh_female_cancan_mars_bigtts",
        description="明快女性声线",
    ),
    Voice(
        key="erudite_uncle",
        display_name="渊博小叔 2.0",
        volc_voice_id="zh_male_yuanboxiaoshu_moon_bigtts",
        description="更有知识播客和故事感",
    ),
)

VOICE_BY_KEY: dict[str, Voice] = {v.key: v for v in VOICES}


def default_voice_key() -> str:
    for voice in VOICES:
        if voice.is_default:
            return voice.key
    return VOICES[0].key


def get_voice(key: str) -> Voice | None:
    return VOICE_BY_KEY.get(key)


def to_volc_voice_id(key: str) -> str:
    """把稳定 voice_key 映射为供应商 Voice ID；未知 key 直接抛错，不回退到客户端值。"""
    voice = get_voice(key)
    if voice is None:
        raise ApiError(ErrorCode.INVALID_VOICE)
    return voice.volc_voice_id
