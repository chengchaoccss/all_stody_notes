#!/usr/bin/env bash
# One-click launcher for the video-assertion service.
#
# Behaviour:
#   - loads .env if present (DOUBAO_API_KEY etc.)
#   - installs missing Python deps the first time it runs
#   - starts the FastAPI app via uvicorn
#
# Override:
#   VA_HOST=0.0.0.0  VA_PORT=8000  ./start.sh
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. load .env
if [[ -f .env ]]; then
  echo "[start] loading .env"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# 2. validate required env
if [[ -z "${DOUBAO_API_KEY:-}" ]]; then
  cat <<'EOF' >&2
[start] ERROR: DOUBAO_API_KEY is not set.

   Either export it in your shell:
     export DOUBAO_API_KEY=ark-xxxxxxxx
     export DOUBAO_MODEL_ENDPOINT=doubao-seed-2-0-pro-260215
   or copy the template:
     cp .env.example .env   # then edit .env
EOF
  exit 1
fi

# 3. install deps if needed
PY=${PYTHON:-python3}
if ! "$PY" -c "import fastapi, uvicorn, video_assertion" >/dev/null 2>&1; then
  echo "[start] installing Python dependencies (one-time)"
  "$PY" -m pip install -e . >/dev/null
fi

HOST="${VA_HOST:-0.0.0.0}"
PORT="${VA_PORT:-8000}"
RUNS_DIR="${VA_RUNS_DIR:-runs}"
mkdir -p "$RUNS_DIR"

cat <<EOF
================================================================
 video-assertion service starting

   Frontend  →  http://localhost:${PORT}
   Swagger   →  http://localhost:${PORT}/docs
   ReDoc     →  http://localhost:${PORT}/redoc
   Health    →  http://localhost:${PORT}/api/v1/health

   Doubao endpoint : ${DOUBAO_BASE_URL:-https://ark.cn-beijing.volces.com/api/v3}
   Doubao model    : ${DOUBAO_MODEL_ENDPOINT:-(default)}
   Job artifacts   : $(realpath "$RUNS_DIR")
================================================================
EOF

exec "$PY" -m uvicorn video_assertion.server.api:app \
  --host "$HOST" --port "$PORT" \
  --log-level "${VA_LOG_LEVEL:-info}"
