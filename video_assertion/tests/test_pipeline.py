import json

from video_assertion.models import Assertion
from video_assertion.pipeline import run_pipeline
from video_assertion.report import write_html, write_json
from tests.conftest import StubClient


def _stub_response(prompt: str, **_) -> str:
    p = prompt.lower()
    # router prompts have the assertion text on the last line
    if "you are a router" in p:
        if "house" in p or "房子" in prompt:
            return json.dumps({"kind": "static", "cv_rule": "", "reason": "presence"})
        if "panda" in p or "熊猫" in prompt:
            return json.dumps({"kind": "dynamic", "cv_rule": "", "reason": "motion"})
        return json.dumps({"kind": "static", "cv_rule": "", "reason": "fallback"})
    # judge prompts
    if "video qa judge" in p:
        if "house" in prompt or "房子" in prompt:
            return json.dumps({"passed": True, "confidence": 0.9, "evidence": "white rectangle resembling a house in scene 0"})
        if "panda" in prompt or "熊猫" in prompt:
            return json.dumps({"passed": True, "confidence": 0.85, "evidence": "moving red square across frames in scene 1"})
        return json.dumps({"passed": False, "confidence": 0.4, "evidence": "unclear"})
    return json.dumps({"passed": False, "confidence": 0.0, "evidence": "unhandled"})


def test_pipeline_end_to_end_with_stub(videos, tmp_path):
    client = StubClient(responder=lambda **kw: _stub_response(kw["text"]))
    assertions = [
        Assertion(id="a1", text="视频中没有闪屏现象"),       # cv_rule -> pass (calm-ish 3-scene video)
        Assertion(id="a2", text="画面里有房子"),             # static -> pass (stub)
        Assertion(id="a3", text="熊猫在动态吃竹子"),         # dynamic -> pass (stub)
    ]
    report = run_pipeline(
        videos["three_scenes"], assertions, tmp_path / "run", client=client
    )
    assert len(report.results) == 3

    by_id = {r.assertion_id: r for r in report.results}
    assert by_id["a1"].kind.value == "cv_rule"
    assert by_id["a1"].passed is True  # the three_scenes video doesn't strobe
    assert by_id["a2"].kind.value == "static"
    assert by_id["a2"].passed is True
    assert by_id["a3"].kind.value == "dynamic"
    assert by_id["a3"].passed is True

    # cv_rule assertions never call the LLM
    cv_calls = [c for c in client.calls if "router" in c["text"].lower() or "judge" in c["text"].lower()]
    assert all("视频中没有闪屏" not in c["text"] or "judge" not in c["text"].lower() for c in cv_calls)


def test_pipeline_detects_real_flashing(videos, tmp_path):
    client = StubClient(responder=lambda **kw: _stub_response(kw["text"]))
    report = run_pipeline(
        videos["flashing"],
        [Assertion(id="a1", text="视频中没有闪屏现象")],
        tmp_path / "run_flash",
        client=client,
    )
    assert report.results[0].passed is False
    # cv_rule path used, so no LLM call needed for this assertion at all
    assert all("video qa judge" not in c["text"].lower() for c in client.calls)


def test_pipeline_writes_json_and_html_reports(videos, tmp_path):
    client = StubClient(responder=lambda **kw: _stub_response(kw["text"]))
    report = run_pipeline(
        videos["three_scenes"],
        [Assertion(id="a1", text="画面里有房子")],
        tmp_path / "run_rpt",
        client=client,
    )
    j = write_json(report, tmp_path / "report.json")
    h = write_html(report, tmp_path / "report.html")
    assert j.is_file() and h.is_file()
    payload = json.loads(j.read_text())
    assert payload["results"][0]["assertion_id"] == "a1"
    assert "<html" in h.read_text().lower()
