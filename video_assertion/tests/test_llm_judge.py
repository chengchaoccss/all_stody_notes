import json

from video_assertion.llm_judge import judge_dynamic, judge_static
from video_assertion.models import Assertion, AssertionKind, Clip, Keyframe
from tests.conftest import StubClient


def _kf(i: int, path: str) -> Keyframe:
    return Keyframe(scene_index=i, timestamp_sec=float(i), path=path, phash=f"h{i}")


def test_judge_static_passes_when_model_says_pass(tmp_path):
    img = tmp_path / "f.jpg"
    img.write_bytes(b"\xff\xd8\xff\xd9")  # tiny valid-ish jpeg bytes
    client = StubClient(
        responder=lambda **_: json.dumps(
            {"passed": True, "confidence": 0.92, "evidence": "house visible"}
        )
    )
    a = Assertion(id="a1", text="has house", kind=AssertionKind.STATIC_PRESENCE)
    out = judge_static(client, a, [_kf(0, str(img))], max_frames=4)
    assert out.passed is True
    assert out.confidence == 0.92
    assert "house" in out.evidence
    assert client.calls[0]["image_paths"] == [str(img)]


def test_judge_static_fails_with_no_keyframes():
    client = StubClient()
    a = Assertion(id="a1", text="has house", kind=AssertionKind.STATIC_PRESENCE)
    out = judge_static(client, a, [], max_frames=4)
    assert out.passed is False
    assert client.calls == []


def test_judge_dynamic_short_circuits_on_high_confidence_pass(tmp_path):
    img1 = tmp_path / "c1.jpg"
    img1.write_bytes(b"\xff\xd8\xff\xd9")
    img2 = tmp_path / "c2.jpg"
    img2.write_bytes(b"\xff\xd8\xff\xd9")

    clips = [
        Clip(scene_index=0, start_sec=0, end_sec=1, sampled_frame_paths=[str(img1)]),
        Clip(scene_index=1, start_sec=2, end_sec=3, sampled_frame_paths=[str(img2)]),
    ]

    answers = iter([
        json.dumps({"passed": True, "confidence": 0.88, "evidence": "panda chewing"}),
        json.dumps({"passed": True, "confidence": 0.99, "evidence": "should not be reached"}),
    ])
    client = StubClient(responder=lambda **_: next(answers))

    a = Assertion(id="a2", text="panda eating bamboo", kind=AssertionKind.DYNAMIC_ACTION)
    out = judge_dynamic(client, a, clips, max_frames=4)
    assert out.passed is True
    assert "panda chewing" in out.evidence
    assert len(client.calls) == 1  # short-circuited after the first clip


def test_judge_dynamic_returns_best_when_all_low_confidence(tmp_path):
    img = tmp_path / "c.jpg"
    img.write_bytes(b"\xff\xd8\xff\xd9")

    clips = [
        Clip(scene_index=0, start_sec=0, end_sec=1, sampled_frame_paths=[str(img)]),
        Clip(scene_index=1, start_sec=2, end_sec=3, sampled_frame_paths=[str(img)]),
    ]
    answers = iter([
        json.dumps({"passed": False, "confidence": 0.3, "evidence": "no motion"}),
        json.dumps({"passed": False, "confidence": 0.5, "evidence": "ambiguous"}),
    ])
    client = StubClient(responder=lambda **_: next(answers))

    a = Assertion(id="a3", text="dog running", kind=AssertionKind.DYNAMIC_ACTION)
    out = judge_dynamic(client, a, clips, max_frames=4)
    assert out.passed is False
    assert out.confidence == 0.5
    assert len(client.calls) == 2
