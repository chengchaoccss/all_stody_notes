"""Extract a representative short clip per scene as a sequence of sampled frames.

We deliberately do NOT export an MP4 because Doubao's Responses API takes its
visual input as one or more images. Sampling N frames spanning the scene gives
the model temporal context while staying cheap.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .models import Clip, Scene


def extract_scene_clips(
    video_path: str | Path,
    scenes: list[Scene],
    out_dir: str | Path,
    frames_per_clip: int = 6,
    max_clip_seconds: float = 3.0,
) -> list[Clip]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video {video_path}")

    clips: list[Clip] = []
    try:
        for sc in scenes:
            if sc.duration <= 0:
                continue
            length = min(sc.duration, max_clip_seconds)
            start = sc.start_sec
            end = start + length
            ts_list = np.linspace(start, end, frames_per_clip)
            paths: list[str] = []
            for i, ts in enumerate(ts_list):
                cap.set(cv2.CAP_PROP_POS_MSEC, float(ts) * 1000.0)
                ok, frame = cap.read()
                if not ok:
                    continue
                p = out_dir / f"clip_scene{sc.index:03d}_f{i:02d}.jpg"
                cv2.imwrite(str(p), frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                paths.append(str(p))
            if paths:
                clips.append(
                    Clip(
                        scene_index=sc.index,
                        start_sec=float(start),
                        end_sec=float(end),
                        sampled_frame_paths=paths,
                    )
                )
    finally:
        cap.release()

    return clips
