"""新闻频道目录（版本控制下的静态配置）。"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import ApiError, ErrorCode


@dataclass(frozen=True)
class Channel:
    key: str
    name: str


CHANNELS: tuple[Channel, ...] = (
    Channel("ai_frontier", "AI 前沿"),
    Channel("tech_product", "科技产品"),
    Channel("startup_business", "创业商业"),
)

CHANNEL_BY_KEY: dict[str, Channel] = {c.key: c for c in CHANNELS}


def get_channel(key: str) -> Channel:
    channel = CHANNEL_BY_KEY.get(key)
    if channel is None:
        raise ApiError(ErrorCode.RESOURCE_NOT_FOUND, "不存在的频道。")
    return channel
