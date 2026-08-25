from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TaskCreateResponse(BaseModel):
    task_id: str
    status: str
    quota_remaining: int


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    current_step: str | None
    error_code: str | None
    error_message: str | None
    program_id: str | None
    created_at: datetime
    updated_at: datetime
