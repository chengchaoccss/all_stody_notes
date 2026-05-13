"""
Volcengine 豆包语音大模型 — 录音文件识别 (large file async ASR).

Docs: https://www.volcengine.com/docs/6561/80816

Flow:
  1. POST /api/v1/auc/submit  -> returns task id
  2. POST /api/v1/auc/query   -> poll until status is finished
  3. Parse `utterances` (each with start_time/end_time in ms, text) into SRT.

Volcengine fetches the audio over HTTP, so the audio file must be publicly
reachable at `audio_url`. In dev we expose /files via FastAPI; in prod swap
this for an OSS / TOS bucket URL.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

import httpx

from app.config import settings


class DoubaoASRError(RuntimeError):
    pass


@dataclass
class Utterance:
    start_ms: int
    end_ms: int
    text: str


def _headers() -> dict[str, str]:
    if not settings.volc_asr_access_token or not settings.volc_asr_app_id:
        raise DoubaoASRError("VOLC_ASR_APP_ID / VOLC_ASR_ACCESS_TOKEN not configured")
    return {
        "Authorization": f"Bearer; {settings.volc_asr_access_token}",
        "Content-Type": "application/json",
    }


def submit_job(audio_url: str, *, language: str = "zh-CN") -> str:
    payload = {
        "app": {
            "appid": settings.volc_asr_app_id,
            "token": settings.volc_asr_access_token,
            "cluster": settings.volc_asr_cluster,
        },
        "user": {"uid": "video-to-notes"},
        "audio": {"format": "wav", "url": audio_url},
        "additions": {
            "with_speaker_info": "False",
            "use_itn": "True",
            "use_capitalize": "True",
            "max_lines": "0",
            "language": language,
        },
        "request": {"reqid": uuid.uuid4().hex},
    }
    resp = httpx.post(settings.volc_asr_submit_url, headers=_headers(), json=payload, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    if data.get("resp", {}).get("code") != 1000:
        raise DoubaoASRError(f"submit failed: {data}")
    return data["resp"]["id"]


def query_job(job_id: str) -> dict:
    payload = {
        "appid": settings.volc_asr_app_id,
        "token": settings.volc_asr_access_token,
        "cluster": settings.volc_asr_cluster,
        "id": job_id,
    }
    resp = httpx.post(settings.volc_asr_query_url, headers=_headers(), json=payload, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


def wait_for_result(
    job_id: str,
    *,
    poll_interval: float = 5.0,
    timeout: float = 60 * 60,
    on_progress=None,
) -> list[Utterance]:
    """Poll until ASR finishes. Returns the utterance list."""
    started = time.monotonic()
    while True:
        data = query_job(job_id)
        resp = data.get("resp", {})
        code = resp.get("code")

        # 1000 = success ; 1001 = running ; >= 2000 = failed
        if code == 1000:
            utts = resp.get("utterances") or []
            return [
                Utterance(
                    start_ms=int(u.get("start_time", 0)),
                    end_ms=int(u.get("end_time", 0)),
                    text=(u.get("text") or "").strip(),
                )
                for u in utts
                if (u.get("text") or "").strip()
            ]
        if code in (1001, 1002):
            if on_progress:
                on_progress(resp)
            if time.monotonic() - started > timeout:
                raise DoubaoASRError("ASR polling timed out")
            time.sleep(poll_interval)
            continue
        raise DoubaoASRError(f"ASR failed: {data}")


def transcribe(audio_url: str, *, language: str = "zh-CN", on_progress=None) -> list[Utterance]:
    job_id = submit_job(audio_url, language=language)
    return wait_for_result(job_id, on_progress=on_progress)
