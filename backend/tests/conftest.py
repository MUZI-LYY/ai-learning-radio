"""pytest 夹具。

通过环境变量在导入应用模块前注入独立临时 SQLite 与私有存储目录，
避免污染开发数据；每个测试前重建空库。
"""

from __future__ import annotations

import os
import shutil
import tempfile

# 必须在导入应用模块前设置，否则模块级单例会绑定默认路径
_TEST_ROOT = tempfile.mkdtemp(prefix="airadio-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_ROOT}/test.db"
os.environ["PRIVATE_STORAGE_ROOT"] = f"{_TEST_ROOT}/private"
# 测试强制使用 mock provider，避免读入真实 .env 后误调线上 LLM/TTS
os.environ["LLM_PROVIDER"] = "mock"
os.environ["TTS_PROVIDER"] = "mock"
os.environ["LLM_API_KEY"] = ""
os.environ["TTS_API_KEY"] = ""
os.environ["PROVIDER_CALLS_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402, F401
from app.api.deps import get_rate_limiter  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.security import generate_invite_code, hash_credential  # noqa: E402
from app.db.base import Base, utcnow  # noqa: E402
from app.db.session import build_engine, get_session_factory, reset_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.invite_credential import InviteCredential  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_state():
    """每个测试前重建空库并清空私有存储。"""
    reset_engine()
    engine = build_engine(get_settings().database_url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    engine.dispose()
    shutil.rmtree(get_settings().private_storage_root, ignore_errors=True)
    get_rate_limiter().reset()
    yield
    get_rate_limiter().reset()


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def make_invite():
    """创建用户 + 邀请码，返回 (明文邀请码, 用户)。"""

    def _make(code: str | None = None, *, revoked: bool = False, role: str = UserRole.USER.value):
        code = code or generate_invite_code()
        factory = get_session_factory()
        with factory() as db:
            user = User(display_name="测试用户", role=role)
            db.add(user)
            db.flush()
            db.add(
                InviteCredential(
                    user_id=user.id,
                    code_digest=hash_credential(code, get_settings().invite_code_pepper),
                    revoked_at=utcnow() if revoked else None,
                )
            )
            db.commit()
            return code, user

    return _make


@pytest.fixture()
def login(client, make_invite):
    """登录并返回 (明文邀请码, 用户)。"""

    def _login(role: str = UserRole.USER.value):
        code, user = make_invite(role=role)
        response = client.post("/api/v1/auth/invite", json={"invite_code": code})
        assert response.status_code == 200
        return code, user

    return _login
