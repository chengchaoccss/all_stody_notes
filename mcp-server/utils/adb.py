"""
ADB utility wrappers.

All blocking one-shot commands are executed asynchronously via
asyncio.create_subprocess_exec so they don't stall the event loop.

Long-running background processes (screenrecord, logcat) are started
as plain subprocess.Popen objects so they can be managed by
ProcessManager without mixing async/sync concerns.
"""

import asyncio
import subprocess
from typing import List, Optional, Tuple

from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

async def _run(cmd: List[str], timeout: int = 60) -> Tuple[int, str, str]:
    """Execute *cmd* asynchronously, return (returncode, stdout, stderr)."""
    logger.debug("CMD: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"Command timed out ({timeout}s): {' '.join(cmd)}")

    return (
        proc.returncode,
        stdout_b.decode("utf-8", errors="replace"),
        stderr_b.decode("utf-8", errors="replace"),
    )


# ---------------------------------------------------------------------------
# Device discovery
# ---------------------------------------------------------------------------

async def get_devices() -> List[str]:
    """Return list of online device serials from `adb devices`."""
    rc, out, err = await _run(["adb", "devices"])
    if rc != 0:
        raise RuntimeError(f"adb devices failed: {err.strip()}")

    devices: List[str] = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if "\t" in line:
            serial, status = line.split("\t", 1)
            if status.strip() == "device":
                devices.append(serial.strip())
    return devices


async def resolve_device(device_id: Optional[str]) -> str:
    """
    Return *device_id* after verifying it is connected, or auto-select the
    only available device.  Raises RuntimeError if the device cannot be
    determined unambiguously.
    """
    devices = await get_devices()
    if not devices:
        raise RuntimeError("No Android device connected via ADB")

    if device_id:
        if device_id not in devices:
            raise RuntimeError(
                f"Device '{device_id}' not found. "
                f"Connected devices: {devices}"
            )
        return device_id

    if len(devices) > 1:
        raise RuntimeError(
            f"Multiple devices connected — specify device_id. "
            f"Available: {devices}"
        )
    return devices[0]


# ---------------------------------------------------------------------------
# APK operations
# ---------------------------------------------------------------------------

async def get_package_name(apk_path: str) -> str:
    """Extract the package name from an APK file using *aapt*."""
    rc, out, err = await _run(["aapt", "dump", "badging", apk_path], timeout=30)
    if rc != 0:
        raise RuntimeError(f"aapt dump badging failed: {err.strip()}")

    for line in out.splitlines():
        if line.startswith("package:"):
            for token in line.split():
                if token.startswith("name="):
                    return token.split("=", 1)[1].strip("'\"")

    raise RuntimeError("Could not parse package name from APK")


async def install_apk(device_id: str, apk_path: str) -> str:
    """Install *apk_path* on *device_id* with `adb install -r`."""
    rc, out, err = await _run(
        ["adb", "-s", device_id, "install", "-r", apk_path],
        timeout=120,
    )
    combined = (out + err).strip()
    if rc != 0 or "Failure" in combined:
        raise RuntimeError(f"adb install failed (rc={rc}): {combined}")
    return combined


async def uninstall_package(device_id: str, package_name: str) -> str:
    """Uninstall *package_name* from *device_id*."""
    rc, out, err = await _run(
        ["adb", "-s", device_id, "uninstall", package_name],
        timeout=60,
    )
    return (out + err).strip()


# ---------------------------------------------------------------------------
# Background process helpers (return subprocess.Popen, not coroutines)
# ---------------------------------------------------------------------------

def start_background_process(
    cmd: List[str],
    stdout_file: Optional[str] = None,
) -> subprocess.Popen:
    """
    Launch *cmd* as a detached background subprocess.

    If *stdout_file* is given, stdout (and stderr) are written to that path.
    The opened file handle is attached as ``proc._mcp_fh`` so ProcessManager
    can close it when the process is terminated.
    """
    if stdout_file:
        fh = open(stdout_file, "w", encoding="utf-8")
        proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT)
        proc._mcp_fh = fh  # type: ignore[attr-defined]
    else:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        proc._mcp_fh = None  # type: ignore[attr-defined]

    logger.debug("Started background process pid=%d: %s", proc.pid, " ".join(cmd))
    return proc


# ---------------------------------------------------------------------------
# File transfer
# ---------------------------------------------------------------------------

async def pull_file(device_id: str, remote_path: str, local_path: str) -> str:
    """Pull a file from the device to *local_path*."""
    rc, out, err = await _run(
        ["adb", "-s", device_id, "pull", remote_path, local_path],
        timeout=120,
    )
    if rc != 0:
        raise RuntimeError(f"adb pull failed: {(out + err).strip()}")
    return (out + err).strip()


async def shell_delete(device_id: str, remote_path: str) -> None:
    """Delete *remote_path* on the device (best-effort, errors are logged)."""
    rc, out, err = await _run(
        ["adb", "-s", device_id, "shell", "rm", "-f", remote_path],
        timeout=30,
    )
    if rc != 0:
        logger.warning("shell rm failed for %s: %s", remote_path, (out + err).strip())


# ---------------------------------------------------------------------------
# Screenrecord lifecycle
# ---------------------------------------------------------------------------

async def signal_screenrecord_stop(device_id: str) -> None:
    """
    Send SIGINT to the screenrecord process on the device so that it
    properly flushes and closes the MP4 file before we pull it.
    """
    rc, out, err = await _run(
        ["adb", "-s", device_id, "shell", "pkill", "-2", "screenrecord"],
        timeout=10,
    )
    if rc != 0:
        logger.warning(
            "pkill screenrecord returned rc=%d — process may have already exited",
            rc,
        )
