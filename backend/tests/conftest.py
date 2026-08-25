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
from app.api.deps import LOCAL_USER_ID  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import build_engine, get_session_factory, reset_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
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
    yield


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def login(client):
    """初始化并返回自动创建的本地用户。"""

    def _login(role: str = UserRole.USER.value):
        response = client.get("/api/v1/me")
        assert response.status_code == 200
        factory = get_session_factory()
        with factory() as db:
            user = db.get(User, LOCAL_USER_ID)
            assert user is not None
            user.role = role
            db.commit()
            return user

    return _login
