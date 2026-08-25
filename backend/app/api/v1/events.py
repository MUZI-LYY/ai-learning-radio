"""必要匿名事件上报（白名单 + 幂等去重）。"""

from __future__ import annotations

from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import ApiError, ErrorCode
from app.models.analytics_event import AnalyticsEvent
from app.models.program import Program

router = APIRouter(prefix="/events", tags=["events"])

EVENT_WHITELIST = {
    "invite_verified",
    "program_play_started",
    "program_play_50_percent",
    "program_play_completed",
}


class EventRequest(BaseModel):
    event_name: str
    program_id: str | None = None


@router.post("", status_code=204)
def report_event(body: EventRequest, user: CurrentUser, db: DbSession) -> Response:
    if body.event_name not in EVENT_WHITELIST:
        raise ApiError(ErrorCode.INVALID_EVENT)

    if body.program_id is not None:
        program = db.execute(
            select(Program.id).where(
                Program.id == body.program_id, Program.user_id == user.id
            )
        ).scalar_one_or_none()
        if program is None:
            raise ApiError(ErrorCode.RESOURCE_NOT_FOUND)

    # 幂等去重：同一用户、节目和关键进度事件只记录一次
    exists = db.execute(
        select(AnalyticsEvent.id).where(
            AnalyticsEvent.user_id == user.id,
            AnalyticsEvent.event_name == body.event_name,
            AnalyticsEvent.program_id == body.program_id,
        )
    ).scalar_one_or_none()
    if exists is None:
        db.add(
            AnalyticsEvent(
                user_id=user.id, event_name=body.event_name, program_id=body.program_id
            )
        )
        db.commit()

    return Response(status_code=204)
