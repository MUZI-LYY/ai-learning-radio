from __future__ import annotations

from pydantic import BaseModel


class UserSummary(BaseModel):
    id: str
    display_name: str
    role: str


class QuotaInfo(BaseModel):
    used: int
    limit: int
    remaining: int


class MeResponse(BaseModel):
    user: UserSummary
    quota: QuotaInfo
    # 第一阶段没有新闻频道，占位为空列表
    channels: list[str] = []
