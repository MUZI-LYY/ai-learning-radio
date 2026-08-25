"""内容哈希工具。"""

from __future__ import annotations

import hashlib


def sha256_hex(data: str) -> str:
    """普通 SHA-256 十六进制摘要，用于内容哈希（非凭证）。"""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
