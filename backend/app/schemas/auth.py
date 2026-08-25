from __future__ import annotations

from pydantic import BaseModel, Field


class InviteRequest(BaseModel):
    invite_code: str = Field(min_length=1, max_length=256)


class UserSummary(BaseModel):
    id: str
    display_name: str
    role: str


class AuthResponse(BaseModel):
    user: UserSummary


class QuotaInfo(BaseModel):
    used: int
    limit: int
    remaining: int


class MeResponse(BaseModel):
    user: UserSummary
    quota: QuotaInfo
    # 第一阶段没有新闻频道，占位为空列表
    channels: list[str] = []
