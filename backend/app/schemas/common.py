from __future__ import annotations

from pydantic import BaseModel


class ErrorBody(BaseModel):
    """统一错误响应结构。"""

    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody
