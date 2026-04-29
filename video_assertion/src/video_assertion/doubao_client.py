"""Thin client for Volcengine Ark (Doubao) Responses API.

We talk to ``POST {base_url}/responses`` directly via httpx so the request
shape matches Volcengine's documented format exactly. The response is parsed
into a single ``output_text`` string for downstream consumers.

The client is split into a plain function plus a callable Protocol so tests
can swap in a stub without monkeypatching the network.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any, Protocol

import httpx

from .config import Config

logger = logging.getLogger(__name__)


class DoubaoClient(Protocol):
    def respond(
        self,
        text: str,
        image_paths: list[str] | None = None,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        ...


def _encode_image_data_url(path: str) -> str:
    p = Path(path)
    suffix = p.suffix.lower().lstrip(".") or "jpeg"
    if suffix == "jpg":
        suffix = "jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:image/{suffix};base64,{b64}"


def _extract_text(payload: dict[str, Any]) -> str:
    """Flatten any reasonable shape Volcengine might return."""
    if "output_text" in payload and isinstance(payload["output_text"], str):
        return payload["output_text"]
    pieces: list[str] = []
    for item in payload.get("output", []) or []:
        for c in item.get("content", []) or []:
            t = c.get("text") or (c.get("text_output") or {}).get("value")
            if t:
                pieces.append(t)
    if pieces:
        return "\n".join(pieces)
    # OpenAI-style chat completions fallback
    choices = payload.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        if isinstance(msg.get("content"), str):
            return msg["content"]
    return ""


class HttpDoubaoClient:
    """Real client. One instance is shared across the pipeline."""

    def __init__(self, config: Config, http: httpx.Client | None = None) -> None:
        self._cfg = config
        self._http = http or httpx.Client(timeout=config.request_timeout)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "HttpDoubaoClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def respond(
        self,
        text: str,
        image_paths: list[str] | None = None,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        content: list[dict[str, Any]] = [{"type": "input_text", "text": text}]
        for p in image_paths or []:
            content.append(
                {"type": "input_image", "image_url": _encode_image_data_url(p)}
            )

        body: dict[str, Any] = {
            "model": self._cfg.model,
            "input": [{"role": "user", "content": content}],
        }
        if json_schema is not None:
            body["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": json_schema.get("name", "response"),
                    "schema": json_schema["schema"],
                    "strict": True,
                }
            }

        url = f"{self._cfg.base_url}/responses"
        logger.debug("POST %s (images=%d)", url, len(image_paths or []))
        resp = self._http.post(
            url,
            headers={
                "Authorization": f"Bearer {self._cfg.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Doubao API error {resp.status_code}: {resp.text[:500]}"
            )
        payload = resp.json()
        out = _extract_text(payload)
        if not out:
            raise RuntimeError(
                f"Doubao returned no text. Raw payload: {json.dumps(payload)[:500]}"
            )
        return out
