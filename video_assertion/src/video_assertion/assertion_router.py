"""Classify each text assertion into ``cv_rule`` / ``static`` / ``dynamic``.

We try a cheap regex-based fast path first (it covers the obvious Chinese and
English phrasings) and fall back to a Doubao text call for anything ambiguous.
"""

from __future__ import annotations

import json
import re

from .doubao_client import DoubaoClient
from .models import Assertion, AssertionKind, RouterDecision

_FAST_RULES = [
    (re.compile(r"(无|不|没有|没).*?(闪屏|频闪|strob|flash)", re.I), "no_flashing"),
    (re.compile(r"(no|without).{0,15}(flash|strob)", re.I), "no_flashing"),
    (re.compile(r"(无|不|没有|没).*?(黑屏|纯黑|black\s*screen)", re.I), "no_black_screen"),
    (re.compile(r"(no|without).{0,15}black\s*screen", re.I), "no_black_screen"),
    (re.compile(r"(无|不|没有|没).*?(卡顿|卡死|冻结|freeze)", re.I), "no_freeze"),
    (re.compile(r"(no|without).{0,15}(freeze|stutter)", re.I), "no_freeze"),
]

_DYNAMIC_HINTS = [
    re.compile(r"(在|正在)\s*\S+(动|跑|走|跳|吃|喝|挥|转|旋|飞|游|打|做)"),
    re.compile(r"动态|运动|移动|moving|running|walking|eating|playing", re.I),
]


def _fast_classify(text: str) -> RouterDecision | None:
    for pattern, rule in _FAST_RULES:
        if pattern.search(text):
            return RouterDecision(kind="cv_rule", cv_rule=rule, reason="regex match")
    for pattern in _DYNAMIC_HINTS:
        if pattern.search(text):
            return RouterDecision(kind="dynamic", reason="dynamic verb hint")
    return None


_PROMPT = """You are a router for video QA assertions. Classify the user assertion into ONE of:
- "cv_rule": purely about pixel artefacts (no flashing, no black screen, no freeze).
  Set "cv_rule" to one of: "no_flashing" | "no_black_screen" | "no_freeze".
- "static": presence/appearance of an object or attribute that is visible in a single frame ("there is a house").
- "dynamic": a movement or action that needs multiple frames ("the panda is eating bamboo").
Reply ONLY with JSON: {"kind": "...", "cv_rule": "...", "reason": "..."} (cv_rule is "" unless kind is cv_rule).

Assertion: %s
"""

_SCHEMA = {
    "name": "router_decision",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "kind": {"type": "string", "enum": ["cv_rule", "static", "dynamic"]},
            "cv_rule": {
                "type": "string",
                "enum": ["no_flashing", "no_black_screen", "no_freeze", ""],
            },
            "reason": {"type": "string"},
        },
        "required": ["kind", "cv_rule", "reason"],
    },
}


def classify_assertion(client: DoubaoClient, assertion: Assertion) -> Assertion:
    if assertion.kind is not None:
        return assertion

    fast = _fast_classify(assertion.text)
    if fast is not None:
        return assertion.model_copy(
            update={
                "kind": AssertionKind(fast.kind),
                "cv_rule": fast.cv_rule or None,
            }
        )

    raw = client.respond(_PROMPT % assertion.text, json_schema=_SCHEMA)
    decision = RouterDecision.model_validate(_load_json(raw))
    return assertion.model_copy(
        update={
            "kind": AssertionKind(decision.kind),
            "cv_rule": decision.cv_rule or None,
        }
    )


def _load_json(raw: str) -> dict:
    raw = raw.strip()
    # tolerate code-fence wrapping
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]
    return json.loads(raw)
