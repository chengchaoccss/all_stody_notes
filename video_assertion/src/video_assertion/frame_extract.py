"""Per-scene keyframe extraction with perceptual-hash deduplication."""

from __future__ import annotations

from pathlib import Path

import cv2
import imagehash
import numpy as np
from PIL import Image

from .models import Keyframe, Scene


def _grab(cap: cv2.VideoCapture, t_sec: float) -> np.ndarray | None:
    cap.set(cv2.CAP_PROP_POS_MSEC, t_sec * 1000.0)
    ok, frame = cap.read()
    return frame if ok else None


def extract_keyframes(
    video_path: str | Path,
    scenes: list[Scene],
    out_dir: str | Path,
    samples_per_scene: int = 3,
    phash_distance: int = 6,
) -> list[Keyframe]:
    """Sample N evenly-spaced frames per scene, then drop near-duplicates.

    Two frames are considered duplicates if their pHash Hamming distance is
    <= ``phash_distance``. The first frame seen wins.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video {video_path}")

    kept: list[Keyframe] = []
    kept_hashes: list[imagehash.ImageHash] = []

    try:
        for sc in scenes:
            if sc.duration <= 0:
                continue
            # avoid hitting the exact boundary frame
            margin = min(0.05, sc.duration / 10)
            ts_list = np.linspace(
                sc.start_sec + margin,
                sc.end_sec - margin,
                samples_per_scene,
            )
            for ts in ts_list:
                frame = _grab(cap, float(ts))
                if frame is None:
                    continue
                pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                h = imagehash.phash(pil)
                if any((h - prev) <= phash_distance for prev in kept_hashes):
                    continue
                fname = f"scene{sc.index:03d}_t{ts:07.3f}.jpg"
                fpath = out_dir / fname
                cv2.imwrite(str(fpath), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                kept.append(
                    Keyframe(
                        scene_index=sc.index,
                        timestamp_sec=float(ts),
                        path=str(fpath),
                        phash=str(h),
                    )
                )
                kept_hashes.append(h)
    finally:
        cap.release()

    return kept
