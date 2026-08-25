"""统一错误码与 API 错误异常。

所有面向用户的错误都使用固定的 `error` 结构：
    {"error": {"code": "...", "message": "...", "request_id": "..."}}
用户只能看到可操作的中文提示，绝不泄露堆栈或内部路径。
"""

from __future__ import annotations

from http import HTTPStatus


class ErrorCode:
    """错误码常量。值本身即 API 响应中的稳定 code。"""

    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"

    # 资源
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    INVALID_TASK_STATE = "INVALID_TASK_STATE"
    INVALID_VOICE = "INVALID_VOICE"
    INVALID_EVENT = "INVALID_EVENT"
    AUDIO_NOT_READY = "AUDIO_NOT_READY"

    # 文件与文档
    UNSUPPORTED_FILE = "UNSUPPORTED_FILE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    EMPTY_DOCUMENT = "EMPTY_DOCUMENT"
    DOCUMENT_TOO_LONG = "DOCUMENT_TOO_LONG"
    SCANNED_PDF_UNSUPPORTED = "SCANNED_PDF_UNSUPPORTED"

    # 额度与预算
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    BUDGET_BLOCKED = "BUDGET_BLOCKED"

    # 请求与校验
    INVALID_REQUEST = "INVALID_REQUEST"

    # 服务端
    LLM_OUTPUT_TRUNCATED = "LLM_OUTPUT_TRUNCATED"
    LLM_OUTPUT_INVALID = "LLM_OUTPUT_INVALID"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# 错误码 -> (HTTP 状态码, 默认中文提示)
_CODE_META: dict[str, tuple[int, str]] = {
    ErrorCode.CONFIRMATION_REQUIRED: (HTTPStatus.BAD_REQUEST, "请提交二次确认短语。"),
    ErrorCode.RESOURCE_NOT_FOUND: (HTTPStatus.NOT_FOUND, "资源不存在或无权访问。"),
    ErrorCode.INVALID_TASK_STATE: (HTTPStatus.CONFLICT, "任务当前状态不允许该操作。"),
    ErrorCode.INVALID_VOICE: (HTTPStatus.BAD_REQUEST, "不支持的音色。"),
    ErrorCode.INVALID_EVENT: (HTTPStatus.BAD_REQUEST, "不支持的事件类型。"),
    ErrorCode.AUDIO_NOT_READY: (HTTPStatus.CONFLICT, "音频尚未生成完成。"),
    ErrorCode.UNSUPPORTED_FILE: (HTTPStatus.BAD_REQUEST, "不支持的文件格式。"),
    ErrorCode.FILE_TOO_LARGE: (HTTPStatus.BAD_REQUEST, "文件超过大小限制。"),
    ErrorCode.EMPTY_DOCUMENT: (HTTPStatus.BAD_REQUEST, "提取后的正文为空。"),
    ErrorCode.DOCUMENT_TOO_LONG: (
        HTTPStatus.BAD_REQUEST,
        "提取后的正文超过 3 万字，请缩短后重试。",
    ),
    ErrorCode.SCANNED_PDF_UNSUPPORTED: (
        HTTPStatus.BAD_REQUEST,
        "该 PDF 无法提取可复制的文字，暂不支持扫描版 PDF。",
    ),
    ErrorCode.QUOTA_EXCEEDED: (HTTPStatus.TOO_MANY_REQUESTS, "今日生成额度已用完。"),
    ErrorCode.BUDGET_BLOCKED: (HTTPStatus.SERVICE_UNAVAILABLE, "系统预算不足，暂时无法生成。"),
    ErrorCode.INVALID_REQUEST: (HTTPStatus.UNPROCESSABLE_ENTITY, "请求参数有误。"),
    ErrorCode.LLM_OUTPUT_TRUNCATED: (
        HTTPStatus.BAD_GATEWAY,
        "生成内容不完整，正在自动重试。",
    ),
    ErrorCode.LLM_OUTPUT_INVALID: (
        HTTPStatus.BAD_GATEWAY,
        "生成内容格式异常，正在自动重试。",
    ),
    ErrorCode.INTERNAL_ERROR: (HTTPStatus.INTERNAL_SERVER_ERROR, "服务暂时不可用，请稍后再试。"),
}


class ApiError(Exception):
    """可安全返回给用户的 API 错误。"""

    def __init__(
        self,
        code: str,
        message: str | None = None,
        *,
        status_code: int | None = None,
    ) -> None:
        self.code = code
        default_status, default_message = _CODE_META.get(
            code, (HTTPStatus.INTERNAL_SERVER_ERROR, "服务暂时不可用，请稍后再试。")
        )
        self.message = message or default_message
        self.status_code = status_code or default_status
        super().__init__(self.message)


def ensure_error_meta(code: str) -> tuple[int, str]:
    """返回错误码对应的 (状态码, 默认消息)，未知码回落到内部错误。"""
    return _CODE_META.get(
        code, (HTTPStatus.INTERNAL_SERVER_ERROR, "服务暂时不可用，请稍后再试。")
    )
