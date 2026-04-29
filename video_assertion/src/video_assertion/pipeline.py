"""End-to-end orchestrator."""

from __future__ import annotations

import logging
from pathlib import Path

from .assertion_router import classify_assertion
from .clip_extract import extract_scene_clips
from .config import Config
from .cv_rules import CV_RULES
from .doubao_client import DoubaoClient, HttpDoubaoClient
from .frame_extract import extract_keyframes
from .llm_judge import judge_dynamic, judge_static
from .models import (
    Assertion,
    AssertionKind,
    AssertionResult,
    Report,
    Scene,
)
from .scene_detect import _video_duration, detect_scenes

logger = logging.getLogger(__name__)


def _judge_cv(assertion: Assertion, video_path: str) -> AssertionResult:
    rule_name = assertion.cv_rule
    if rule_name not in CV_RULES:
        return AssertionResult(
            assertion_id=assertion.id,
            text=assertion.text,
            kind=AssertionKind.CV_RULE,
            passed=False,
            confidence=0.0,
            evidence=f"unknown cv_rule {rule_name!r}",
        )
    passed, msg, metric = CV_RULES[rule_name](video_path)
    return AssertionResult(
        assertion_id=assertion.id,
        text=assertion.text,
        kind=AssertionKind.CV_RULE,
        passed=passed,
        confidence=0.95 if passed else 0.9,
        evidence=f"{rule_name}: {msg}",
        evidence_refs=[f"metric={metric:.2f}"],
    )


def run_pipeline(
    video_path: str | Path,
    assertions: list[Assertion],
    work_dir: str | Path,
    client: DoubaoClient | None = None,
    config: Config | None = None,
    scenes: list[Scene] | None = None,
) -> Report:
    """Run the full pipeline and return a structured Report.

    ``client`` and ``config`` are split so tests can inject a mock client
    without needing DOUBAO_API_KEY in the environment.
    """
    video_path = str(video_path)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    cfg = config or (Config.from_env() if client is None else None)
    owns_client = False
    if client is None:
        if cfg is None:
            raise RuntimeError("either client or config must be provided")
        client = HttpDoubaoClient(cfg)
        owns_client = True

    # use config defaults when present, otherwise sensible fallbacks
    max_keyframes = cfg.max_keyframes_per_call if cfg else 8
    max_clip_frames = cfg.max_clip_frames if cfg else 6

    try:
        scenes = scenes if scenes is not None else detect_scenes(video_path)
        logger.info("detected %d scene(s)", len(scenes))

        keyframes = extract_keyframes(
            video_path, scenes, work_dir / "keyframes"
        )
        clips = extract_scene_clips(
            video_path, scenes, work_dir / "clips",
            frames_per_clip=max_clip_frames,
        )

        # 1) classify each assertion
        classified: list[Assertion] = [
            classify_assertion(client, a) for a in assertions
        ]

        # 2) dispatch to the right judge
        results: list[AssertionResult] = []
        for a in classified:
            if a.kind == AssertionKind.CV_RULE:
                results.append(_judge_cv(a, video_path))
            elif a.kind == AssertionKind.STATIC_PRESENCE:
                results.append(
                    judge_static(client, a, keyframes, max_keyframes)
                )
            elif a.kind == AssertionKind.DYNAMIC_ACTION:
                results.append(
                    judge_dynamic(client, a, clips, max_clip_frames)
                )
            else:
                results.append(
                    AssertionResult(
                        assertion_id=a.id,
                        text=a.text,
                        kind=AssertionKind.STATIC_PRESENCE,
                        passed=False,
                        confidence=0.0,
                        evidence="assertion was not classified",
                    )
                )

        return Report(
            video_path=video_path,
            duration_sec=_video_duration(video_path),
            scenes=scenes,
            keyframes=keyframes,
            clips=clips,
            results=results,
        )
    finally:
        if owns_client and isinstance(client, HttpDoubaoClient):
            client.close()
