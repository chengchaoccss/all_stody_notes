"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str
    model: str
    request_timeout: float = 60.0
    max_keyframes_per_call: int = 8
    max_clip_frames: int = 6

    @classmethod
    def from_env(cls) -> "Config":
        api_key = os.environ.get("DOUBAO_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "DOUBAO_API_KEY is not set. "
                "export it before running the pipeline (see .env.example)."
            )
        return cls(
            api_key=api_key,
            base_url=os.environ.get(
                "DOUBAO_BASE_URL",
                "https://ark.cn-beijing.volces.com/api/v3",
            ).rstrip("/"),
            model=os.environ.get(
                "DOUBAO_MODEL_ENDPOINT",
                "doubao-seed-2-0-pro-260215",
            ),
            request_timeout=float(os.environ.get("DOUBAO_TIMEOUT", "60")),
        )
