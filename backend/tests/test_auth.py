from __future__ import annotations

from app.core.config import get_settings
from app.services.auth.session import COOKIE_NAME


def _login(client, code: str):
    return client.post("/api/v1/auth/invite", json={"invite_code": code})


def test_invite_success_sets_cookie(client, make_invite):
    code, user = make_invite()
    response = _login(client, code)

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == user.id
    assert body["user"]["display_name"] == "测试用户"
    assert COOKIE_NAME in response.cookies


def test_invite_invalid_code(client):
    response = _login(client, "definitely-wrong-code")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_INVITE"


def test_invite_revoked_code(client, make_invite):
    code, _ = make_invite(revoked=True)
    response = _login(client, code)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "REVOKED_INVITE"


def test_error_structure_has_request_id(client):
    response = _login(client, "wrong")
    error = response.json()["error"]
    assert set(error.keys()) == {"code", "message", "request_id"}
    assert error["request_id"]


def test_me_requires_auth(client):
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_returns_quota_after_login(client, make_invite):
    code, _ = make_invite()
    _login(client, code)

    response = client.get("/api/v1/me")
    assert response.status_code == 200
    body = response.json()
    assert body["quota"] == {
        "used": 0,
        "limit": get_settings().daily_private_program_limit,
        "remaining": get_settings().daily_private_program_limit,
    }
    assert body["channels"] == []


def test_logout_revokes_session(client, make_invite):
    code, _ = make_invite()
    _login(client, code)
    assert client.get("/api/v1/me").status_code == 200

    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200

    assert client.get("/api/v1/me").status_code == 401


def test_cross_user_cannot_see_others(client, make_invite):
    code_a, user_a = make_invite()
    make_invite()
    _login(client, code_a)
    me = client.get("/api/v1/me").json()
    assert me["user"]["id"] == user_a.id
