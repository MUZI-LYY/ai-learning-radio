"""创建私人学习任务：校验上传、冻结音色、原子扣减额度并落库。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import ApiError, ErrorCode
from app.db.base import uuid_str
from app.models.enums import TaskStatus
from app.models.generation_task import GenerationTask
from app.models.learning_source import LearningSource
from app.models.program import Program
from app.models.user import User
from app.services.documents.validator import validate_upload
from app.services.generation.quota import get_quota_record, remaining_quota
from app.services.providers.voices import default_voice_key, get_voice
from app.services.storage.local import get_storage


def create_private_task(
    db: Session,
    *,
    user: User,
    filename: str,
    content_type: str | None,
    data: bytes,
    focus: str | None,
    voice_key: str | None,
) -> tuple[str, int]:
    """创建任务并扣减当日额度；返回 (task_id, 剩余额度)。"""
    media_type, error_code = validate_upload(filename, content_type, len(data), data[:16])
    if error_code is not None:
        raise ApiError(error_code)

    if voice_key is not None and get_voice(voice_key) is None:
        raise ApiError(ErrorCode.INVALID_VOICE)
    voice_key = voice_key or default_voice_key()

    if remaining_quota(db, user.id) <= 0:
        raise ApiError(ErrorCode.QUOTA_EXCEEDED)

    raw_key = f"uploads/{uuid_str()}"
    get_storage().save(user.id, raw_key, data)

    source = LearningSource(
        user_id=user.id,
        original_name=filename,
        media_type=media_type.value,
        size_bytes=len(data),
        text="",
        text_sha256="",
        raw_path=raw_key,
    )
    db.add(source)
    db.flush()

    task = GenerationTask(
        user_id=user.id,
        source_id=source.id,
        status=TaskStatus.QUEUED.value,
        current_step="validating",
        focus=focus or None,
        voice_key=voice_key,
    )
    db.add(task)
    db.flush()

    # 创建任务与扣减额度处于同一事务
    record = get_quota_record(db, user.id)
    record.used_count += 1
    db.add(record)
    db.commit()

    return task.id, remaining_quota(db, user.id)


def regenerate_task(db: Session, *, user: User, program: Program) -> tuple[str, int]:
    """对已有节目重新生成：复用已解析资料，创建新任务并扣一次当日额度。"""
    if remaining_quota(db, user.id) <= 0:
        raise ApiError(ErrorCode.QUOTA_EXCEEDED)

    task = GenerationTask(
        user_id=user.id,
        source_id=program.source_id,
        status=TaskStatus.QUEUED.value,
        current_step="validating",
        focus=None,
        voice_key=program.voice_key or default_voice_key(),
    )
    db.add(task)
    db.flush()

    record = get_quota_record(db, user.id)
    record.used_count += 1
    db.add(record)
    db.commit()

    return task.id, remaining_quota(db, user.id)
