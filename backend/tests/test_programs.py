"""节目库、详情、删除与重新生成测试。"""

from __future__ import annotations

import asyncio

from app.db.session import get_session_factory
from app.models.generation_task import GenerationTask
from app.services.generation.workflow import run_task

TERMINAL = {"completed", "text_ready", "failed"}


def _run(task_id: str) -> str:
    factory = get_session_factory()
    for _ in range(10):
        asyncio.run(run_task(task_id))
        with factory() as db:
            status = db.get(GenerationTask, task_id).status
        if status in TERMINAL:
            return status
    return status


def _create(client, filename="a.md", content=b"# t\nbody text\n"):
    return client.post(
        "/api/v1/learning/tasks",
        files={"file": (filename, content, "text/markdown")},
        data={"focus": "", "voice_key": "elegant_youth"},
    )


def test_program_list_and_delete(client, login):
    login()
    task_id = _create(client).json()["task_id"]
    _run(task_id)
    program_id = client.get(f"/api/v1/tasks/{task_id}").json()["program_id"]

    programs = client.get("/api/v1/programs").json()
    assert len(programs) == 1
    assert programs[0]["id"] == program_id
    assert programs[0]["source_name"] == "a.md"
    assert programs[0]["audio_ready"] is True

    assert client.delete(f"/api/v1/programs/{program_id}").status_code == 200
    assert client.get(f"/api/v1/programs/{program_id}").status_code == 404
    assert client.get(f"/api/v1/programs/{program_id}/audio").status_code == 404
    assert client.get("/api/v1/programs").json() == []


def test_regenerate_creates_new_task_and_deducts_quota(client, login):
    login()
    task_id = _create(client).json()["task_id"]
    _run(task_id)
    program_id = client.get(f"/api/v1/tasks/{task_id}").json()["program_id"]

    response = client.post(f"/api/v1/programs/{program_id}/regenerate")
    assert response.status_code == 201
    new_task_id = response.json()["task_id"]
    assert response.json()["quota_remaining"] == 0
    assert new_task_id != task_id

    assert _run(new_task_id) == "completed"
    # 节目库现在有两期节目
    assert len(client.get("/api/v1/programs").json()) == 2


def test_delete_all_data_requires_confirmation(client, login):
    login()
    response = client.request("DELETE", "/api/v1/me/data", json={"confirmation": "错"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONFIRMATION_REQUIRED"


def test_delete_all_data_wipes_everything(client, login):
    login()
    task_id = _create(client).json()["task_id"]
    _run(task_id)
    program_id = client.get(f"/api/v1/tasks/{task_id}").json()["program_id"]

    response = client.request(
        "DELETE", "/api/v1/me/data", json={"confirmation": "删除全部数据"}
    )
    assert response.status_code == 200

    # 本地用户保留，可以继续使用空白电台
    assert client.get("/api/v1/me").status_code == 200
    assert client.get("/api/v1/programs").json() == []

    # 数据库中节目与资料已删除
    factory = get_session_factory()
    with factory() as db:
        from app.models.program import Program

        assert db.query(Program).filter_by(id=program_id).count() == 0
