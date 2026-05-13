from __future__ import annotations

import logging
import traceback
from pathlib import Path

from app.config import settings
from app.db import SessionLocal
from app.models.task import Task, TaskStatus
from app.services import doubao_asr, doubao_llm, ffmpeg, subtitle
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)


def _set_state(task_id: str, *, status: TaskStatus | None = None, progress: int | None = None,
               error: str | None = None, **fields) -> None:
    with SessionLocal() as db:
        task = db.get(Task, task_id)
        if task is None:
            return
        if status is not None:
            task.status = status
        if progress is not None:
            task.progress = progress
        if error is not None:
            task.error = error
        for k, v in fields.items():
            setattr(task, k, v)
        db.commit()


@celery_app.task(name="pipeline.process_video", bind=True)
def process_video(self, task_id: str) -> None:
    try:
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task is None:
                log.error("task %s not found", task_id)
                return
            video_path = Path(task.video_path)
            filename = task.filename

        # 1) Audio extraction
        _set_state(task_id, status=TaskStatus.extracting_audio, progress=5)
        audio_path = settings.audio_dir / f"{task_id}.wav"
        ffmpeg.extract_audio(video_path, audio_path)
        duration = ffmpeg.probe_duration(audio_path)
        _set_state(task_id, audio_path=str(audio_path), duration_seconds=duration, progress=20)

        # 2) ASR (豆包语音大模型 录音文件识别)
        _set_state(task_id, status=TaskStatus.transcribing, progress=25)
        audio_url = f"{settings.public_file_base_url.rstrip('/')}/audio/{audio_path.name}"

        def _on_progress(_resp: dict) -> None:
            with SessionLocal() as db:
                t = db.get(Task, task_id)
                if t and t.progress < 60:
                    t.progress = min(60, t.progress + 2)
                    db.commit()

        utterances = doubao_asr.transcribe(audio_url, on_progress=_on_progress)
        srt = subtitle.utterances_to_srt(utterances)
        subtitle_path = settings.subtitles_dir / f"{task_id}.srt"
        subtitle_path.write_text(srt, encoding="utf-8")
        _set_state(task_id, subtitle_path=str(subtitle_path), progress=65)

        # 3) LLM note generation (豆包 chat)
        _set_state(task_id, status=TaskStatus.generating_notes, progress=70)
        transcript = subtitle.utterances_to_plain(utterances)
        notes_md = doubao_llm.generate_notes(transcript, title_hint=filename)
        notes_path = settings.notes_dir / f"{task_id}.md"
        notes_path.write_text(notes_md, encoding="utf-8")

        _set_state(
            task_id,
            status=TaskStatus.completed,
            progress=100,
            notes_path=str(notes_path),
        )
    except Exception as e:  # noqa: BLE001
        log.exception("pipeline failed for task %s", task_id)
        _set_state(
            task_id,
            status=TaskStatus.failed,
            error=f"{e}\n\n{traceback.format_exc()[-2000:]}",
        )
        raise
