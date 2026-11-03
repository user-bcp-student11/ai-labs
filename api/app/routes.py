from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.schemas import (
    BackendHealthResponse,
    Identity,
    RequirementUploadResponse,
    SummaryResponse,
    TaskCreateRequest,
    TaskResponse,
)
from app.security import legacy_identity
from app.services import RequirementService


def create_api_router(service: RequirementService) -> APIRouter:
    router = APIRouter()

    @router.get("/api/tasks", response_model=list[TaskResponse])
    def list_tasks(
        owner: str | None = Query(default=None),
        identity: Identity = Depends(legacy_identity),
    ) -> list[TaskResponse]:
        return service.list_tasks(owner, identity)

    @router.post("/api/tasks", status_code=201, response_model=TaskResponse)
    def create_task(
        payload: TaskCreateRequest,
        identity: Identity = Depends(legacy_identity),
    ) -> TaskResponse:
        return service.create_task(payload, identity)

    @router.get("/api/summary", response_model=SummaryResponse)
    def summary(
        owner: str | None = Query(default=None),
        identity: Identity = Depends(legacy_identity),
    ) -> SummaryResponse:
        return service.summarize(owner, identity)

    @router.post("/api/requirements", status_code=201, response_model=RequirementUploadResponse)
    async def upload_requirement(
        file: UploadFile = File(...),
        identity: Identity = Depends(legacy_identity),
    ) -> RequirementUploadResponse:
        return await service.upload_requirement(file, identity)

    @router.get("/api/backend-health", response_model=BackendHealthResponse)
    def backend_health(identity: Identity = Depends(legacy_identity)) -> BackendHealthResponse:
        return service.backend_health(identity)

    return router