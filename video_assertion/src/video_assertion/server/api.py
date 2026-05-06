"""FastAPI application exposing the video-assertion pipeline.

Endpoints:

    POST   /api/v1/jobs                  submit a video + assertions
    GET    /api/v1/jobs                  list jobs (most recent first)
    GET    /api/v1/jobs/{job_id}         job status + Report (when done)
    GET    /api/v1/jobs/{job_id}/report.html         rendered HTML report
    GET    /api/v1/jobs/{job_id}/evidence/{path}     keyframe / clip frame
    GET    /api/v1/health                liveness probe

Swagger UI is served at /docs and ReDoc at /redoc.

A static single-page frontend is mounted at / so the same process can serve
both API and UI — see ``static/index.html``.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Path as PathParam,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..models import Assertion
from .jobs import JobStore
from .schemas import (
    HealthResponse,
    JobDetail,
    JobSummary,
    JobsList,
    SubmitResponse,
)

logger = logging.getLogger(__name__)


API_DESCRIPTION = """
**Video Assertion API** — submit a video plus a list of natural-language
expectations and receive a structured pass/fail verdict per assertion.

The pipeline:

1. Splits the video into scenes with PySceneDetect (no ML model).
2. Extracts keyframes per scene and dedups them by perceptual hash.
3. Routes each assertion to the cheapest tool that can answer it:
   * pure OpenCV statistics for *no flashing / no black screen / no freeze*
   * Doubao multimodal model + keyframes for static presence
   * Doubao multimodal model + sampled clip frames for dynamic actions

The model is Volcengine **Doubao** — set `DOUBAO_API_KEY` and
`DOUBAO_MODEL_ENDPOINT` in the server's environment.

Typical usage:

```
POST /api/v1/jobs   (multipart: file=@video.mp4, assertions=["..."])
   ↓
{"job_id": "3f1c8e9a4b2d", "status": "queued"}

GET /api/v1/jobs/3f1c8e9a4b2d
   ↓ (after a few seconds)
{"job_id": "...", "status": "completed", "report": {...}, ...}
```
"""


def create_app(
    runs_dir: Path | None = None,
    job_store: JobStore | None = None,
) -> FastAPI:
    runs_dir = Path(runs_dir or os.environ.get("VA_RUNS_DIR", "runs"))
    store = job_store or JobStore(runs_dir=runs_dir)

    app = FastAPI(
        title="Video Assertion API",
        version="0.1.0",
        description=API_DESCRIPTION,
        contact={
            "name": "video-assertion",
            "url": "https://github.com/chengchaoccss/all_stody_notes",
        },
        license_info={"name": "MIT"},
        openapi_tags=[
            {"name": "jobs", "description": "Submit and inspect assertion jobs"},
            {"name": "artifacts", "description": "Download generated reports and evidence"},
            {"name": "system", "description": "Health and metadata"},
        ],
    )
    app.state.job_store = store

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_store() -> JobStore:
        return app.state.job_store  # type: ignore[no-any-return]

    # --------------------------------------------------------------- jobs
    @app.post(
        "/api/v1/jobs",
        response_model=SubmitResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["jobs"],
        summary="Submit a video and a list of assertions",
        description=(
            "Multipart/form-data with two fields:\n\n"
            "* **file** — the video file (mp4 / mov / mkv ...)\n"
            "* **assertions** — JSON: either an array of strings or "
            "an array of `{id, text}` objects, or `{\"assertions\": [...]}`."
        ),
        responses={
            202: {"description": "Job accepted; poll GET /api/v1/jobs/{job_id}"},
            400: {"description": "Invalid assertions JSON or empty file"},
        },
    )
    async def submit_job(
        file: UploadFile = File(..., description="Video file"),
        assertions: str = Form(
            ...,
            description=(
                'JSON array of strings or `{id,text}` objects. '
                'Example: `["视频中没有闪屏现象","画面里有房子"]`'
            ),
            examples=[
                '["视频中没有闪屏现象","画面里有房子","熊猫在动态吃竹子"]'
            ],
        ),
        store: JobStore = Depends(get_store),
    ) -> SubmitResponse:
        items = _parse_assertions(assertions)
        if not items:
            raise HTTPException(400, "no assertions parsed from request")

        job_id = store.allocate_job_id()
        suffix = Path(file.filename or "input.mp4").suffix or ".mp4"
        video_path = store.runs_dir / job_id / f"input{suffix}"
        try:
            with video_path.open("wb") as out:
                shutil.copyfileobj(file.file, out)
        finally:
            await file.close()

        if video_path.stat().st_size == 0:
            shutil.rmtree(store.runs_dir / job_id, ignore_errors=True)
            raise HTTPException(400, "uploaded video is empty")

        store.submit(job_id, video_path, items)
        return SubmitResponse(job_id=job_id, status="queued")

    @app.get(
        "/api/v1/jobs",
        response_model=JobsList,
        tags=["jobs"],
        summary="List all jobs",
    )
    def list_jobs(store: JobStore = Depends(get_store)) -> JobsList:
        items = [
            JobSummary(
                job_id=j["job_id"],
                status=j["status"],
                created_at=j["created_at"],
                started_at=j.get("started_at"),
                finished_at=j.get("finished_at"),
                n_assertions=j.get("n_assertions", 0),
                passed=j.get("passed"),
            )
            for j in sorted(store.list(), key=lambda x: x["created_at"], reverse=True)
        ]
        return JobsList(items=items, total=len(items))

    @app.get(
        "/api/v1/jobs/{job_id}",
        response_model=JobDetail,
        tags=["jobs"],
        summary="Fetch a single job",
        responses={404: {"description": "Job not found"}},
    )
    def get_job(
        job_id: str = PathParam(..., examples=["3f1c8e9a4b2d"]),
        store: JobStore = Depends(get_store),
    ) -> JobDetail:
        job = store.get(job_id)
        if job is None:
            raise HTTPException(404, f"job {job_id} not found")
        report_url = (
            f"/api/v1/jobs/{job_id}/report.html"
            if job["status"] == "completed"
            else None
        )
        return JobDetail(
            job_id=job["job_id"],
            status=job["status"],
            created_at=job["created_at"],
            started_at=job.get("started_at"),
            finished_at=job.get("finished_at"),
            error=job.get("error"),
            report=job.get("report"),
            report_html_url=report_url,
        )

    # ---------------------------------------------------------- artifacts
    @app.get(
        "/api/v1/jobs/{job_id}/report.html",
        response_class=HTMLResponse,
        tags=["artifacts"],
        summary="Rendered HTML report",
        responses={
            200: {"content": {"text/html": {}}, "description": "HTML report"},
            404: {"description": "Job not found or report not yet ready"},
        },
    )
    def get_report_html(
        job_id: str, store: JobStore = Depends(get_store)
    ) -> HTMLResponse:
        path = store.report_path(job_id, "report.html")
        if path is None:
            raise HTTPException(404, "report not ready")
        return HTMLResponse(path.read_text(encoding="utf-8"))

    @app.get(
        "/api/v1/jobs/{job_id}/report.json",
        tags=["artifacts"],
        summary="Structured JSON report",
        responses={404: {"description": "Job not found or report not yet ready"}},
    )
    def get_report_json(
        job_id: str, store: JobStore = Depends(get_store)
    ) -> JSONResponse:
        path = store.report_path(job_id, "report.json")
        if path is None:
            raise HTTPException(404, "report not ready")
        return JSONResponse(content=json.loads(path.read_text(encoding="utf-8")))

    @app.get(
        "/api/v1/jobs/{job_id}/evidence/{file_path:path}",
        tags=["artifacts"],
        summary="Fetch a single evidence image",
        responses={
            200: {"content": {"image/jpeg": {}}},
            404: {"description": "Job or file not found"},
        },
    )
    def get_evidence(
        job_id: str,
        file_path: str,
        store: JobStore = Depends(get_store),
    ) -> FileResponse:
        path = store.evidence_path(job_id, file_path)
        if path is None:
            raise HTTPException(404, "evidence not found")
        return FileResponse(str(path))

    # ------------------------------------------------------------ system
    @app.get(
        "/api/v1/health",
        response_model=HealthResponse,
        tags=["system"],
        summary="Liveness probe",
    )
    def health() -> HealthResponse:
        return HealthResponse()

    # --------------------------------------------------------- frontend
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount(
            "/", StaticFiles(directory=str(static_dir), html=True), name="frontend"
        )

    return app


def _parse_assertions(raw: str) -> list[Assertion]:
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"assertions field is not valid JSON: {exc}")

    if isinstance(data, dict) and "assertions" in data:
        data = data["assertions"]
    if not isinstance(data, list):
        raise HTTPException(400, "assertions must be a JSON array")

    out: list[Assertion] = []
    for i, item in enumerate(data):
        if isinstance(item, str):
            text = item.strip()
            if not text:
                continue
            out.append(Assertion(id=f"a{i+1}", text=text))
        elif isinstance(item, dict) and "text" in item:
            out.append(
                Assertion(
                    id=str(item.get("id") or f"a{i+1}"),
                    text=str(item["text"]),
                )
            )
    return out


# default app instance — used by uvicorn `video_assertion.server.api:app`
app = create_app()


def run() -> None:
    """Console-script entry point: ``video-assertion-server``."""
    import uvicorn

    host = os.environ.get("VA_HOST", "0.0.0.0")
    port = int(os.environ.get("VA_PORT", "8000"))
    uvicorn.run(
        "video_assertion.server.api:app",
        host=host,
        port=port,
        log_level=os.environ.get("VA_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    run()
