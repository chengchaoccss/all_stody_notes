from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.task import TaskStatus


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    status: TaskStatus
    progress: int
    error: str | None
    duration_seconds: float | None
    created_at: datetime
    updated_at: datetime


class TaskDetail(TaskRead):
    subtitle_url: str | None = None
    notes_url: str | None = None
    notes_markdown: str | None = None
    subtitle_srt: str | None = None
