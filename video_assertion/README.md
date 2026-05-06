# video-assertion

Long-video AI assertion pipeline using Volcengine **Doubao** multimodal model.

Given a video and a list of natural-language expectations like

```json
[
  "视频中没有闪屏现象",
  "视频中没有黑屏",
  "画面里有房子",
  "熊猫在动态吃竹子"
]
```

it returns a structured per-assertion `pass / fail` verdict with evidence,
without uploading the entire video to the LLM.

## Why this design

Sending the whole video to a multimodal model is expensive and noisy. Instead we
**route each assertion** to the cheapest tool that can answer it:

| Assertion kind | Routed to | Model calls |
|---|---|---|
| `no_flashing` / `no_black_screen` / `no_freeze` | Pure OpenCV statistics | 0 |
| `"there is a house"` (static presence) | Doubao + deduplicated keyframes | 1 |
| `"the panda is eating bamboo"` (dynamic action) | Doubao + 6-frame clip per scene | 1 per scene (short-circuits on confident pass) |

The router itself uses a regex fast-path for common Chinese / English wording,
falling back to Doubao only for ambiguous cases.

## Pipeline

```
video.mp4 ──► PySceneDetect (scene cuts)
                │
                ├──► per-scene keyframes  ── pHash dedup ──► static judge
                ├──► per-scene 3s clip    ── 6 sampled frames ──► dynamic judge
                └──► luminance / freeze stats ──► CV rules
                                                            │
                                                            ▼
                                                  per-assertion JSON + HTML report
```

No fine-tuning, no fixed object classes. The model your video shows can change
freely — the only thing the system reads is the text of your assertions.

## Install

```bash
pip install -e .
```

Python 3.10+. All dependencies are pure-Python wheels except OpenCV (headless).

## Configure Doubao

```bash
cp .env.example .env
# edit .env, then:
export $(grep -v '^#' .env | xargs)
```

Required:
- `DOUBAO_API_KEY` — your Volcengine Ark key (starts with `ark-...`)
- `DOUBAO_BASE_URL` — defaults to `https://ark.cn-beijing.volces.com/api/v3`
- `DOUBAO_MODEL_ENDPOINT` — e.g. `doubao-seed-2-0-pro-260215`

The client talks to `POST {base_url}/responses` (Volcengine's Responses API).

## Run as a service (recommended)

```bash
./start.sh                 # macOS / Linux
start.bat                  # Windows
```

Once started, open:

| URL | What it is |
|---|---|
| http://localhost:8000/ | Web frontend (upload video, paste assertions, view report) |
| http://localhost:8000/docs | **Swagger UI** — interactive API explorer |
| http://localhost:8000/redoc | ReDoc (alternative API docs) |
| http://localhost:8000/openapi.json | Raw OpenAPI 3.1 spec |
| http://localhost:8000/api/v1/health | Liveness probe |

Override host / port:

```bash
VA_HOST=0.0.0.0 VA_PORT=9000 ./start.sh
```

### API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/jobs` | Submit a video + assertions (multipart) |
| GET | `/api/v1/jobs` | List all jobs |
| GET | `/api/v1/jobs/{job_id}` | Job state + structured report |
| GET | `/api/v1/jobs/{job_id}/report.html` | Rendered HTML report |
| GET | `/api/v1/jobs/{job_id}/report.json` | Structured JSON report |
| GET | `/api/v1/jobs/{job_id}/evidence/{path}` | A single evidence image |
| GET | `/api/v1/health` | Liveness probe |

### Curl example (external user)

```bash
# 1. submit
curl -X POST http://localhost:8000/api/v1/jobs \
  -F "file=@/path/to/your_video.mp4" \
  -F 'assertions=["视频中没有闪屏现象","画面里有房子","熊猫在动态吃竹子"]'
# → {"job_id":"3f1c8e9a4b2d","status":"queued"}

# 2. poll until status is "completed"
curl http://localhost:8000/api/v1/jobs/3f1c8e9a4b2d

# 3. open report
xdg-open http://localhost:8000/api/v1/jobs/3f1c8e9a4b2d/report.html
```

## Run as a CLI

```bash
python cli.py \
  --video path/to/video.mp4 \
  --assertions examples/assertions.json \
  --out runs/run1
```

Outputs:
- `runs/run1/report.json` — structured verdicts
- `runs/run1/report.html` — human-readable report with embedded evidence frames
- `runs/run1/keyframes/` — extracted JPEGs
- `runs/run1/clips/` — sampled frames per scene clip

## Programmatic use

```python
from video_assertion import Assertion, run_pipeline
from video_assertion.report import write_html

report = run_pipeline(
    "video.mp4",
    [Assertion(id="a1", text="画面里有房子")],
    work_dir="runs/r1",
)
print(report.passed, report.results[0].evidence)
write_html(report, "report.html")
```

## Offline demo (no API key)

A stubbed demo that uses a synthetic 3-scene video — useful for verifying the
install:

```bash
DEMO_STUB=1 python examples/run_demo.py
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

36 tests covering CV rules, scene detection, keyframe dedup, the Doubao
HTTP wire format (mocked transport), the assertion router, the LLM judges,
end-to-end pipeline behaviour, **and the FastAPI server** (10 integration
tests via `TestClient` covering submit / poll / report download / OpenAPI
metadata / static frontend / path-traversal).

## Project layout

```
src/video_assertion/
  scene_detect.py        # PySceneDetect wrapper
  frame_extract.py       # keyframe sampling + pHash dedup
  clip_extract.py        # short-clip → N sampled frames
  cv_rules.py            # flashing / black screen / freeze
  doubao_client.py       # Volcengine Ark Responses API client
  assertion_router.py    # text → cv_rule / static / dynamic
  llm_judge.py           # Doubao-based static + dynamic judges
  pipeline.py            # orchestrator
  report.py              # JSON + HTML rendering
  server/
    api.py               # FastAPI app (Swagger /docs, ReDoc /redoc)
    jobs.py              # in-memory job store + thread-pool worker
    schemas.py           # request/response Pydantic models
    static/              # single-page frontend (HTML / CSS / JS)
tests/                   # 36 tests
examples/run_demo.py     # offline demo with stubbed Doubao
cli.py                   # CLI entry point
start.sh / start.bat     # one-click launchers
```

## Tuning

All thresholds live as keyword arguments at the top of each module:

- `scene_detect.detect_scenes(threshold=27.0, min_scene_len_frames=12)`
- `frame_extract.extract_keyframes(samples_per_scene=3, phash_distance=6)`
- `clip_extract.extract_scene_clips(frames_per_clip=6, max_clip_seconds=3.0)`
- `cv_rules.check_no_flashing(window_sec=1.0, delta_threshold=60.0, flips_threshold=4)`
- `cv_rules.check_no_black_screen(luma_threshold=8.0, min_streak_sec=0.5)`
- `cv_rules.check_no_freeze(diff_threshold=0.5, min_streak_sec=1.0)`
