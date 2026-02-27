#!/usr/bin/env python3
"""
Example CI pipeline script.

Replace the placeholder steps below with real build / test logic.
The script must exit with code 0 on success and non-zero on failure.

Usage (invoked automatically by ci_tool.py):
    python scripts/run_ci.py --type daily
    python scripts/run_ci.py --type release --version 2.1.0
    python scripts/run_ci.py --type smoke   --env staging
"""

import argparse
import sys
import time


def run_daily() -> None:
    print("[CI] === Daily Pipeline ===")
    steps = [
        "Environment setup",
        "Unit tests",
        "Integration tests",
        "Collect coverage report",
    ]
    for i, step in enumerate(steps, 1):
        print(f"[CI] Step {i}/{len(steps)}: {step} ...", flush=True)
        time.sleep(0.1)  # placeholder: replace with real work
        print(f"[CI] Step {i}/{len(steps)}: {step} ... OK")


def run_release(version: str) -> None:
    print(f"[CI] === Release Pipeline  version={version} ===")
    steps = [
        "Version validation",
        "Clean build",
        "Unit + integration tests",
        "Build APK / artefact",
        "Publish artefact",
    ]
    for i, step in enumerate(steps, 1):
        print(f"[CI] Step {i}/{len(steps)}: {step} ...", flush=True)
        time.sleep(0.1)
        print(f"[CI] Step {i}/{len(steps)}: {step} ... OK")


def run_smoke(env: str) -> None:
    print(f"[CI] === Smoke Pipeline  env={env} ===")
    steps = [
        "Sanity checks",
        "Critical path tests",
        "Health checks",
    ]
    for i, step in enumerate(steps, 1):
        print(f"[CI] Step {i}/{len(steps)}: {step} ...", flush=True)
        time.sleep(0.1)
        print(f"[CI] Step {i}/{len(steps)}: {step} ... OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP CI Pipeline Runner")
    parser.add_argument(
        "--type",
        required=True,
        choices=["daily", "release", "smoke"],
        help="Pipeline type",
    )
    parser.add_argument("--version", default="latest", help="Release version tag")
    parser.add_argument("--env", default="staging", help="Target environment")
    args = parser.parse_args()

    t0 = time.monotonic()
    try:
        if args.type == "daily":
            run_daily()
        elif args.type == "release":
            run_release(args.version)
        elif args.type == "smoke":
            run_smoke(args.env)
    except Exception as exc:
        print(f"[CI] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

    elapsed = time.monotonic() - t0
    print(f"[CI] Pipeline '{args.type}' completed successfully in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
