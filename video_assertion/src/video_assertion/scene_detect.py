"""Scene segmentation via PySceneDetect.

The detector runs ContentDetector (HSV-difference based) and falls back to a
single full-video scene if no cuts are found, which is common for short clips.
"""

from __future__ import annotations

from pathlib import Path

import cv2
from scenedetect import ContentDetector, SceneManager, open_video

from .models import Scene


def _video_duration(path: str) -> float:
    cap = cv2.VideoCapture(path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        if fps <= 0 or frames <= 0:
            return 0.0
        return frames / fps
    finally:
        cap.release()


def detect_scenes(
    video_path: str | Path,
    threshold: float = 27.0,
    min_scene_len_frames: int = 12,
) -> list[Scene]:
    video_path = str(video_path)
    video = open_video(video_path)
    sm = SceneManager()
    sm.add_detector(
        ContentDetector(threshold=threshold, min_scene_len=min_scene_len_frames)
    )
    sm.detect_scenes(video=video)
    raw = sm.get_scene_list()

    if not raw:
        duration = _video_duration(video_path)
        if duration <= 0:
            return []
        return [Scene(index=0, start_sec=0.0, end_sec=duration)]

    return [
        Scene(
            index=i,
            start_sec=float(s.get_seconds()),
            end_sec=float(e.get_seconds()),
        )
        for i, (s, e) in enumerate(raw)
    ]
