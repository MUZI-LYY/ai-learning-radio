"""上传学习资料并创建私人学习任务。"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from app.api.deps import CurrentUser, DbSession
from app.schemas.task import TaskCreateResponse
from app.services.generation.tasks import create_private_task

router = APIRouter(prefix="/learning", tags=["learning"])


@router.post("/tasks", response_model=TaskCreateResponse, status_code=201)
async def create_task(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    focus: str = Form(""),
    voice_key: str = Form(""),
) -> TaskCreateResponse:
    data = await file.read()
    task_id, remaining = create_private_task(
        db,
        user=user,
        filename=file.filename or "",
        content_type=file.content_type,
        data=data,
        focus=focus or None,
        voice_key=voice_key or None,
    )
    return TaskCreateResponse(task_id=task_id, status="queued", quota_remaining=remaining)
