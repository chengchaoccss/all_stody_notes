from __future__ import annotations

from app.services.doubao_asr import Utterance


def _fmt_ts(ms: int) -> str:
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms_ = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms_:03d}"


def utterances_to_srt(utterances: list[Utterance]) -> str:
    lines: list[str] = []
    for idx, u in enumerate(utterances, start=1):
        lines.append(str(idx))
        lines.append(f"{_fmt_ts(u.start_ms)} --> {_fmt_ts(u.end_ms)}")
        lines.append(u.text)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def utterances_to_plain(utterances: list[Utterance]) -> str:
    """Plain transcript with light timestamp prefixes, fed into the LLM."""
    out: list[str] = []
    for u in utterances:
        mm = u.start_ms // 60_000
        ss = (u.start_ms % 60_000) // 1000
        out.append(f"[{mm:02d}:{ss:02d}] {u.text}")
    return "\n".join(out)
