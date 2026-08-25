"""私人节目：列表、详情、鉴权音频、重新生成、删除。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import ApiError, ErrorCode
from app.models.learning_source import LearningSource
from app.models.program import Program
from app.schemas.llm import LessonResult
from app.schemas.program import ProgramDetail, ProgramSummary, RecallQuestionOut, SegmentOut
from app.schemas.task import TaskCreateResponse
from app.services.generation.tasks import regenerate_task
from app.services.providers.voices import get_voice
from app.services.storage.local import get_storage

router = APIRouter(prefix="/programs", tags=["programs"])


def _owned_program(db: DbSession, user_id: str, program_id: str) -> Program:
    program = db.execute(
        select(Program).where(
            Program.id == program_id,
            Program.user_id == user_id,
            Program.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if program is None:
        raise ApiError(ErrorCode.RESOURCE_NOT_FOUND)
    return program


def _source_name(db: DbSession, source_id: str) -> str:
    source = db.get(LearningSource, source_id)
    return source.original_name if source else ""


def _summary(db: DbSession, program: Program) -> ProgramSummary:
    voice = get_voice(program.voice_key or "")
    return ProgramSummary(
        id=program.id,
        title=program.title or "",
        status=program.status,
        voice_key=program.voice_key,
        voice_name=voice.display_name if voice else None,
        audio_duration_seconds=program.audio_duration_seconds,
        audio_ready=program.audio_key is not None,
        source_name=_source_name(db, program.source_id),
        created_at=program.created_at,
    )


@router.get("", response_model=list[ProgramSummary])
def list_programs(user: CurrentUser, db: DbSession) -> list[ProgramSummary]:
    programs = db.execute(
        select(Program)
        .where(Program.user_id == user.id, Program.deleted_at.is_(None))
        .order_by(Program.created_at.desc())
    ).scalars().all()
    return [_summary(db, p) for p in programs]


@router.get("/{program_id}", response_model=ProgramDetail)
def get_program(program_id: str, user: CurrentUser, db: DbSession) -> ProgramDetail:
    program = _owned_program(db, user.id, program_id)
    if program.transcript_json is None:
        raise ApiError(ErrorCode.RESOURCE_NOT_FOUND, "节目文稿尚未生成。")

    lesson = LessonResult.model_validate_json(program.transcript_json)
    voice = get_voice(program.voice_key or "")
    return ProgramDetail(
        id=program.id,
        title=program.title or "",
        status=program.status,
        source_name=_source_name(db, program.source_id),
        voice_key=program.voice_key,
        voice_name=voice.display_name if voice else None,
        audio_duration_seconds=program.audio_duration_seconds,
        audio_ready=program.audio_key is not None,
        learning_objectives=lesson.learning_objectives,
        segments=[
            SegmentOut(section=s.section, origin=s.origin, narration=s.narration)
            for s in lesson.segments
        ],
        summary=lesson.summary,
        knowledge_points=lesson.knowledge_points,
        recall_questions=[
            RecallQuestionOut(question=q.question, answer=q.answer)
            for q in lesson.recall_questions
        ],
        created_at=program.created_at,
    )


@router.get("/{program_id}/audio")
def get_audio(program_id: str, user: CurrentUser, db: DbSession) -> FileResponse:
    program = _owned_program(db, user.id, program_id)
    if program.audio_key is None:
        raise ApiError(ErrorCode.AUDIO_NOT_READY)

    path = get_storage().path(user.id, program.audio_key)
    if not path.exists():
        raise ApiError(ErrorCode.AUDIO_NOT_READY)

    media_type = "audio/mpeg" if program.audio_key.endswith(".mp3") else "audio/wav"
    return FileResponse(path, media_type=media_type)


@router.post("/{program_id}/regenerate", response_model=TaskCreateResponse, status_code=201)
def regenerate(program_id: str, user: CurrentUser, db: DbSession) -> TaskCreateResponse:
    program = _owned_program(db, user.id, program_id)
    task_id, remaining = regenerate_task(db, user=user, program=program)
    return TaskCreateResponse(task_id=task_id, status="queued", quota_remaining=remaining)


@router.delete("/{program_id}")
def delete_program(program_id: str, user: CurrentUser, db: DbSession) -> dict:
    program = _owned_program(db, user.id, program_id)
    storage = get_storage()
    if program.audio_key:
        storage.delete(user.id, program.audio_key)
    program.deleted_at = _utcnow()
    db.commit()
    return {"ok": True}


def _utcnow():
    from datetime import UTC, datetime

    return datetime.now(UTC)
