from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.repositories import TaskRepository, connect_database
from app.routes import create_api_router
from app.services import RequirementService


def create_app(db_path: str | None = None, upload_dir: str | None = None) -> FastAPI:
    selected_db = db_path or os.getenv("WORKSHOP_DB_PATH", "./data/workshop.db")
    selected_uploads = upload_dir or os.getenv("WORKSHOP_UPLOAD_DIR", "./uploads")
    Path(selected_uploads).mkdir(parents=True, exist_ok=True)
    connection = connect_database(selected_db)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            connection.close()

    app = FastAPI(title="Workshop Requirements API", version="0.1.0", lifespan=lifespan)
    app.state.connection = connection
    app.state.upload_dir = selected_uploads
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    repository = TaskRepository(connection)
    service = RequirementService(repository, selected_uploads)
    app.include_router(create_api_router(service))
    return app


app = create_app()
