"""Multimodal judging: ask Doubao whether an assertion holds given the evidence."""

from __future__ import annotations

import json
import logging

from .assertion_router import _load_json
from .doubao_client import DoubaoClient
from .models import (
    Assertion,
    AssertionKind,
    AssertionResult,
    Clip,
    JudgeDecision,
    Keyframe,
)

logger = logging.getLogger(__name__)


_JUDGE_SCHEMA = {
    "name": "judge_decision",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "passed": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "evidence": {"type": "string"},
        },
        "required": ["passed", "confidence", "evidence"],
    },
}


_STATIC_PROMPT = """You are a strict video QA judge. The user expects: "{text}".
You are given {n} keyframes sampled from a video. Each frame is one still
image; ignore the order. Decide whether the expectation HOLDS based purely on
what is visible in any of the frames.

Respond ONLY in JSON:
{{"passed": <bool>, "confidence": <0..1>, "evidence": "<short reason citing what you saw>"}}
"""


_DYNAMIC_PROMPT = """You are a strict video QA judge. The user expects: "{text}".
You are given {n} consecutive frames sampled from one short clip in
chronological order. Decide whether the described motion or action is taking
place across these frames.

Respond ONLY in JSON:
{{"passed": <bool>, "confidence": <0..1>, "evidence": "<short reason describing the motion you observed>"}}
"""


def _judge(
    client: DoubaoClient,
    prompt: str,
    image_paths: list[str],
) -> JudgeDecision:
    raw = client.respond(prompt, image_paths=image_paths, json_schema=_JUDGE_SCHEMA)
    return JudgeDecision.model_validate(_load_json(raw))


def judge_static(
    client: DoubaoClient,
    assertion: Assertion,
    keyframes: list[Keyframe],
    max_frames: int,
) -> AssertionResult:
    selected = keyframes[:max_frames]
    if not selected:
        return AssertionResult(
            assertion_id=assertion.id,
            text=assertion.text,
            kind=AssertionKind.STATIC_PRESENCE,
            passed=False,
            confidence=0.0,
            evidence="no keyframes were extracted from the video",
        )
    prompt = _STATIC_PROMPT.format(text=assertion.text, n=len(selected))
    decision = _judge(client, prompt, [k.path for k in selected])
    return AssertionResult(
        assertion_id=assertion.id,
        text=assertion.text,
        kind=AssertionKind.STATIC_PRESENCE,
        passed=decision.passed,
        confidence=decision.confidence,
        evidence=decision.evidence,
        evidence_refs=[k.path for k in selected],
    )


def judge_dynamic(
    client: DoubaoClient,
    assertion: Assertion,
    clips: list[Clip],
    max_frames: int,
) -> AssertionResult:
    """Judge a dynamic assertion against the most likely scene.

    We currently pass each clip in turn and short-circuit on the first
    high-confidence pass. For long videos with many scenes a smarter
    pre-filter would live here, but this matches the spec.
    """
    if not clips:
        return AssertionResult(
            assertion_id=assertion.id,
            text=assertion.text,
            kind=AssertionKind.DYNAMIC_ACTION,
            passed=False,
            confidence=0.0,
            evidence="no clips were extracted from the video",
        )

    best: AssertionResult | None = None
    for clip in clips:
        frames = clip.sampled_frame_paths[:max_frames]
        prompt = _DYNAMIC_PROMPT.format(text=assertion.text, n=len(frames))
        decision = _judge(client, prompt, frames)
        result = AssertionResult(
            assertion_id=assertion.id,
            text=assertion.text,
            kind=AssertionKind.DYNAMIC_ACTION,
            passed=decision.passed,
            confidence=decision.confidence,
            evidence=f"[scene {clip.scene_index}] {decision.evidence}",
            evidence_refs=frames,
        )
        if result.passed and result.confidence >= 0.7:
            return result
        if best is None or result.confidence > best.confidence:
            best = result
    assert best is not None
    return best
