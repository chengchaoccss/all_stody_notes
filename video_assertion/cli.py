"""Command-line entry point.

Usage:
    python cli.py --video path/to.mp4 --assertions path/to.json --out runs/run1
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from video_assertion import Assertion, run_pipeline
from video_assertion.report import write_html, write_json


def _load_assertions(path: Path) -> list[Assertion]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        items = raw
    else:
        items = raw.get("assertions", [])
    out: list[Assertion] = []
    for i, item in enumerate(items):
        if isinstance(item, str):
            out.append(Assertion(id=f"a{i+1}", text=item))
        else:
            out.append(
                Assertion(
                    id=str(item.get("id") or f"a{i+1}"),
                    text=str(item["text"]),
                )
            )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run the video assertion pipeline")
    p.add_argument("--video", required=True, type=Path)
    p.add_argument("--assertions", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    assertions = _load_assertions(args.assertions)
    args.out.mkdir(parents=True, exist_ok=True)

    report = run_pipeline(args.video, assertions, args.out)

    write_json(report, args.out / "report.json")
    write_html(report, args.out / "report.html")

    print(f"\n=== {len(report.results)} assertions ===")
    for r in report.results:
        flag = "PASS" if r.passed else "FAIL"
        print(f"[{flag}] ({r.kind.value}, conf={r.confidence:.2f}) {r.text}")
        print(f"        {r.evidence}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    sys.exit(main())
