"""Request / response schemas for the HTTP API.

These are kept separate from ``video_assertion.models`` so the wire format can
evolve independently of the internal pipeline data model.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..models import Report


JobStatus = Literal["queued", "running", "completed", "failed"]


class SubmitResponse(BaseModel):
    """Returned right after a job is accepted."""

    job_id: str = Field(..., description="Opaque ID used to poll job status",
                        examples=["3f1c8e9a4b2d"])
    status: JobStatus = Field(..., description="Initial job status",
                              examples=["queued"])


class JobSummary(BaseModel):
    """Compact view used in list endpoints."""

    job_id: str
    status: JobStatus
    created_at: str = Field(..., description="ISO-8601 UTC timestamp")
    started_at: str | None = None
    finished_at: str | None = None
    n_assertions: int = Field(..., description="Total number of assertions in the job")
    passed: bool | None = Field(
        None, description="True if all assertions passed; null until completed"
    )


class JobDetail(BaseModel):
    """Full job state including the structured Report once available."""

    job_id: str
    status: JobStatus
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = Field(
        None, description="Populated only when status == 'failed'"
    )
    report: Report | None = Field(
        None, description="Populated only when status == 'completed'"
    )
    report_html_url: str | None = Field(
        None, description="Convenience URL to the rendered HTML report"
    )


class JobsList(BaseModel):
    items: list[JobSummary]
    total: int


class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "video-assertion"
    version: str = "0.1.0"
