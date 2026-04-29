"""Pydantic data models that flow through the pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AssertionKind(str, Enum):
    CV_RULE = "cv_rule"           # solvable with pure OpenCV statistics
    STATIC_PRESENCE = "static"    # "has X" — judged on still frames
    DYNAMIC_ACTION = "dynamic"    # "X is doing Y" — judged on a short clip


class Assertion(BaseModel):
    id: str
    text: str
    kind: AssertionKind | None = None
    cv_rule: str | None = None    # populated when kind == CV_RULE


class Scene(BaseModel):
    index: int
    start_sec: float
    end_sec: float

    @property
    def duration(self) -> float:
        return self.end_sec - self.start_sec

    @property
    def midpoint(self) -> float:
        return (self.start_sec + self.end_sec) / 2


class Keyframe(BaseModel):
    scene_index: int
    timestamp_sec: float
    path: str
    phash: str


class Clip(BaseModel):
    scene_index: int
    start_sec: float
    end_sec: float
    sampled_frame_paths: list[str]


class AssertionResult(BaseModel):
    assertion_id: str
    text: str
    kind: AssertionKind
    passed: bool
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    evidence_refs: list[str] = Field(default_factory=list)


class Report(BaseModel):
    video_path: str
    duration_sec: float
    scenes: list[Scene]
    keyframes: list[Keyframe]
    clips: list[Clip]
    results: list[AssertionResult]

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)


# --- structured response schemas used when calling Doubao ---

class RouterDecision(BaseModel):
    kind: Literal["cv_rule", "static", "dynamic"]
    cv_rule: Literal["no_flashing", "no_black_screen", "no_freeze", ""] = ""
    reason: str = ""


class JudgeDecision(BaseModel):
    passed: bool
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
