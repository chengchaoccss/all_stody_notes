from video_assertion.cv_rules import (
    check_no_black_screen,
    check_no_flashing,
    check_no_freeze,
)


def test_flashing_video_fails_no_flashing(videos):
    passed, msg, metric = check_no_flashing(videos["flashing"])
    assert passed is False, msg
    assert metric > 0


def test_calm_video_passes_no_flashing(videos):
    passed, _, _ = check_no_flashing(videos["calm"])
    assert passed is True


def test_three_scene_video_has_black_streak(videos):
    # third scene is solid black for ~2s, threshold is 0.5s
    passed, msg, metric = check_no_black_screen(videos["three_scenes"])
    assert passed is False, msg
    assert metric >= 0.5


def test_calm_video_has_no_black_streak(videos):
    passed, _, _ = check_no_black_screen(videos["calm"])
    assert passed is True


def test_calm_video_is_not_a_freeze(videos):
    # gradient pans every frame -> no freeze
    passed, _, _ = check_no_freeze(videos["calm"])
    assert passed is True


def test_solid_black_section_counts_as_freeze(videos):
    # the black tail of three_scenes is identical frames -> freeze rule fires
    passed, msg, metric = check_no_freeze(videos["three_scenes"])
    assert passed is False, msg
    assert metric >= 1.0
