from __future__ import annotations

from app.api.deps import LOCAL_USER_ID
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.models.user import User


def test_me_creates_local_user_without_login(client):
    response = client.get("/api/v1/me")

    assert response.status_code == 200
    body = response.json()
    assert body["user"] == {
        "id": LOCAL_USER_ID,
        "display_name": "本地用户",
        "role": "user",
    }
    assert body["quota"] == {
        "used": 0,
        "limit": get_settings().daily_private_program_limit,
        "remaining": get_settings().daily_private_program_limit,
    }


def test_me_reuses_the_same_local_user(client):
    first = client.get("/api/v1/me").json()["user"]["id"]
    second = client.get("/api/v1/me").json()["user"]["id"]

    assert first == second == LOCAL_USER_ID
    factory = get_session_factory()
    with factory() as db:
        assert db.query(User).count() == 1


def test_invite_and_logout_routes_are_removed(client):
    assert client.post("/api/v1/auth/invite", json={"invite_code": "unused"}).status_code == 404
    assert client.post("/api/v1/auth/logout").status_code == 404


def test_delete_all_data_preserves_local_identity(client):
    user_id = client.get("/api/v1/me").json()["user"]["id"]

    response = client.request(
        "DELETE",
        "/api/v1/me/data",
        json={"confirmation": "删除全部数据"},
    )

    assert response.status_code == 200
    assert client.get("/api/v1/me").json()["user"]["id"] == user_id


def test_error_structure_has_request_id(client):
    response = client.request(
        "DELETE",
        "/api/v1/me/data",
        json={"confirmation": "错误短语"},
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert set(error.keys()) == {"code", "message", "request_id"}
    assert error["request_id"]
