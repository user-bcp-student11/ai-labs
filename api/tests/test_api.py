import base64
import sqlite3
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from urllib3.exceptions import HTTPError

from app.main import create_app


def token(username: str = "student", role: str = "STUDENT") -> str:
    raw = f"{username}|{role}|{int(time.time()) + 3600}|WORKSHOP_SECRET_2026"
    return base64.b64encode(raw.encode()).decode()


def headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role)}"}


@pytest.mark.parametrize(
    ("method", "path", "request_kwargs"),
    [
        pytest.param("get", "/api/tasks", {}, id="list-tasks"),
        pytest.param("post", "/api/tasks", {"json": {}}, id="create-task"),
        pytest.param("get", "/api/summary", {}, id="summary"),
        pytest.param(
            "post",
            "/api/requirements",
            {"files": {"file": ("requirements.txt", b"content", "text/plain")}},
            id="upload-requirement",
        ),
        pytest.param("get", "/api/backend-health", {}, id="backend-health"),
    ],
)
def test_all_endpoints_reject_missing_authentication(
    method: str, path: str, request_kwargs: dict, tmp_path: Path
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = getattr(client, method)(path, **request_kwargs)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_lists_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all(
        set(task)
        == {"id", "title", "description", "status", "owner", "priority", "createdAt"}
        for task in response.json()
    )
    assert all(task["owner"] == "student" for task in response.json())


def test_list_tasks_with_empty_owner_uses_authenticated_identity(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks?owner=", headers=headers())

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all(task["owner"] == "student" for task in response.json())


def test_creates_task_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Add tests", "description": "Improve coverage", "status": "TODO", "priority": "HIGH"},
        )
        summary = client.get("/api/summary", headers=headers())
    assert created.status_code == 201
    assert created.json()["owner"] == "student"
    assert summary.status_code == 200
    assert summary.json() == {
        "owner": "student",
        "total": 3,
        "byStatus": {"TODO": 2, "IN_PROGRESS": 1},
        "highPriorityOpen": 2,
    }
    assert summary.json()["total"] == 3


def test_create_task_with_empty_payload_uses_all_defaults(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json={})

    payload = response.json()
    assert response.status_code == 201
    assert payload["id"] == 4
    assert payload["title"] == ""
    assert payload["description"] == ""
    assert payload["status"] == "TODO"
    assert payload["owner"] == "student"
    assert payload["priority"] == "MEDIUM"
    assert isinstance(payload["createdAt"], str)
    assert payload["createdAt"]


def test_create_task_preserves_observed_defaults(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json={"title": "Default task"})

    payload = response.json()
    assert response.status_code == 201
    assert set(payload) == {"id", "title", "description", "status", "owner", "priority", "createdAt"}
    assert payload["title"] == "Default task"
    assert payload["description"] == ""
    assert payload["status"] == "TODO"
    assert payload["owner"] == "student"
    assert payload["priority"] == "MEDIUM"
    assert payload["createdAt"]


def test_create_task_stores_quotes_as_literal_text(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Quoted ' title", "description": "Quoted ' description"},
        )

    assert response.status_code == 201
    assert response.json()["title"] == "Quoted ' title"
    assert response.json()["description"] == "Quoted ' description"


def test_create_task_rejects_non_object_payload(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json=[])

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "model_attributes_type",
                "loc": ["body"],
                "msg": "Input should be a valid dictionary or object to extract fields from",
                "input": [],
            }
        ]
    }


def test_list_tasks_rejects_other_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks?owner=trainer", headers=headers())

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to access this owner"}


def test_summary_returns_counts_for_empty_owner_dataset(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        app.state.connection.execute("DELETE FROM tasks WHERE owner=?", ("student",))
        app.state.connection.commit()
        response = client.get("/api/summary", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "owner": "student",
        "total": 0,
        "byStatus": {},
        "highPriorityOpen": 0,
    }


def test_summary_rejects_other_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/summary?owner=trainer", headers=headers())

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to access this owner"}


def test_create_task_rejects_owner_override(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Trainer task", "owner": "trainer"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to access this owner"}


def test_uploads_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"Login must be accessible", "text/plain")},
        )
    assert response.status_code == 201
    assert response.json() == {
        "owner": "student",
        "fileName": "requirements.txt",
        "storedAt": str(upload_dir / "requirements.txt"),
        "size": 24,
    }
    assert (upload_dir / "requirements.txt").exists()


def test_uploads_empty_file_without_extension(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements", b"", "application/octet-stream")},
        )

    assert response.status_code == 201
    assert response.json() == {
        "owner": "student",
        "fileName": "requirements",
        "storedAt": str(upload_dir / "requirements"),
        "size": 0,
    }
    assert (upload_dir / "requirements").read_bytes() == b""


def test_upload_requirement_without_file_returns_422(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/requirements", headers=headers())

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["body", "file"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }


def test_rejects_invalid_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_invalid_token_does_not_expose_error_detail(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_invalid_utf8_token_returns_generic_401(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    invalid_utf8_token = base64.b64encode(b"\xff").decode("ascii")
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {invalid_utf8_token}"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_backend_health_preserves_observed_response_shape(
    monkeypatch, tmp_path: Path
) -> None:
    class StubResponse:
        status = 503
        data = b'{"status":"DOWN"}'

    class StubPoolManager:
        def request(self, method: str, url: str, timeout: float) -> StubResponse:
            assert method == "GET"
            assert url == "http://auth.test/q/health"
            assert timeout == 3.0
            return StubResponse()

    monkeypatch.setattr("app.services.urllib3.PoolManager", StubPoolManager)
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://auth.test/q/health")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 503,
        "body": '{"status":"DOWN"}',
    }


def test_backend_health_does_not_expose_error_detail(monkeypatch, tmp_path: Path) -> None:
    class FailingPoolManager:
        def request(self, method: str, url: str, timeout: float) -> None:
            raise HTTPError("private backend detail")

    monkeypatch.setattr("app.services.urllib3.PoolManager", FailingPoolManager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 0,
        "body": "Backend health check failed",
    }


def test_backend_health_preserves_empty_upstream_body(monkeypatch, tmp_path: Path) -> None:
    class EmptyResponse:
        status = 200
        data = b""

    class StubPoolManager:
        def request(self, method: str, url: str, timeout: float) -> EmptyResponse:
            return EmptyResponse()

    monkeypatch.setattr("app.services.urllib3.PoolManager", StubPoolManager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {"requestedBy": "student", "status": 200, "body": ""}


@pytest.mark.parametrize(
    ("method", "path", "failure_target", "request_kwargs"),
    [
        pytest.param(
            "get",
            "/api/tasks",
            "app.repositories.TaskRepository.list_by_owner",
            {},
            id="list-tasks-database-error",
        ),
        pytest.param(
            "post",
            "/api/tasks",
            "app.repositories.TaskRepository.create",
            {"json": {}},
            id="create-task-database-error",
        ),
        pytest.param(
            "get",
            "/api/summary",
            "app.repositories.TaskRepository.summary_rows",
            {},
            id="summary-database-error",
        ),
        pytest.param(
            "post",
            "/api/requirements",
            "app.services.Path.write_bytes",
            {"files": {"file": ("requirements.txt", b"content", "text/plain")}},
            id="upload-storage-error",
        ),
        pytest.param(
            "get",
            "/api/backend-health",
            "app.services.urllib3.PoolManager",
            {},
            id="backend-unexpected-error",
        ),
    ],
)
def test_unhandled_internal_failures_return_500(
    monkeypatch,
    method: str,
    path: str,
    failure_target: str,
    request_kwargs: dict,
    tmp_path: Path,
) -> None:
    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("injected internal failure")

    monkeypatch.setattr(failure_target, fail)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = getattr(client, method)(path, headers=headers(), **request_kwargs)

    assert response.status_code == 500
