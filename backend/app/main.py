from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.tasks import router as tasks_router
from app.config import settings
from app.db import Base, engine

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router, prefix=settings.api_prefix)

app.mount(
    "/files/audio",
    StaticFiles(directory=str(settings.audio_dir), check_dir=False),
    name="files-audio",
)
app.mount(
    "/files/subtitles",
    StaticFiles(directory=str(settings.subtitles_dir), check_dir=False),
    name="files-subtitles",
)
app.mount(
    "/files/notes",
    StaticFiles(directory=str(settings.notes_dir), check_dir=False),
    name="files-notes",
)


@app.on_event("startup")
def _startup() -> None:
    # auto-create tables in dev; switch to alembic for prod migrations.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
