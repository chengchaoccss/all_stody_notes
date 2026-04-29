from video_assertion.scene_detect import _video_duration, detect_scenes


def test_three_scene_video_yields_at_least_two_scenes(videos):
    scenes = detect_scenes(videos["three_scenes"])
    assert len(scenes) >= 2
    # scenes are continuous and non-overlapping
    for prev, curr in zip(scenes, scenes[1:]):
        assert curr.start_sec >= prev.end_sec - 0.05
    # cover most of the video
    total = sum(s.duration for s in scenes)
    assert total > 0.5 * _video_duration(videos["three_scenes"])


def test_calm_video_returns_at_least_one_scene(videos):
    # ContentDetector finds no cut -> fallback to single full-length scene
    scenes = detect_scenes(videos["calm"])
    assert len(scenes) >= 1
    assert scenes[0].start_sec == 0.0
