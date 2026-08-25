"""领域枚举与状态常量。

使用 Python `str` 枚举，保证存入数据库的是稳定字符串，也便于未来迁移 PostgreSQL。
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """值为字符串的枚举基类。"""

    def __str__(self) -> str:
        return self.value


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class MediaType(StrEnum):
    DOCX = "docx"
    PDF = "pdf"
    MARKDOWN = "markdown"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    PARSING = "parsing"
    SUMMARIZING = "summarizing"
    GENERATING = "generating"
    SYNTHESIZING = "synthesizing"
    RETRY_WAIT = "retry_wait"
    COMPLETED = "completed"
    TEXT_READY = "text_ready"  # 教学内容成功但 TTS 最终失败，任务以带警告的成功终态结束
    FAILED = "failed"


# 终态集合：任务不再被 Worker 领取。
TERMINAL_TASK_STATUSES = {TaskStatus.COMPLETED, TaskStatus.TEXT_READY, TaskStatus.FAILED}


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_WAIT = "retry_wait"


class ProgramStatus(StrEnum):
    GENERATING = "generating"
    COMPLETED = "completed"
    TEXT_READY = "text_ready"
    FAILED = "failed"


class ProviderKind(StrEnum):
    LLM = "llm"
    TTS = "tts"
