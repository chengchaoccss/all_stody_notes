"""End-to-end tests for the FastAPI server using TestClient.

We never reach the real Doubao API: the JobStore is configured with a stub
client factory that returns deterministic JSON responses.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from video_assertion.server.api import create_app
from video_assertion.server.jobs import JobStore

from tests.conftest import StubClient


def _stub_response(text, image_paths, json_schema):
    p = text.lower()
    if "you are a router" in p:
        if "房子" in text or "house" in p:
            return json.dumps({"kind": "static", "cv_rule": "", "reason": ""})
        if "熊猫" in text or "panda" in p:
            return json.dumps({"kind": "dynamic", "cv_rule": "", "reason": ""})
        return json.dumps({"kind": "static", "cv_rule": "", "reason": ""})
    if "video qa judge" in p:
        if "房子" in text or "house" in p:
            return json.dumps({"passed": True, "confidence": 0.9, "evidence": "white rectangle resembling a house"})
        if "熊猫" in text or "panda" in p:
            return json.dumps({"passed": True, "confidence": 0.85, "evidence": "moving object across frames"})
        return json.dumps({"passed": False, "confidence": 0.4, "evidence": "unclear"})
    return json.dumps({"passed": False, "confidence": 0.0, "evidence": "unhandled"})


def _client_factory():
    return StubClient(responder=lambda **kw: _stub_response(kw["text"], kw["image_paths"], kw["json_schema"]))


@pytest.fixture()
def api_client(tmp_path: Path) -> TestClient:
    runs_dir = tmp_path / "runs"
    store = JobStore(runs_dir=runs_dir, client_factory=_client_factory, max_workers=2)
    app = create_app(runs_dir=runs_dir, job_store=store)
    with TestClient(app) as client:
        yield client
    store.shutdown()


def _wait_for_completion(client: TestClient, job_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/api/v1/jobs/{job_id}")
        assert r.status_code == 200
        body = r.json()
        if body["status"] in {"completed", "failed"}:
            return body
        time.sleep(0.1)
    pytest.fail(f"job {job_id} did not finish within {timeout}s")


def test_health_endpoint(api_client: TestClient):
    r = api_client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["service"] == "video-assertion"


def test_swagger_and_openapi_endpoints(api_client: TestClient):
    assert api_client.get("/openapi.json").status_code == 200
    assert api_client.get("/docs").status_code == 200
    assert api_client.get("/redoc").status_code == 200


def test_openapi_documents_submit_endpoint(api_client: TestClient):
    spec = api_client.get("/openapi.json").json()
    submit = spec["paths"]["/api/v1/jobs"]["post"]
    assert submit["tags"] == ["jobs"]
    assert "Submit" in submit["summary"]
    # multipart fields should be in the request body
    schema = submit["requestBody"]["content"]["multipart/form-data"]["schema"]
    props = schema.get("properties") or schema.get("$ref")
    # FastAPI can either inline or $ref; both are fine, just sanity-check presence
    assert props


def test_submit_invalid_assertions_returns_400(api_client: TestClient, videos):
    with open(videos["three_scenes"], "rb") as f:
        r = api_client.post(
            "/api/v1/jobs",
            files={"file": ("video.mp4", f, "video/mp4")},
            data={"assertions": "not-json"},
        )
    assert r.status_code == 400


def test_submit_empty_video_returns_400(api_client: TestClient):
    r = api_client.post(
        "/api/v1/jobs",
        files={"file": ("empty.mp4", b"", "video/mp4")},
        data={"assertions": '["x"]'},
    )
    assert r.status_code == 400


def test_get_unknown_job_returns_404(api_client: TestClient):
    assert api_client.get("/api/v1/jobs/does-not-exist").status_code == 404


def test_full_submit_poll_complete_flow(api_client: TestClient, videos):
    with open(videos["three_scenes"], "rb") as f:
        r = api_client.post(
            "/api/v1/jobs",
            files={"file": ("video.mp4", f, "video/mp4")},
            data={
                "assertions": json.dumps(
                    [
                        "视频中没有闪屏现象",
                        "画面里有房子",
                        "熊猫在动态吃竹子",
                    ]
                )
            },
        )
    assert r.status_code == 202
    submit = r.json()
    assert submit["status"] == "queued"
    job_id = submit["job_id"]

    # list endpoint should now show this job
    listing = api_client.get("/api/v1/jobs").json()
    assert any(j["job_id"] == job_id for j in listing["items"])

    final = _wait_for_completion(api_client, job_id)
    assert final["status"] == "completed", final
    report = final["report"]
    assert len(report["results"]) == 3
    by_id = {r["assertion_id"]: r for r in report["results"]}
    assert by_id["a1"]["kind"] == "cv_rule"
    assert by_id["a1"]["passed"] is True
    assert by_id["a2"]["passed"] is True
    assert by_id["a3"]["passed"] is True

    # report.html artifact is downloadable
    html = api_client.get(f"/api/v1/jobs/{job_id}/report.html")
    assert html.status_code == 200
    assert "<html" in html.text.lower()

    # report.json artifact is downloadable
    js = api_client.get(f"/api/v1/jobs/{job_id}/report.json").json()
    assert js["video_path"]
    assert len(js["results"]) == 3


def test_flashing_video_fails_no_flashing_via_api(api_client: TestClient, videos):
    with open(videos["flashing"], "rb") as f:
        r = api_client.post(
            "/api/v1/jobs",
            files={"file": ("flash.mp4", f, "video/mp4")},
            data={"assertions": json.dumps(["视频中没有闪屏现象"])},
        )
    job_id = r.json()["job_id"]
    final = _wait_for_completion(api_client, job_id)
    assert final["status"] == "completed"
    assert final["report"]["results"][0]["passed"] is False


def test_evidence_path_traversal_is_blocked(api_client: TestClient, videos):
    with open(videos["three_scenes"], "rb") as f:
        r = api_client.post(
            "/api/v1/jobs",
            files={"file": ("v.mp4", f, "video/mp4")},
            data={"assertions": json.dumps(["画面里有房子"])},
        )
    job_id = r.json()["job_id"]
    _wait_for_completion(api_client, job_id)
    # try to escape the runs/<job_id> folder
    r = api_client.get(f"/api/v1/jobs/{job_id}/evidence/../../etc/passwd")
    assert r.status_code == 404


def test_static_frontend_is_served_at_root(api_client: TestClient):
    r = api_client.get("/")
    assert r.status_code == 200
    assert "视频断言" in r.text or "video" in r.text.lower()
