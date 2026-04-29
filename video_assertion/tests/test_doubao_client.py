"""Test the HTTP wire format of HttpDoubaoClient using a mocked transport."""

import base64
import json
from pathlib import Path

import httpx

from video_assertion.config import Config
from video_assertion.doubao_client import HttpDoubaoClient


def _make_client(handler):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    cfg = Config(
        api_key="ark-test",
        base_url="https://example.test/api/v3",
        model="m1",
    )
    return HttpDoubaoClient(cfg, http=http), http


def test_request_shape_and_response_parsing(tmp_path: Path):
    img = tmp_path / "x.jpg"
    img.write_bytes(b"\xff\xd8jpeg\xff\xd9")

    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["auth"] = req.headers.get("authorization")
        captured["body"] = json.loads(req.content)
        return httpx.Response(
            200,
            json={
                "output": [
                    {"content": [{"type": "output_text", "text": "hello world"}]}
                ]
            },
        )

    client, http = _make_client(handler)
    try:
        out = client.respond("hi", image_paths=[str(img)])
    finally:
        http.close()

    assert out == "hello world"
    assert captured["url"].endswith("/responses")
    assert captured["auth"] == "Bearer ark-test"
    body = captured["body"]
    assert body["model"] == "m1"
    msg = body["input"][0]
    assert msg["role"] == "user"
    parts = msg["content"]
    assert parts[0] == {"type": "input_text", "text": "hi"}
    assert parts[1]["type"] == "input_image"
    assert parts[1]["image_url"].startswith("data:image/jpeg;base64,")
    expected_b64 = base64.b64encode(img.read_bytes()).decode("ascii")
    assert expected_b64 in parts[1]["image_url"]


def test_respond_includes_json_schema_when_requested():
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(req.content)
        return httpx.Response(200, json={"output_text": "{}"})

    client, http = _make_client(handler)
    try:
        client.respond(
            "x",
            json_schema={
                "name": "schema_a",
                "schema": {"type": "object", "properties": {"a": {"type": "integer"}}},
            },
        )
    finally:
        http.close()

    fmt = captured["body"]["text"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["name"] == "schema_a"
    assert fmt["strict"] is True


def test_error_response_raises():
    def handler(req):
        return httpx.Response(401, text="Unauthorized")

    client, http = _make_client(handler)
    try:
        try:
            client.respond("hi")
        except RuntimeError as exc:
            assert "401" in str(exc)
        else:
            raise AssertionError("expected RuntimeError on non-2xx")
    finally:
        http.close()


def test_extract_text_chat_completions_fallback():
    """Some Volcengine endpoints return OpenAI chat-completions shape."""

    def handler(req):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "fallback"}}]},
        )

    client, http = _make_client(handler)
    try:
        assert client.respond("hi") == "fallback"
    finally:
        http.close()
