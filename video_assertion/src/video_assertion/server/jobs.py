"""In-memory job store + thread-pool worker.

This is intentionally simple: one Python process, jobs live in memory, work
runs on a bounded thread pool. For a multi-instance deployment swap this
module out for Celery / RQ / arq + Redis without touching the API layer.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..models import Assertion, Report
from ..pipeline import run_pipeline
from ..report import write_html, write_json

logger = logging.getLogger(__name__)

ClientFactory = Callable[[], object]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Job(dict):
    """Plain dict with attribute helpers — keeps JSON serialisation trivial."""

    @classmethod
    def new(cls, job_id: str, n: int) -> "Job":
        return cls(
            job_id=job_id,
            status="queued",
            created_at=_utcnow(),
            started_at=None,
            finished_at=None,
            error=None,
            report=None,
            n_assertions=n,
            passed=None,
        )


class JobStore:
    """Thread-safe job registry with background execution."""

    def __init__(
        self,
        runs_dir: Path,
        client_factory: ClientFactory | None = None,
        max_workers: int = 2,
    ) -> None:
        self._runs_dir = Path(runs_dir)
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        self._client_factory = client_factory
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="va-worker"
        )

    @property
    def runs_dir(self) -> Path:
        return self._runs_dir

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def allocate_job_id(self) -> str:
        """Reserve a job_id (and its work dir) without starting work.

        The caller writes the video into ``runs_dir/<job_id>/`` and then
        calls :meth:`submit` once the upload is on disk. Splitting the steps
        avoids a race where the worker thread tries to read the video while
        the API handler is still saving it.
        """
        job_id = uuid.uuid4().hex[:12]
        (self._runs_dir / job_id).mkdir(parents=True, exist_ok=True)
        return job_id

    def submit(
        self, job_id: str, video_path: Path, assertions: list[Assertion]
    ) -> None:
        if not video_path.is_file():
            raise FileNotFoundError(video_path)
        job = Job.new(job_id, len(assertions))
        with self._lock:
            self._jobs[job_id] = job
        work_dir = self._runs_dir / job_id
        self._executor.submit(self._run, job_id, video_path, assertions, work_dir)

    # backwards-compatible single-shot API used by simpler callers/tests
    def create(self, video_path: Path, assertions: list[Assertion]) -> str:
        job_id = self.allocate_job_id()
        self.submit(job_id, video_path, assertions)
        return job_id

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return Job(job) if job is not None else None

    def list(self) -> list[Job]:
        with self._lock:
            return [Job(j) for j in self._jobs.values()]

    def _update(self, job_id: str, **patch) -> None:
        with self._lock:
            j = self._jobs.get(job_id)
            if j is not None:
                j.update(patch)

    def _work_dir(self, job_id: str) -> Path:
        return self._runs_dir / job_id

    def _run(
        self,
        job_id: str,
        video_path: Path,
        assertions: list[Assertion],
        work_dir: Path,
    ) -> None:
        self._update(job_id, status="running", started_at=_utcnow())
        try:
            client = self._client_factory() if self._client_factory else None
            report: Report = run_pipeline(
                video_path, assertions, work_dir, client=client
            )
            write_json(report, work_dir / "report.json")
            write_html(report, work_dir / "report.html")
            self._update(
                job_id,
                status="completed",
                finished_at=_utcnow(),
                report=json.loads(report.model_dump_json()),
                passed=report.passed,
            )
        except Exception as exc:  # noqa: BLE001 — we want to surface any failure
            logger.exception("job %s failed", job_id)
            self._update(
                job_id,
                status="failed",
                finished_at=_utcnow(),
                error=f"{type(exc).__name__}: {exc}",
            )

    def report_path(self, job_id: str, name: str) -> Path | None:
        """Resolve a known report artifact safely."""
        if name not in {"report.json", "report.html"}:
            return None
        p = self._work_dir(job_id) / name
        return p if p.is_file() else None

    def evidence_path(self, job_id: str, relative: str) -> Path | None:
        """Resolve an evidence image (keyframe / clip frame), with path-traversal guard."""
        base = self._work_dir(job_id).resolve()
        candidate = (base / relative).resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            return None
        return candidate if candidate.is_file() else None
