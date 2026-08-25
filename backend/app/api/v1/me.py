"""当前用户、今日额度与删除全部个人数据。"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import delete, select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import ApiError, ErrorCode
from app.models.daily_quota_usage import DailyQuotaUsage
from app.models.generation_task import GenerationTask
from app.models.learning_source import LearningSource
from app.models.program import Program
from app.schemas.auth import MeResponse, QuotaInfo, UserSummary
from app.services.generation.quota import quota_limit, remaining_quota
from app.services.storage.local import get_storage

router = APIRouter(prefix="/me", tags=["me"])

CONFIRMATION_PHRASE = "删除全部数据"


class DeleteDataRequest(BaseModel):
    confirmation: str


@router.get("", response_model=MeResponse)
def get_me(user: CurrentUser, db: DbSession) -> MeResponse:
    limit = quota_limit()
    remaining = remaining_quota(db, user.id)
    used = max(0, limit - remaining)
    return MeResponse(
        user=UserSummary(id=user.id, display_name=user.display_name, role=user.role),
        quota=QuotaInfo(used=used, limit=limit, remaining=remaining),
        channels=[],
    )


@router.delete("/data")
def delete_all_data(body: DeleteDataRequest, user: CurrentUser, db: DbSession) -> dict:
    if body.confirmation != CONFIRMATION_PHRASE:
        raise ApiError(ErrorCode.CONFIRMATION_REQUIRED, "二次确认短语不匹配。")

    storage = get_storage()
    # 删除音频文件与节目（级联删除知识点与回忆题）
    programs = db.execute(
        select(Program).where(Program.user_id == user.id)
    ).scalars().all()
    for program in programs:
        if program.audio_key:
            storage.delete(user.id, program.audio_key)
        db.delete(program)
    db.flush()

    # 删除任务（级联删除步骤）与资料
    for task in db.execute(
        select(GenerationTask).where(GenerationTask.user_id == user.id)
    ).scalars().all():
        db.delete(task)
    for source in db.execute(
        select(LearningSource).where(LearningSource.user_id == user.id)
    ).scalars().all():
        db.delete(source)
    db.execute(delete(DailyQuotaUsage).where(DailyQuotaUsage.user_id == user.id))

    storage.delete_user(user.id)
    db.commit()
    return {"ok": True}
