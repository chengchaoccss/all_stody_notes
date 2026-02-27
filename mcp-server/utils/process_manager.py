"""
Thread-safe manager for background subprocess.Popen objects grouped by session.

Usage
-----
    # Start a background process and register it
    proc = start_background_process(cmd, stdout_file="/tmp/out.txt")
    process_manager.register("session-abc", proc, name="logcat")

    # Later: stop every process that belongs to the session
    process_manager.stop_session("session-abc")

The manager is a module-level singleton shared across the entire application.
"""

import subprocess
import threading
from typing import Dict, List, NamedTuple, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class _Entry(NamedTuple):
    proc: subprocess.Popen
    name: str


class ProcessManager:
    """Manages groups of long-running subprocesses keyed by session ID."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: Dict[str, List[_Entry]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        session_id: str,
        proc: subprocess.Popen,
        name: str = "",
    ) -> None:
        """Associate *proc* with *session_id*."""
        with self._lock:
            self._sessions.setdefault(session_id, []).append(_Entry(proc, name))
        logger.debug(
            "[%s] Registered process '%s' pid=%d", session_id, name, proc.pid
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def stop_session(self, session_id: str) -> List[int]:
        """
        Terminate all processes registered under *session_id*.

        Returns the list of PIDs that were stopped.
        """
        with self._lock:
            entries = self._sessions.pop(session_id, [])

        if not entries:
            logger.warning("[%s] stop_session called but no processes found", session_id)
            return []

        pids: List[int] = []
        for entry in entries:
            proc, name = entry.proc, entry.name
            pids.append(proc.pid)
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(
                            "[%s] Process '%s' pid=%d did not stop after SIGTERM — killing",
                            session_id,
                            name,
                            proc.pid,
                        )
                        proc.kill()
                        proc.wait(timeout=3)

                # Close any file handle that was attached by start_background_process
                fh = getattr(proc, "_mcp_fh", None)
                if fh is not None and not fh.closed:
                    try:
                        fh.flush()
                        fh.close()
                    except Exception as fh_err:
                        logger.debug("Error closing file handle: %s", fh_err)

                logger.info(
                    "[%s] Stopped process '%s' pid=%d (exit=%s)",
                    session_id,
                    name,
                    proc.pid,
                    proc.returncode,
                )
            except Exception as exc:
                logger.warning(
                    "[%s] Error stopping process '%s' pid=%d: %s",
                    session_id,
                    name,
                    proc.pid,
                    exc,
                )

        return pids

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def is_active(self, session_id: str) -> bool:
        """Return True if *session_id* has registered processes."""
        with self._lock:
            return session_id in self._sessions

    def list_sessions(self) -> List[str]:
        """Return a snapshot of all active session IDs."""
        with self._lock:
            return list(self._sessions.keys())

    def session_info(self, session_id: str) -> Optional[List[dict]]:
        """Return process info for *session_id*, or None if not found."""
        with self._lock:
            entries = self._sessions.get(session_id)
        if entries is None:
            return None
        return [
            {
                "name": e.name,
                "pid": e.proc.pid,
                "running": e.proc.poll() is None,
            }
            for e in entries
        ]


# Module-level singleton
process_manager = ProcessManager()
