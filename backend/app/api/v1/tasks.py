"""任务状态查询与 TTS 单独重试。"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import ApiError, ErrorCode
from app.models.enums import StepStatus, TaskStatus
from app.models.generation_task import GenerationTask
from app.models.program import Program
from app.models.task_step import TaskStep
from app.schemas.task import TaskStatusResponse
from app.services.generation.workflow import RETRY_DELAY_SECONDS, _utcnow

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _owned_task(db: DbSession, user_id: str, task_id: str) -> GenerationTask:
    task = db.execute(
        select(GenerationTask).where(
            GenerationTask.id == task_id, GenerationTask.user_id == user_id
        )
    ).scalar_one_or_none()
    if task is None:
        raise ApiError(ErrorCode.RESOURCE_NOT_FOUND)
    return task


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task(task_id: str, user: CurrentUser, db: DbSession) -> TaskStatusResponse:
    task = _owned_task(db, user.id, task_id)
    program_id = db.execute(
        select(Program.id).where(Program.task_id == task.id)
    ).scalar_one_or_none()
    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        current_step=task.current_step,
        error_code=task.error_code,
        error_message=task.error_message,
        program_id=program_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.post("/{task_id}/retry-audio", response_model=TaskStatusResponse)
def retry_audio(task_id: str, user: CurrentUser, db: DbSession) -> TaskStatusResponse:
    task = _owned_task(db, user.id, task_id)
    if task.status != TaskStatus.TEXT_READY.value:
        raise ApiError(ErrorCode.INVALID_TASK_STATE, "仅文字稿就绪的节目可以单独重试音频。")

    step = db.execute(
        select(TaskStep).where(TaskStep.task_id == task.id, TaskStep.step_name == "synthesizing")
    ).scalar_one_or_none()
    if step is not None:
        step.status = StepStatus.PENDING.value
        step.attempts = 0
        step.completed_at = None

    task.status = TaskStatus.RETRY_WAIT.value
    task.current_step = "synthesizing"
    task.updated_at = _utcnow() - timedelta(seconds=RETRY_DELAY_SECONDS + 1)
    task.error_code = None
    task.error_message = None
    db.commit()

    program_id = db.execute(
        select(Program.id).where(Program.task_id == task.id)
    ).scalar_one_or_none()
    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        current_step=task.current_step,
        error_code=None,
        error_message=None,
        program_id=program_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.post("/{task_id}/retry-generation", response_model=TaskStatusResponse)
def retry_generation(task_id: str, user: CurrentUser, db: DbSession) -> TaskStatusResponse:
    """用户显式确认后，原地重试失败的摘要生成，不重复扣上传额度。"""
    task = _owned_task(db, user.id, task_id)
    if task.status != TaskStatus.FAILED.value or task.current_step != "summarizing":
        raise ApiError(ErrorCode.INVALID_TASK_STATE, "仅摘要生成失败的任务可以重新生成。")

    step = db.execute(
        select(TaskStep).where(
            TaskStep.task_id == task.id,
            TaskStep.step_name == "summarizing",
        )
    ).scalar_one_or_none()
    if step is None:
        raise ApiError(ErrorCode.INVALID_TASK_STATE, "未找到可重试的生成步骤。")

    step.status = StepStatus.PENDING.value
    step.attempts = 0
    step.output_json = None
    step.completed_at = None

    task.status = TaskStatus.RETRY_WAIT.value
    task.updated_at = _utcnow() - timedelta(seconds=RETRY_DELAY_SECONDS + 1)
    task.completed_at = None
    task.error_code = None
    task.error_message = None
    db.commit()

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        current_step=task.current_step,
        error_code=None,
        error_message=None,
        program_id=None,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
