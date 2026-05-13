from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskDetail, TaskRead
from app.workers.pipeline import process_video

router = APIRouter(prefix="/tasks", tags=["tasks"])

ALLOWED_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".m4v", ".ts"}


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(file: UploadFile = File(...), db: Session = Depends(get_db)) -> TaskRead:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, detail=f"unsupported video format: {suffix}")

    task = Task(filename=file.filename or "video", video_path="")
    db.add(task)
    db.commit()
    db.refresh(task)

    dest = settings.uploads_dir / f"{task.id}{suffix}"
    size = 0
    max_bytes = settings.max_upload_mb * 1024 * 1024
    with dest.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                dest.unlink(missing_ok=True)
                db.delete(task)
                db.commit()
                raise HTTPException(413, detail="file too large")
            out.write(chunk)

    task.video_path = str(dest)
    db.commit()

    process_video.delay(task.id)
    return TaskRead.model_validate(task)


@router.get("", response_model=list[TaskRead])
def list_tasks(db: Session = Depends(get_db), limit: int = 50) -> list[TaskRead]:
    rows = db.query(Task).order_by(desc(Task.created_at)).limit(limit).all()
    return [TaskRead.model_validate(r) for r in rows]


@router.get("/{task_id}", response_model=TaskDetail)
def get_task(task_id: str, db: Session = Depends(get_db)) -> TaskDetail:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "task not found")

    detail = TaskDetail.model_validate(task)
    base = settings.public_file_base_url.rstrip("/")
    if task.subtitle_path:
        detail.subtitle_url = f"{base}/subtitles/{Path(task.subtitle_path).name}"
        try:
            detail.subtitle_srt = Path(task.subtitle_path).read_text(encoding="utf-8")
        except OSError:
            pass
    if task.notes_path:
        detail.notes_url = f"{base}/notes/{Path(task.notes_path).name}"
        try:
            detail.notes_markdown = Path(task.notes_path).read_text(encoding="utf-8")
        except OSError:
            pass
    return detail


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, db: Session = Depends(get_db)) -> None:
    task = db.get(Task, task_id)
    if not task:
        return
    for p in (task.video_path, task.audio_path, task.subtitle_path, task.notes_path):
        if p:
            Path(p).unlink(missing_ok=True)
    db.delete(task)
    db.commit()
