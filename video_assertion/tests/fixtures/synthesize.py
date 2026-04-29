"""Programmatically generated test videos.

Each helper builds a short MP4 with deterministic visual content so that the
pipeline's CV rules and scene logic can be exercised without any real footage.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


FOURCC = cv2.VideoWriter_fourcc(*"mp4v")


def _writer(path: Path, fps: int, size: tuple[int, int]) -> cv2.VideoWriter:
    path.parent.mkdir(parents=True, exist_ok=True)
    w = cv2.VideoWriter(str(path), FOURCC, fps, size)
    if not w.isOpened():
        raise RuntimeError(f"cannot open VideoWriter for {path}")
    return w


def make_three_scene_video(
    path: Path,
    fps: int = 24,
    seconds_per_scene: int = 2,
    size: tuple[int, int] = (320, 240),
) -> Path:
    """Three visually distinct scenes back-to-back.

    Scene A: blue background with a static white rectangle ("house").
    Scene B: green background with a moving red square ("panda eating").
    Scene C: solid black (so the black-screen rule has something to find).
    """
    w = _writer(path, fps, size)
    width, height = size
    total_per_scene = fps * seconds_per_scene

    # Scene A
    for _ in range(total_per_scene):
        frame = np.full((height, width, 3), (180, 80, 30), dtype=np.uint8)  # BGR blue
        cv2.rectangle(frame, (60, 90), (160, 200), (255, 255, 255), -1)
        cv2.rectangle(frame, (90, 130), (110, 160), (40, 40, 40), -1)
        w.write(frame)

    # Scene B
    for i in range(total_per_scene):
        frame = np.full((height, width, 3), (40, 160, 60), dtype=np.uint8)  # BGR green
        x = 30 + (i * 4) % (width - 90)
        cv2.rectangle(frame, (x, 90), (x + 60, 150), (40, 40, 220), -1)
        w.write(frame)

    # Scene C
    for _ in range(total_per_scene):
        w.write(np.zeros((height, width, 3), dtype=np.uint8))

    w.release()
    return path


def make_flashing_video(
    path: Path,
    fps: int = 24,
    seconds: int = 2,
    size: tuple[int, int] = (320, 240),
) -> Path:
    """Strobe between near-black and near-white every frame."""
    w = _writer(path, fps, size)
    width, height = size
    for i in range(fps * seconds):
        v = 250 if i % 2 == 0 else 5
        w.write(np.full((height, width, 3), v, dtype=np.uint8))
    w.release()
    return path


def make_calm_video(
    path: Path,
    fps: int = 24,
    seconds: int = 2,
    size: tuple[int, int] = (320, 240),
) -> Path:
    """Slowly panning gradient with no abrupt changes."""
    w = _writer(path, fps, size)
    width, height = size
    base = np.tile(np.linspace(40, 200, width, dtype=np.uint8), (height, 1))
    for i in range(fps * seconds):
        shifted = np.roll(base, i * 2, axis=1)
        frame = cv2.cvtColor(shifted, cv2.COLOR_GRAY2BGR)
        w.write(frame)
    w.release()
    return path


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[2] / "test_data"
    make_three_scene_video(out / "three_scenes.mp4")
    make_flashing_video(out / "flashing.mp4")
    make_calm_video(out / "calm.mp4")
    print(f"wrote synthetic videos under {out}")
