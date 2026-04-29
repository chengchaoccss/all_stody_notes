"""Standalone demo:
- generates a synthetic 3-scene video (no network needed)
- runs the pipeline against either a stubbed Doubao client (DEMO_STUB=1)
  or the real Doubao API (default; needs DOUBAO_API_KEY in env)
- writes JSON + HTML reports under runs/

Run:
    DEMO_STUB=1 python examples/run_demo.py     # offline, deterministic
    python examples/run_demo.py                  # live Doubao
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from tests.fixtures.synthesize import make_three_scene_video  # noqa: E402

from video_assertion import Assertion, run_pipeline  # noqa: E402
from video_assertion.report import write_html, write_json  # noqa: E402


def _stub_responder(text, image_paths, json_schema):
    p = text.lower()
    if "you are a router" in p:
        if "房子" in text or "house" in p:
            return json.dumps({"kind": "static", "cv_rule": "", "reason": "presence"})
        if "熊猫" in text or "panda" in p:
            return json.dumps({"kind": "dynamic", "cv_rule": "", "reason": "motion"})
        return json.dumps({"kind": "static", "cv_rule": "", "reason": "fallback"})
    if "video qa judge" in p:
        if "房子" in text or "house" in p:
            return json.dumps({"passed": True, "confidence": 0.9, "evidence": "white rectangle resembling a house"})
        if "熊猫" in text or "panda" in p:
            return json.dumps({"passed": True, "confidence": 0.85, "evidence": "moving object across frames"})
        return json.dumps({"passed": False, "confidence": 0.4, "evidence": "unclear"})
    return json.dumps({"passed": False, "confidence": 0.0, "evidence": "unhandled"})


class _StubClient:
    def __init__(self, fn):
        self._fn = fn

    def respond(self, text, image_paths=None, json_schema=None):
        return self._fn(text, image_paths or [], json_schema)


def main() -> int:
    work = ROOT / "runs" / "demo"
    work.mkdir(parents=True, exist_ok=True)
    video = work / "synthetic.mp4"
    if not video.exists():
        make_three_scene_video(video)

    assertions = [
        Assertion(id="no_flash", text="视频中没有闪屏现象"),
        Assertion(id="no_black", text="视频中没有黑屏"),
        Assertion(id="has_house", text="画面里有房子"),
        Assertion(id="panda_eat", text="熊猫在动态吃竹子"),
    ]

    if os.environ.get("DEMO_STUB") == "1":
        client = _StubClient(_stub_responder)
        report = run_pipeline(video, assertions, work, client=client)
    else:
        report = run_pipeline(video, assertions, work)

    write_json(report, work / "report.json")
    write_html(report, work / "report.html")

    print(f"\nReport written to {work / 'report.html'}")
    for r in report.results:
        flag = "PASS" if r.passed else "FAIL"
        print(f"[{flag}] ({r.kind.value}, conf={r.confidence:.2f}) {r.text}")
        print(f"        {r.evidence}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
