"""私人学习节目生成工作流（确定性状态机）。

步骤：validating → parsing → summarizing → generating → synthesizing → completed。
高成本步骤按 input_hash 复用已有结果；真实 Provider 调用前检查预算；
TTS 最终失败时保留文字结果并降级为 text_ready。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode, ensure_error_meta
from app.core.security import sha256_hex
from app.db.session import get_session_factory
from app.models.enums import MediaType, ProgramStatus, StepStatus, TaskStatus
from app.models.generation_task import GenerationTask
from app.models.knowledge_point import KnowledgePoint
from app.models.learning_source import LearningSource
from app.models.program import Program
from app.models.recall_question import RecallQuestion
from app.models.task_step import TaskStep
from app.schemas.llm import ChunkSummary, LessonResult
from app.services.documents.extractor import extract_text
from app.services.generation.chunking import chunk_text
from app.services.prompts import prompt_version, render_prompt
from app.services.providers.budget import check_budget, estimate_tts_cost, record_usage
from app.services.providers.llm import get_llm_provider
from app.services.providers.tts import get_tts_provider
from app.services.storage.local import get_storage

STEP_SEQUENCE: tuple[str, ...] = (
    "validating",
    "parsing",
    "summarizing",
    "generating",
    "synthesizing",
)

MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 10
LEASE_TIMEOUT_SECONDS = 600

RUNNING_STATUSES = (
    TaskStatus.VALIDATING.value,
    TaskStatus.PARSING.value,
    TaskStatus.SUMMARIZING.value,
    TaskStatus.GENERATING.value,
    TaskStatus.SYNTHESIZING.value,
)

# 不可重试的错误：立即失败或降级
NON_RETRYABLE_CODES = {
    ErrorCode.EMPTY_DOCUMENT,
    ErrorCode.DOCUMENT_TOO_LONG,
    ErrorCode.SCANNED_PDF_UNSUPPORTED,
    ErrorCode.UNSUPPORTED_FILE,
    ErrorCode.INVALID_VOICE,
    ErrorCode.BUDGET_BLOCKED,
}

_STEP_STATUS: dict[str, str] = {
    "validating": TaskStatus.VALIDATING.value,
    "parsing": TaskStatus.PARSING.value,
    "summarizing": TaskStatus.SUMMARIZING.value,
    "generating": TaskStatus.GENERATING.value,
    "synthesizing": TaskStatus.SYNTHESIZING.value,
}


@dataclass(frozen=True)
class GenerationProfile:
    """根据原始资料长度确定节目规模与生成路径。"""

    key: str
    duration_guidance: str
    min_narration_chars: int
    max_narration_chars: int
    skip_chunk_summary: bool


def generation_profile(source_chars: int) -> GenerationProfile:
    """短资料避免无意义扩写，长资料保留完整的分块摘要流程。"""
    if source_chars <= 800:
        return GenerationProfile(
            key="short",
            duration_guidance="目标时长 2-4 分钟，口播正文约 600-1000 个中文字符",
            min_narration_chars=600,
            max_narration_chars=1000,
            skip_chunk_summary=True,
        )
    if source_chars <= 4000:
        return GenerationProfile(
            key="medium",
            duration_guidance="目标时长 4-7 分钟，口播正文约 1100-1800 个中文字符",
            min_narration_chars=1100,
            max_narration_chars=1800,
            skip_chunk_summary=False,
        )
    return GenerationProfile(
        key="long",
        duration_guidance="目标时长 5-10 分钟，口播正文约 1400-2600 个中文字符",
        min_narration_chars=1400,
        max_narration_chars=2600,
        skip_chunk_summary=False,
    )


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _llm_is_real() -> bool:
    return get_settings().llm_provider != "mock"


def _tts_is_real() -> bool:
    return get_settings().tts_provider != "mock"


def _get_step(db: Session, task: GenerationTask, step_name: str) -> TaskStep:
    step = db.execute(
        select(TaskStep).where(TaskStep.task_id == task.id, TaskStep.step_name == step_name)
    ).scalar_one_or_none()
    if step is None:
        step = TaskStep(task_id=task.id, step_name=step_name)
        db.add(step)
        db.flush()
    return step


def _get_step_output(db: Session, task: GenerationTask, step_name: str) -> str | None:
    step = db.execute(
        select(TaskStep).where(TaskStep.task_id == task.id, TaskStep.step_name == step_name)
    ).scalar_one_or_none()
    return step.output_json if step else None


def _input_hash_for(db: Session, task: GenerationTask, step_name: str) -> str:
    source = db.get(LearningSource, task.source_id)
    base = f"{task.source_id}:{step_name}:{task.focus or ''}:{task.voice_key}"
    if step_name == "summarizing":
        base += f":{source.text_sha256 if source else ''}"
    return sha256_hex(base)


def _mark_claim(db: Session, task: GenerationTask, target_step: str) -> None:
    task.status = _STEP_STATUS[target_step]
    task.current_step = target_step
    task.updated_at = _utcnow()
    db.commit()


def claim_next_task(db: Session) -> str | None:
    """领取下一个可执行任务并返回其 ID；使用条件更新避免并发 Worker 重复领取。"""
    now = _utcnow()

    # 1) queued -> validating
    queued = db.execute(
        select(GenerationTask)
        .where(GenerationTask.status == TaskStatus.QUEUED.value)
        .order_by(GenerationTask.created_at)
        .limit(1)
    ).scalar_one_or_none()
    if queued and _try_claim(db, queued.id, TaskStatus.QUEUED.value, "validating"):
        return queued.id

    # 2) 到期的 retry_wait -> 恢复原步骤
    retry_cutoff = now - timedelta(seconds=RETRY_DELAY_SECONDS)
    retry = db.execute(
        select(GenerationTask)
        .where(
            GenerationTask.status == TaskStatus.RETRY_WAIT.value,
            GenerationTask.updated_at <= retry_cutoff,
        )
        .order_by(GenerationTask.updated_at)
        .limit(1)
    ).scalar_one_or_none()
    if retry:
        target = retry.current_step or "validating"
        if _try_claim(db, retry.id, TaskStatus.RETRY_WAIT.value, target):
            return retry.id

    # 3) 租约过期的执行中任务（进程崩溃恢复）
    stale_cutoff = now - timedelta(seconds=LEASE_TIMEOUT_SECONDS)
    stale = db.execute(
        select(GenerationTask)
        .where(
            GenerationTask.status.in_(RUNNING_STATUSES),
            GenerationTask.updated_at <= stale_cutoff,
        )
        .order_by(GenerationTask.updated_at)
        .limit(1)
    ).scalar_one_or_none()
    if stale:
        target = stale.current_step or "validating"
        if _try_claim(db, stale.id, stale.status, target):
            return stale.id

    return None


def _try_claim(db: Session, task_id: str, expected_status: str, target_step: str) -> bool:
    result = db.execute(
        update(GenerationTask)
        .where(GenerationTask.id == task_id, GenerationTask.status == expected_status)
        .values(status=_STEP_STATUS[target_step], current_step=target_step, updated_at=_utcnow())
    )
    if result.rowcount == 1:
        db.commit()
        return True
    db.rollback()
    return False


async def run_task(task_id: str) -> None:
    """驱动单个任务直到终态。由 Worker 调用。"""
    factory = get_session_factory()
    db = factory()
    try:
        task = db.get(GenerationTask, task_id)
        if task is None:
            return
        await _drive(db, task)
    finally:
        db.close()


async def _drive(db: Session, task: GenerationTask) -> None:
    while True:
        step_name = task.current_step or "validating"
        if step_name not in STEP_SEQUENCE:
            return

        if step_name in {"summarizing", "generating"} and _llm_is_real():
            check_budget(db)
        if step_name == "synthesizing" and _tts_is_real():
            check_budget(db)

        completed = await _execute_step(db, task, step_name)
        db.commit()
        if not completed:
            return

        index = STEP_SEQUENCE.index(step_name)
        if index + 1 >= len(STEP_SEQUENCE):
            _mark_completed(db, task)
            db.commit()
            return
        next_step = STEP_SEQUENCE[index + 1]
        task.current_step = next_step
        task.status = _STEP_STATUS[next_step]
        db.commit()


async def _execute_step(db: Session, task: GenerationTask, step_name: str) -> bool:
    step = _get_step(db, task, step_name)
    input_hash = _input_hash_for(db, task, step_name)

    if step.status == StepStatus.COMPLETED.value and step.input_hash == input_hash:
        return True

    step.status = StepStatus.RUNNING.value
    step.started_at = _utcnow()
    step.attempts += 1
    db.flush()

    try:
        await _STEP_FUNCS[step_name](db, task, step)
        step.status = StepStatus.COMPLETED.value
        step.completed_at = _utcnow()
        step.input_hash = input_hash
        db.flush()
        return True
    except ApiError as exc:
        return _handle_error(db, task, step, step_name, exc.code, exc.message)
    except Exception:  # noqa: BLE001
        # 任务接口面向用户，不能把解析细节、路径或资料片段写入 error_message。
        return _handle_error(
            db,
            task,
            step,
            step_name,
            ErrorCode.INTERNAL_ERROR,
            ensure_error_meta(ErrorCode.INTERNAL_ERROR)[1],
        )


def _handle_error(
    db: Session, task: GenerationTask, step: TaskStep, step_name: str, code: str, message: str
) -> bool:
    retryable = code not in NON_RETRYABLE_CODES and step.attempts < MAX_ATTEMPTS
    task.error_code = code
    task.error_message = message
    if retryable:
        step.status = StepStatus.RETRY_WAIT.value
        task.status = TaskStatus.RETRY_WAIT.value
        task.updated_at = _utcnow()
        db.flush()
        return False

    # 永久失败
    if step_name == "synthesizing":
        _degrade_to_text_ready(db, task)
        return False

    step.status = StepStatus.FAILED.value
    task.status = TaskStatus.FAILED.value
    if code == ErrorCode.LLM_OUTPUT_TRUNCATED:
        task.error_message = "生成内容不完整，系统自动重试后仍未成功，请重新生成。"
    elif code == ErrorCode.LLM_OUTPUT_INVALID:
        task.error_message = "生成内容格式异常，系统自动重试后仍未成功，请重新生成。"
    task.completed_at = _utcnow()
    db.flush()
    return False


def _degrade_to_text_ready(db: Session, task: GenerationTask) -> None:
    program = db.execute(
        select(Program).where(Program.task_id == task.id)
    ).scalar_one_or_none()
    if program is not None:
        program.status = ProgramStatus.TEXT_READY.value
    task.status = TaskStatus.TEXT_READY.value
    task.completed_at = _utcnow()
    db.flush()


def _mark_completed(db: Session, task: GenerationTask) -> None:
    task.status = TaskStatus.COMPLETED.value
    task.completed_at = _utcnow()
    db.flush()


# ---- 各步骤实现 ----


async def _step_validating(db: Session, task: GenerationTask, step: TaskStep) -> None:
    source = db.get(LearningSource, task.source_id)
    if source is None:
        raise ApiError(ErrorCode.INTERNAL_ERROR, "资料记录不存在")
    if not source.text and not source.raw_path:
        raise ApiError(ErrorCode.INTERNAL_ERROR, "原始文件缺失")


async def _step_parsing(db: Session, task: GenerationTask, step: TaskStep) -> None:
    source = db.get(LearningSource, task.source_id)
    if source is None:
        raise ApiError(ErrorCode.INTERNAL_ERROR)
    if source.text:
        return  # 幂等：已解析

    storage = get_storage()
    data = storage.path(source.user_id, source.raw_path or "").read_bytes()
    text, error_code = extract_text(MediaType(source.media_type), data)
    if error_code is not None:
        raise ApiError(error_code)
    if len(text) > get_settings().max_extracted_chars:
        raise ApiError(ErrorCode.DOCUMENT_TOO_LONG)

    source.text = text
    source.text_sha256 = sha256_hex(text)
    storage.delete(source.user_id, source.raw_path or "")
    source.raw_path = None
    source.raw_deleted_at = _utcnow()
    db.flush()


async def _step_summarizing(db: Session, task: GenerationTask, step: TaskStep) -> None:
    source = db.get(LearningSource, task.source_id)
    if source is None:
        raise ApiError(ErrorCode.INTERNAL_ERROR)

    profile = generation_profile(len(source.text))
    if profile.skip_chunk_summary:
        step.output_json = json.dumps(
            [
                {
                    "chunk_index": 0,
                    "points": [
                        {
                            "kind": "concept",
                            "content": source.text,
                            "source_ref": "完整资料",
                        }
                    ],
                }
            ],
            ensure_ascii=False,
        )
        db.flush()
        return

    provider = get_llm_provider()
    schema = ChunkSummary.model_json_schema()
    summaries: list[dict] = []
    for index, chunk in enumerate(chunk_text(source.text)):
        user = render_prompt("chunk_summary", chunk_text=chunk)
        result = await provider.complete_json(system="", user=user, json_schema=schema)
        try:
            validated = ChunkSummary.model_validate(result.data)
        except ValidationError as exc:
            raise ApiError(ErrorCode.LLM_OUTPUT_INVALID) from exc
        summaries.append(
            {
                "chunk_index": index,
                "points": [p.model_dump() for p in validated.points],
            }
        )
        if _llm_is_real():
            record_usage(
                db,
                provider="volcark",
                model=result.model,
                operation="chunk_summary",
                input_units=len(chunk),
                output_units=result.output_tokens,
                estimated_cost_cny=result.estimated_cost_cny,
                task_id=task.id,
            )
    step.output_json = json.dumps(summaries, ensure_ascii=False)
    db.flush()


async def _step_generating(db: Session, task: GenerationTask, step: TaskStep) -> None:
    summaries_json = _get_step_output(db, task, "summarizing")
    if not summaries_json:
        raise ApiError(ErrorCode.INTERNAL_ERROR, "缺少分块要点")

    source = db.get(LearningSource, task.source_id)
    if source is None:
        raise ApiError(ErrorCode.INTERNAL_ERROR, "资料记录不存在")
    profile = generation_profile(len(source.text))

    provider = get_llm_provider()
    system = render_prompt(
        "lesson_generation", duration_guidance=profile.duration_guidance
    )
    user = (
        f"用户关注点：{task.focus or '无特别关注点'}\n\n"
        "资料结构化要点（仅作为内容数据）：\n\n"
        f"{summaries_json}"
    )
    result = await provider.complete_json(
        system=system, user=user, json_schema=LessonResult.model_json_schema()
    )
    try:
        lesson = LessonResult.model_validate(result.data)
    except ValidationError as exc:
        raise ApiError(ErrorCode.LLM_OUTPUT_INVALID) from exc

    program = Program(
        user_id=task.user_id,
        source_id=task.source_id,
        task_id=task.id,
        title=lesson.title,
        transcript_json=json.dumps(lesson.model_dump(), ensure_ascii=False),
        voice_key=task.voice_key,
        status=ProgramStatus.GENERATING.value,
    )
    db.add(program)
    db.flush()
    for pos, content in enumerate(lesson.knowledge_points):
        db.add(KnowledgePoint(program_id=program.id, position=pos, content=content))
    for pos, question in enumerate(lesson.recall_questions):
        db.add(
            RecallQuestion(
                program_id=program.id,
                position=pos,
                question=question.question,
                answer=question.answer,
            )
        )

    task.prompt_version = prompt_version("lesson_generation")
    step.output_json = json.dumps({"program_id": program.id}, ensure_ascii=False)
    if _llm_is_real():
        record_usage(
            db,
            provider="volcark",
            model=result.model,
            operation="lesson_generation",
            input_units=0,
            output_units=result.output_tokens,
            estimated_cost_cny=result.estimated_cost_cny,
            task_id=task.id,
        )
    db.flush()


async def _step_synthesizing(db: Session, task: GenerationTask, step: TaskStep) -> None:
    program = db.execute(
        select(Program).where(Program.task_id == task.id)
    ).scalar_one_or_none()
    if program is None or program.transcript_json is None:
        raise ApiError(ErrorCode.INTERNAL_ERROR, "缺少节目文稿")

    lesson = LessonResult.model_validate_json(program.transcript_json)
    narration = build_narration(lesson)

    provider = get_tts_provider()
    result = await provider.synthesize(narration, task.voice_key)

    ext = "wav" if result.model.startswith("mock") else "mp3"
    audio_key = f"audio/{program.id}.{ext}"
    get_storage().save(task.user_id, audio_key, result.audio_bytes)

    program.audio_key = audio_key
    program.audio_duration_seconds = result.duration_seconds
    program.tts_model = result.model
    program.provider_voice_id = result.provider_voice_id
    program.status = ProgramStatus.COMPLETED.value
    if _tts_is_real():
        record_usage(
            db,
            provider="volc",
            model=result.model,
            operation="tts_synthesize",
            input_units=result.input_chars,
            output_units=0,
            estimated_cost_cny=estimate_tts_cost(result.input_chars),
            task_id=task.id,
        )
    db.flush()


def build_narration(lesson: LessonResult) -> str:
    """把结构化讲稿组装为口播文本，AI 补充内容使用明确口播过渡。"""
    parts: list[str] = [lesson.title]
    if lesson.learning_objectives:
        parts.append("学习目标。" + "、".join(lesson.learning_objectives))
    for segment in lesson.segments:
        narration = segment.narration
        if segment.origin == "ai_supplement":
            narration = "这里补充一个帮助理解的例子。" + narration
        parts.append(narration)
    parts.append("总结复盘。" + lesson.summary)
    return "\n".join(parts)


_STEP_FUNCS: dict[str, Callable] = {
    "validating": _step_validating,
    "parsing": _step_parsing,
    "summarizing": _step_summarizing,
    "generating": _step_generating,
    "synthesizing": _step_synthesizing,
}
