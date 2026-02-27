"""
Tool: test recording session management

Manages a test session that runs three parallel background captures:
  • screenrecord  — writes /sdcard/mcp_record.mp4 on the device
  • logcat        — writes outputs/sessions/<id>/logcat.txt
  • crash logcat  — writes outputs/sessions/<id>/crash.txt

Session directory layout
------------------------
outputs/sessions/<session_id>/
  screen.mp4
  logcat.txt
  crash.txt
  meta.json

Multiple sessions can run concurrently — each is tracked independently
by ProcessManager.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from utils.adb import (
    pull_file,
    resolve_device,
    shell_delete,
    signal_screenrecord_stop,
    start_background_process,
)
from utils.logger import get_logger
from utils.process_manager import process_manager

logger = get_logger(__name__)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_SESSION_DIR = os.path.join(_PROJECT_ROOT, "outputs", "sessions")
REMOTE_VIDEO_PATH = "/sdcard/mcp_record.mp4"


def _session_dir(session_id: str) -> str:
    """Return (and create) the local directory for *session_id*."""
    path = os.path.join(BASE_SESSION_DIR, session_id)
    os.makedirs(path, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

async def start_test_record(
    device_id: Optional[str],
    session_name: Optional[str],
) -> dict:
    """
    Start a recording session.

    Creates the session directory, spawns three background processes
    (screenrecord, logcat, crash logcat), writes an initial meta.json,
    and returns the session_id.

    Parameters
    ----------
    device_id : str | None
        Target device serial.  Auto-selected if only one device is connected.
    session_name : str | None
        Optional human-readable label; prepended to the generated session ID.

    Returns
    -------
    dict with keys: session_id, session_dir, device_id, started_at
    """
    device = await resolve_device(device_id)

    # Build a unique, filesystem-safe session ID
    uid = str(uuid.uuid4()).replace("-", "")[:12]
    if session_name:
        safe_name = "".join(c for c in session_name if c.isalnum() or c in "_-")[:40]
        session_id = f"{safe_name}_{uid}"
    else:
        session_id = uid

    sess_dir = _session_dir(session_id)
    started_at = datetime.now(timezone.utc).isoformat()

    logger.info("[record] Starting session=%s device=%s", session_id, device)

    # ── 1. screenrecord ───────────────────────────────────────────────────
    screen_proc = start_background_process(
        ["adb", "-s", device, "shell", "screenrecord", REMOTE_VIDEO_PATH],
    )
    process_manager.register(session_id, screen_proc, name="screenrecord")

    # ── 2. logcat (all buffers) ───────────────────────────────────────────
    logcat_path = os.path.join(sess_dir, "logcat.txt")
    logcat_proc = start_background_process(
        ["adb", "-s", device, "logcat"],
        stdout_file=logcat_path,
    )
    process_manager.register(session_id, logcat_proc, name="logcat")

    # ── 3. crash logcat ───────────────────────────────────────────────────
    crash_path = os.path.join(sess_dir, "crash.txt")
    crash_proc = start_background_process(
        ["adb", "-s", device, "logcat", "-b", "crash"],
        stdout_file=crash_path,
    )
    process_manager.register(session_id, crash_proc, name="crash_logcat")

    # ── Write initial meta.json ───────────────────────────────────────────
    meta = {
        "session_id": session_id,
        "session_name": session_name,
        "device_id": device,
        "started_at": started_at,
        "stopped_at": None,
        "duration_sec": None,
        "status": "recording",
        "files": {
            "screen": "screen.mp4",
            "logcat": "logcat.txt",
            "crash": "crash.txt",
        },
    }
    with open(os.path.join(sess_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info("[record] Session %s started", session_id)
    return {
        "session_id": session_id,
        "session_dir": sess_dir,
        "device_id": device,
        "started_at": started_at,
    }


# ---------------------------------------------------------------------------
# Stop
# ---------------------------------------------------------------------------

async def stop_test_record(session_id: str) -> dict:
    """
    Stop the recording session identified by *session_id*.

    Flow
    ----
    1. Verify session is active
    2. Send SIGINT to screenrecord on the device (so the MP4 finalises)
    3. Wait briefly for the file to close
    4. Terminate logcat / crash-logcat subprocesses
    5. Pull screen.mp4 from the device
    6. Delete the temporary file from the device
    7. Update meta.json with timing information

    Returns
    -------
    dict with session summary and file paths.
    """
    if not process_manager.is_active(session_id):
        raise ValueError(f"No active session found: '{session_id}'")

    sess_dir = _session_dir(session_id)
    meta_path = os.path.join(sess_dir, "meta.json")

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    device: str = meta["device_id"]
    started_at = datetime.fromisoformat(meta["started_at"])

    logger.info("[record] Stopping session=%s device=%s", session_id, device)

    # ── 1. Gracefully stop screenrecord on the device ─────────────────────
    try:
        await signal_screenrecord_stop(device)
        logger.info("[record] Sent SIGINT to screenrecord on %s", device)
    except Exception as exc:
        logger.warning("[record] signal_screenrecord_stop: %s", exc)

    # Give screenrecord time to flush and close the MP4
    await asyncio.sleep(2)

    # ── 2. Kill local background processes (logcat, screenrecord adb) ─────
    process_manager.stop_session(session_id)

    # ── 3. Pull screen recording ──────────────────────────────────────────
    screen_local = os.path.join(sess_dir, "screen.mp4")
    pull_error: Optional[str] = None
    try:
        await pull_file(device, REMOTE_VIDEO_PATH, screen_local)
        logger.info("[record] Pulled screen.mp4 to %s", screen_local)
        await shell_delete(device, REMOTE_VIDEO_PATH)
    except Exception as exc:
        pull_error = str(exc)
        logger.warning("[record] Failed to pull screen recording: %s", exc)

    # ── 4. Update meta.json ───────────────────────────────────────────────
    stopped_at = datetime.now(timezone.utc)
    # Handle timezone-aware vs naive comparison
    if started_at.tzinfo is None:
        duration_sec = (stopped_at.replace(tzinfo=None) - started_at).total_seconds()
    else:
        duration_sec = (stopped_at - started_at).total_seconds()

    stopped_at_str = stopped_at.isoformat()
    meta.update(
        {
            "stopped_at": stopped_at_str,
            "duration_sec": round(duration_sec, 3),
            "status": "completed",
            "pull_error": pull_error,
        }
    )
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info("[record] Session %s done, duration=%.1fs", session_id, duration_sec)

    return {
        "session_id": session_id,
        "session_dir": sess_dir,
        "duration_sec": round(duration_sec, 3),
        "stopped_at": stopped_at_str,
        "files": {
            "screen": screen_local if not pull_error else None,
            "logcat": os.path.join(sess_dir, "logcat.txt"),
            "crash": os.path.join(sess_dir, "crash.txt"),
            "meta": meta_path,
        },
        "pull_error": pull_error,
    }
