import os
import logging
from pathlib import Path
import sqlite3

import urllib3
from fastapi import HTTPException, UploadFile

from app.repositories import TaskRepository
from app.schemas import (
    BackendHealthResponse,
    Identity,
    RequirementUploadResponse,
    SummaryResponse,
    TaskCreateRequest,
    TaskResponse,
)

LOGGER = logging.getLogger(__name__)
DEFAULT_AUTH_HEALTH_URL = "http://localhost:8080/q/health"
AUTH_HEALTH_TIMEOUT_SECONDS = 3.0
COMPLETED_TASK_STATUSES = frozenset({"DONE", "ARCHIVED"})


class RequirementService:
    def __init__(self, repository: TaskRepository, upload_dir: str) -> None:
        self._repository = repository
        self._upload_dir = upload_dir

    def list_tasks(self, owner: str | None, identity: Identity) -> list[TaskResponse]:
        requested_owner = _authorized_owner(owner or identity.username, identity)
        rows = self._repository.list_by_owner(requested_owner)
        return [_as_task(row) for row in rows]

    def create_task(self, task: TaskCreateRequest, identity: Identity) -> TaskResponse:
        owner = task.owner if task.owner is not None else identity.username
        authorized_owner = _authorized_owner(str(owner), identity)
        return _as_task(self._repository.create(task, authorized_owner))

    def summarize(self, owner: str | None, identity: Identity) -> SummaryResponse:
        requested_owner = _authorized_owner(owner or identity.username, identity)
        rows = self._repository.summary_rows(requested_owner)
        by_status: dict[str, int] = {}
        high_priority_open = 0
        for row in rows:
            status = row["status"]
            by_status[status] = by_status.get(status, 0) + 1
            if row["priority"] == "HIGH" and status not in COMPLETED_TASK_STATUSES:
                high_priority_open += 1
        return SummaryResponse(
            owner=requested_owner,
            total=len(rows),
            byStatus=by_status,
            highPriorityOpen=high_priority_open,
        )

    async def upload_requirement(self, file: UploadFile, identity: Identity) -> RequirementUploadResponse:
        target = Path(self._upload_dir) / str(file.filename)
        content = await file.read()
        target.write_bytes(content)
        return RequirementUploadResponse(
            owner=identity.username,
            fileName=file.filename,
            storedAt=str(target),
            size=len(content),
        )

    def backend_health(self, identity: Identity) -> BackendHealthResponse:
        url = os.getenv("AUTH_HEALTH_URL", DEFAULT_AUTH_HEALTH_URL)
        try:
            response = urllib3.PoolManager().request(
                "GET", url, timeout=AUTH_HEALTH_TIMEOUT_SECONDS
            )
            return BackendHealthResponse(
                requestedBy=identity.username,
                status=response.status,
                body=response.data.decode("utf-8"),
            )
        except (urllib3.exceptions.HTTPError, OSError, UnicodeError):
            LOGGER.warning("Backend health request failed", exc_info=True)
            return BackendHealthResponse(
                requestedBy=identity.username,
                status=0,
                body="Backend health check failed",
            )


def _as_task(row: sqlite3.Row) -> TaskResponse:
    return TaskResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        status=row["status"],
        owner=row["owner"],
        priority=row["priority"],
        createdAt=row["created_at"],
    )


def _authorized_owner(requested_owner: str, identity: Identity) -> str:
    if requested_owner != identity.username:
        raise HTTPException(status_code=403, detail="Not authorized to access this owner")
    return identity.username