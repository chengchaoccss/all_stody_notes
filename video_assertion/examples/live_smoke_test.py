"""One-shot live verification against the real Doubao Responses API.

Run this **on your own machine** (the sandbox where this project was developed
cannot reach `ark.cn-beijing.volces.com`).

What it does:
1. Pings the model with a tiny text-only prompt to confirm the endpoint works.
2. Generates a synthetic 3-scene video.
3. Runs the full pipeline against it with three representative assertions.

Usage:
    export DOUBAO_API_KEY=ark-xxxxxxxx
    export DOUBAO_MODEL_ENDPOINT=doubao-seed-2-0-pro-260215
    python examples/live_smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from tests.fixtures.synthesize import make_three_scene_video  # noqa: E402

from video_assertion import Assertion, run_pipeline  # noqa: E402
from video_assertion.config import Config  # noqa: E402
from video_assertion.doubao_client import HttpDoubaoClient  # noqa: E402
from video_assertion.report import write_html, write_json  # noqa: E402


def main() -> int:
    cfg = Config.from_env()
    print(f"→ Doubao endpoint: {cfg.base_url}/responses  model={cfg.model}")

    with HttpDoubaoClient(cfg) as client:
        print("[1/2] text-only ping")
        pong = client.respond("Reply with the single word: pong")
        print(f"      response: {pong[:80]}")

        print("[2/2] full pipeline against a synthetic 3-scene video")
        work = ROOT / "runs" / "live"
        work.mkdir(parents=True, exist_ok=True)
        video = work / "synthetic.mp4"
        if not video.exists():
            make_three_scene_video(video)

        assertions = [
            Assertion(id="no_flash", text="视频中没有闪屏现象"),
            Assertion(id="has_rect", text="画面里出现过一个白色的矩形"),
            Assertion(id="moves",    text="画面里有一个红色物体在水平方向移动"),
        ]
        report = run_pipeline(video, assertions, work, client=client, config=cfg)

        write_json(report, work / "report.json")
        write_html(report, work / "report.html")

        for r in report.results:
            flag = "PASS" if r.passed else "FAIL"
            print(f"  [{flag}] ({r.kind.value}, conf={r.confidence:.2f}) {r.text}")
            print(f"          {r.evidence}")

        print(f"\nartifacts in {work}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
