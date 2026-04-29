"""Shared pytest fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tests.fixtures.synthesize import (  # noqa: E402
    make_calm_video,
    make_flashing_video,
    make_three_scene_video,
)


@pytest.fixture(scope="session")
def videos(tmp_path_factory) -> dict[str, Path]:
    out = tmp_path_factory.mktemp("videos")
    return {
        "three_scenes": make_three_scene_video(out / "three_scenes.mp4"),
        "flashing": make_flashing_video(out / "flashing.mp4"),
        "calm": make_calm_video(out / "calm.mp4"),
    }


class StubClient:
    """Deterministic Doubao stand-in for tests.

    ``responder`` is called with the prompt + image_paths and must return the
    string the real API would have returned (typically a JSON blob).
    """

    def __init__(self, responder=None) -> None:
        self.calls: list[dict] = []
        self._responder = responder or (lambda **_: '{"passed": true, "confidence": 0.9, "evidence": "stub"}')

    def respond(self, text, image_paths=None, json_schema=None):
        record = {
            "text": text,
            "image_paths": list(image_paths or []),
            "json_schema": json_schema,
        }
        self.calls.append(record)
        out = self._responder(**record)
        if not isinstance(out, str):
            return json.dumps(out)
        return out


@pytest.fixture()
def stub_client():
    return StubClient()
