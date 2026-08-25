"""匿名事件白名单与幂等去重测试。"""

from __future__ import annotations

import asyncio

from app.db.session import get_session_factory
from app.models.analytics_event import AnalyticsEvent
from app.models.generation_task import GenerationTask
from app.services.generation.workflow import run_task


def _create_and_complete(client):
    task_id = client.post(
        "/api/v1/learning/tasks",
        files={"file": ("a.md", b"# t\nbody\n", "text/markdown")},
        data={"focus": "", "voice_key": "elegant_youth"},
    ).json()["task_id"]
    factory = get_session_factory()
    for _ in range(10):
        asyncio.run(run_task(task_id))
        with factory() as db:
            status = db.get(GenerationTask, task_id).status
        if status in {"completed", "text_ready", "failed"}:
            break
    return client.get(f"/api/v1/tasks/{task_id}").json()["program_id"]


def test_invalid_event_rejected(client, login):
    login()
    response = client.post("/api/v1/events", json={"event_name": "hack_event"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_EVENT"


def test_play_event_idempotent(client, login):
    login()
    program_id = _create_and_complete(client)

    for _ in range(2):
        response = client.post(
            "/api/v1/events",
            json={"event_name": "program_play_completed", "program_id": program_id},
        )
        assert response.status_code == 204

    factory = get_session_factory()
    with factory() as db:
        count = (
            db.query(AnalyticsEvent)
            .filter_by(event_name="program_play_completed", program_id=program_id)
            .count()
        )
    assert count == 1


def test_event_requires_owned_program(client, login, make_invite):
    login()
    program_id = _create_and_complete(client)

    client.post("/api/v1/auth/logout")
    code_b, _ = make_invite()
    client.post("/api/v1/auth/invite", json={"invite_code": code_b})

    response = client.post(
        "/api/v1/events",
        json={"event_name": "program_play_started", "program_id": program_id},
    )
    assert response.status_code == 404
