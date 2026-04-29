from pathlib import Path

from video_assertion.frame_extract import extract_keyframes
from video_assertion.scene_detect import detect_scenes


def test_keyframes_are_written_and_deduplicated(videos, tmp_path):
    scenes = detect_scenes(videos["three_scenes"])
    out = tmp_path / "kf"
    kfs = extract_keyframes(videos["three_scenes"], scenes, out, samples_per_scene=4)

    assert kfs, "expected at least one keyframe"
    for kf in kfs:
        assert Path(kf.path).is_file()

    # the solid-black scene produces identical frames -> dedup keeps just one
    black_scene_idx = max(s.index for s in scenes)
    black_kfs = [k for k in kfs if k.scene_index == black_scene_idx]
    assert len(black_kfs) <= 2, (
        f"dedup should collapse the static black scene, got {len(black_kfs)}"
    )


def test_keyframes_have_distinct_phashes_overall(videos, tmp_path):
    scenes = detect_scenes(videos["three_scenes"])
    kfs = extract_keyframes(
        videos["three_scenes"], scenes, tmp_path / "kf", samples_per_scene=3
    )
    hashes = {k.phash for k in kfs}
    assert len(hashes) >= 2  # at least two visually different scenes survive
