"""Rule-based visual checks that do not need any ML model.

Each rule returns a tuple ``(passed, evidence_string, metric_value)`` so the
report can show a number alongside the verdict.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def _iter_luma(video_path: str) -> tuple[float, list[float]]:
    """Yield mean luminance per frame plus the source FPS."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    luma: list[float] = []
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            luma.append(float(gray.mean()))
    finally:
        cap.release()
    return fps, luma


def check_no_flashing(
    video_path: str | Path,
    window_sec: float = 1.0,
    delta_threshold: float = 60.0,
    flips_threshold: int = 4,
) -> tuple[bool, str, float]:
    """Detect flashing/strobing.

    Sliding window of ``window_sec``: count how often the per-frame luminance
    swings by more than ``delta_threshold`` between consecutive frames. If any
    window has at least ``flips_threshold`` such swings, we flag it.
    """
    fps, luma = _iter_luma(str(video_path))
    if len(luma) < 2:
        return True, "video too short to analyse, defaulting to pass", 0.0

    diffs = np.abs(np.diff(np.asarray(luma)))
    flips = (diffs >= delta_threshold).astype(np.int32)
    win = max(1, int(round(window_sec * fps)))
    csum = np.convolve(flips, np.ones(win, dtype=np.int32), mode="valid")
    peak = int(csum.max()) if csum.size else 0

    passed = peak < flips_threshold
    msg = (
        f"max luminance swings >= {delta_threshold} within {window_sec:.1f}s "
        f"window: {peak} (threshold {flips_threshold})"
    )
    return passed, msg, float(peak)


def check_no_black_screen(
    video_path: str | Path,
    luma_threshold: float = 8.0,
    min_streak_sec: float = 0.5,
) -> tuple[bool, str, float]:
    """Fail if the frame mean luminance stays below ``luma_threshold`` for
    longer than ``min_streak_sec`` seconds in a row."""
    fps, luma = _iter_luma(str(video_path))
    if not luma:
        return True, "empty video", 0.0

    streak = 0
    longest = 0
    for v in luma:
        streak = streak + 1 if v < luma_threshold else 0
        longest = max(longest, streak)

    longest_sec = longest / fps
    passed = longest_sec < min_streak_sec
    msg = (
        f"longest dark streak {longest_sec:.2f}s "
        f"(threshold {min_streak_sec:.2f}s, luma<{luma_threshold})"
    )
    return passed, msg, float(longest_sec)


def check_no_freeze(
    video_path: str | Path,
    diff_threshold: float = 0.5,
    min_streak_sec: float = 1.0,
    sample_step: int = 1,
) -> tuple[bool, str, float]:
    """Fail if consecutive frames are nearly identical for too long
    (rendering hang / playback freeze)."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0

    prev: np.ndarray | None = None
    longest = 0
    streak = 0
    idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % sample_step != 0:
                idx += 1
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev is not None:
                diff = float(np.abs(gray.astype(np.int16) - prev.astype(np.int16)).mean())
                if diff < diff_threshold:
                    streak += 1
                    longest = max(longest, streak)
                else:
                    streak = 0
            prev = gray
            idx += 1
    finally:
        cap.release()

    longest_sec = longest * sample_step / fps
    passed = longest_sec < min_streak_sec
    msg = (
        f"longest near-static streak {longest_sec:.2f}s "
        f"(threshold {min_streak_sec:.2f}s, frame-mean-diff<{diff_threshold})"
    )
    return passed, msg, float(longest_sec)


CV_RULES = {
    "no_flashing": check_no_flashing,
    "no_black_screen": check_no_black_screen,
    "no_freeze": check_no_freeze,
}
