import json

from video_assertion.assertion_router import classify_assertion
from video_assertion.models import Assertion, AssertionKind
from tests.conftest import StubClient


def _classify(text: str, responder=None) -> Assertion:
    client = StubClient(responder=responder)
    a = Assertion(id="x", text=text)
    return classify_assertion(client, a)


def test_chinese_no_flashing_routes_to_cv_rule_without_calling_llm():
    client = StubClient(responder=lambda **_: pytest_should_not_be_called())  # noqa
    out = classify_assertion(client, Assertion(id="x", text="视频中没有闪屏现象"))
    assert out.kind == AssertionKind.CV_RULE
    assert out.cv_rule == "no_flashing"
    assert client.calls == []  # fast path took it


def test_english_no_flash_routes_to_cv_rule():
    out = _classify("there should be no flashing in the video")
    assert out.kind == AssertionKind.CV_RULE
    assert out.cv_rule == "no_flashing"


def test_dynamic_hint_routes_to_dynamic():
    out = _classify("熊猫在动态吃竹子")
    assert out.kind == AssertionKind.DYNAMIC_ACTION


def test_static_assertion_falls_through_to_llm_router():
    captured = {}

    def fake(text, image_paths, json_schema):
        captured["got_schema"] = json_schema is not None
        return json.dumps({"kind": "static", "cv_rule": "", "reason": "object presence"})

    out = _classify("画面里有一栋房子", responder=fake)
    assert out.kind == AssertionKind.STATIC_PRESENCE
    assert captured["got_schema"] is True


def test_router_handles_codefence_wrapped_json():
    raw = "```json\n{\"kind\":\"static\",\"cv_rule\":\"\",\"reason\":\"ok\"}\n```"
    out = _classify("a thing exists", responder=lambda **_: raw)
    assert out.kind == AssertionKind.STATIC_PRESENCE


def pytest_should_not_be_called():
    raise AssertionError("LLM router should not be invoked when fast path matches")
