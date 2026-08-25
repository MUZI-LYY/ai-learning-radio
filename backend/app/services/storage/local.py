"""本地受控文件存储。

用户文件按 user_id 隔离；存储 key 为相对路径，禁止 `..` 路径穿越。
上传原始文件解析成功后删除；音频只保存受控对象键。
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.core.config import get_settings


class LocalStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _safe_path(self, user_id: str, relative_key: str) -> Path:
        key = Path(relative_key)
        if key.is_absolute() or ".." in key.parts:
            raise ValueError("非法存储键")
        return (self.root / user_id / key).resolve()

    def save(self, user_id: str, relative_key: str, data: bytes) -> str:
        path = self._safe_path(user_id, relative_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return relative_key

    def path(self, user_id: str, relative_key: str) -> Path:
        return self._safe_path(user_id, relative_key)

    def exists(self, user_id: str, relative_key: str) -> bool:
        return self._safe_path(user_id, relative_key).exists()

    def delete(self, user_id: str, relative_key: str) -> bool:
        path = self._safe_path(user_id, relative_key)
        try:
            path.unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def delete_user(self, user_id: str) -> None:
        shutil.rmtree(self.root / user_id, ignore_errors=True)


def get_storage() -> LocalStorage:
    """每次读取最新配置（不缓存），便于测试通过环境变量注入存储根目录。"""
    return LocalStorage(get_settings().private_storage_root)
