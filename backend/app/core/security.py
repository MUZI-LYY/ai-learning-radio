"""认证相关的哈希与令牌工具。

- 邀请码和会话令牌都是高熵随机串，只保存「加 pepper 的摘要」，不保存明文。
- 使用 HMAC-SHA256（带 pepper 作为密钥），并用常量时间比较防时序攻击。
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def hash_credential(secret: str, pepper: str) -> str:
    """计算带 pepper 的 HMAC-SHA256 摘要，返回十六进制字符串。"""
    return hmac.new(pepper.encode("utf-8"), secret.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_credential(secret: str, expected_digest: str, pepper: str) -> bool:
    """常量时间比较明文与摘要是否匹配。"""
    candidate = hash_credential(secret, pepper)
    return hmac.compare_digest(candidate, expected_digest)


def generate_invite_code(length: int = 32) -> str:
    """生成足够长、可撤销的随机邀请码。"""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def generate_session_token(length: int = 43) -> str:
    """生成随机会话令牌（43 字符，约 256 bit 熵）。"""
    return secrets.token_urlsafe(length)


def sha256_hex(data: str) -> str:
    """普通 SHA-256 十六进制摘要，用于内容哈希（非凭证）。"""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
