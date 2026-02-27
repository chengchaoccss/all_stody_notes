"""
MCP Device Automation Server
=============================
Provides three tool groups for AI / Agent callers:

  POST /tools/download_and_install_apk  — download & install an APK
  POST /tools/start_test_record         — start screen + log capture
  POST /tools/stop_test_record          — stop capture & pull artefacts
  POST /tools/trigger_pipeline          — run a CI pipeline script

  GET  /health                          — liveness probe
  GET  /sessions                        — list active recording sessions

Run with:
    uvicorn server:app --host 0.0.0.0 --port 8000

All responses conform to the envelope:
    { "success": bool, "data": any, "error": str|null, "duration_sec": float }
"""

import time
import traceback
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from tools.ci_tool import trigger_pipeline
from tools.install_tool import download_and_install_apk
from tools.record_tool import start_test_record, stop_test_record
from utils.logger import get_logger
from utils.process_manager import process_manager

logger = get_logger("mcp_server")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resp(
    success: bool,
    data=None,
    error: Optional[str] = None,
    duration_sec: float = 0.0,
) -> dict:
    return {
        "success": success,
        "data": data,
        "error": error,
        "duration_sec": round(duration_sec, 3),
    }


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("MCP Device Automation Server starting up")
    logger.info("=" * 60)
    yield
    logger.info("MCP Server shutting down — stopping all active sessions")
    for sid in process_manager.list_sessions():
        try:
            process_manager.stop_session(sid)
        except Exception as exc:
            logger.warning("Error stopping session %s on shutdown: %s", sid, exc)
    logger.info("MCP Server stopped")


app = FastAPI(
    title="MCP Device Automation Server",
    description="AI-callable tool server for Android device automation",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def _global_exc_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s:\n%s", request.url, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content=_resp(False, error=f"{type(exc).__name__}: {exc}"),
    )


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class InstallRequest(BaseModel):
    apk_url: str
    device_id: Optional[str] = None
    install_mode: str = "replace"


class StartRecordRequest(BaseModel):
    device_id: Optional[str] = None
    session_name: Optional[str] = None


class StopRecordRequest(BaseModel):
    session_id: str


class TriggerPipelineRequest(BaseModel):
    pipeline_name: str
    extra_args: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/tools/download_and_install_apk", summary="Download APK from URL and install on device")
async def api_install(req: InstallRequest):
    t0 = time.monotonic()
    logger.info("[API] download_and_install_apk  params=%s", req.model_dump())
    try:
        data = await download_and_install_apk(
            apk_url=req.apk_url,
            device_id=req.device_id,
            install_mode=req.install_mode,
        )
        dur = time.monotonic() - t0
        logger.info("[API] download_and_install_apk  OK  %.3fs", dur)
        return _resp(True, data=data, duration_sec=dur)
    except Exception as exc:
        dur = time.monotonic() - t0
        logger.error("[API] download_and_install_apk  ERROR  %.3fs  %s", dur, exc)
        return _resp(False, error=str(exc), duration_sec=dur)


@app.post("/tools/start_test_record", summary="Begin screen recording + logcat capture")
async def api_start_record(req: StartRecordRequest):
    t0 = time.monotonic()
    logger.info("[API] start_test_record  params=%s", req.model_dump())
    try:
        data = await start_test_record(
            device_id=req.device_id,
            session_name=req.session_name,
        )
        dur = time.monotonic() - t0
        logger.info(
            "[API] start_test_record  OK  session=%s  %.3fs",
            data.get("session_id"),
            dur,
        )
        return _resp(True, data=data, duration_sec=dur)
    except Exception as exc:
        dur = time.monotonic() - t0
        logger.error("[API] start_test_record  ERROR  %.3fs  %s", dur, exc)
        return _resp(False, error=str(exc), duration_sec=dur)


@app.post("/tools/stop_test_record", summary="Stop capture, pull artefacts, write meta.json")
async def api_stop_record(req: StopRecordRequest):
    t0 = time.monotonic()
    logger.info("[API] stop_test_record  session_id=%s", req.session_id)
    try:
        data = await stop_test_record(session_id=req.session_id)
        dur = time.monotonic() - t0
        logger.info("[API] stop_test_record  OK  %.3fs", dur)
        return _resp(True, data=data, duration_sec=dur)
    except Exception as exc:
        dur = time.monotonic() - t0
        logger.error("[API] stop_test_record  ERROR  %.3fs  %s", dur, exc)
        return _resp(False, error=str(exc), duration_sec=dur)


@app.post("/tools/trigger_pipeline", summary="Execute a CI pipeline defined in ci_mapping.yaml")
async def api_trigger_pipeline(req: TriggerPipelineRequest):
    t0 = time.monotonic()
    logger.info("[API] trigger_pipeline  params=%s", req.model_dump())
    try:
        data = await trigger_pipeline(
            pipeline_name=req.pipeline_name,
            extra_args=req.extra_args or [],
        )
        dur = time.monotonic() - t0
        logger.info("[API] trigger_pipeline  OK  %.3fs", dur)
        return _resp(True, data=data, duration_sec=dur)
    except Exception as exc:
        dur = time.monotonic() - t0
        logger.error("[API] trigger_pipeline  ERROR  %.3fs  %s", dur, exc)
        return _resp(False, error=str(exc), duration_sec=dur)


# ---------------------------------------------------------------------------
# Utility endpoints
# ---------------------------------------------------------------------------

@app.get("/health", summary="Liveness probe")
async def health():
    return {"status": "ok"}


@app.get("/sessions", summary="List active recording sessions")
async def list_sessions():
    sessions = process_manager.list_sessions()
    details = {}
    for sid in sessions:
        info = process_manager.session_info(sid)
        if info is not None:
            details[sid] = info
    return _resp(True, data={"active_sessions": details, "count": len(sessions)})
