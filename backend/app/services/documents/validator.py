"""上传文件校验：扩展名、声明 MIME、文件头签名、大小。

不因改后缀接受任意文件。
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.errors import ErrorCode
from app.models.enums import MediaType

_ALLOWED_EXTENSIONS = {".docx": MediaType.DOCX, ".pdf": MediaType.PDF, ".md": MediaType.MARKDOWN}

# 各类型允许的声明 MIME（为空表示不强校验 MIME）
_ALLOWED_MIMES: dict[MediaType, set[str]] = {
    MediaType.DOCX: {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
    MediaType.PDF: {"application/pdf", "application/octet-stream"},
    MediaType.MARKDOWN: {
        "text/markdown",
        "text/x-markdown",
        "text/plain",
        "application/octet-stream",
        "text/x-markdown; charset=utf-8",
    },
}

# 明显冲突的 MIME：扩展名与声明 MIME 属于不同文档类型时拒绝
_CONFLICTING_MIMES: dict[MediaType, set[str]] = {
    MediaType.DOCX: {"application/pdf"},
    MediaType.PDF: {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    MediaType.MARKDOWN: {"application/pdf"},
}


def _media_type_from_filename(filename: str) -> MediaType | None:
    suffix = filename[filename.rfind("."):].lower() if "." in filename else ""
    return _ALLOWED_EXTENSIONS.get(suffix)


def _matches_signature(media_type: MediaType, head: bytes) -> bool:
    if media_type == MediaType.DOCX:
        # ZIP 文件头 PK\x03\x04
        return head[:4] == b"PK\x03\x04"
    if media_type == MediaType.PDF:
        return head[:5] == b"%PDF-"
    if media_type == MediaType.MARKDOWN:
        # 文本文件：无固定魔数，只要求不含二进制 NUL 字节
        return b"\x00" not in head
    return False


def validate_upload(
    filename: str, content_type: str | None, size_bytes: int, head: bytes
) -> tuple[MediaType | None, str | None]:
    """返回 (媒体类型, 错误码)；错误码为 None 表示通过。"""
    settings = get_settings()
    if size_bytes > settings.max_upload_mb * 1024 * 1024:
        return None, ErrorCode.FILE_TOO_LARGE

    media_type = _media_type_from_filename(filename)
    if media_type is None:
        return None, ErrorCode.UNSUPPORTED_FILE

    mime = (content_type or "").split(";")[0].strip().lower()
    if mime and media_type in _CONFLICTING_MIMES and mime in _CONFLICTING_MIMES[media_type]:
        return None, ErrorCode.UNSUPPORTED_FILE

    if not _matches_signature(media_type, head):
        return None, ErrorCode.UNSUPPORTED_FILE

    return media_type, None
