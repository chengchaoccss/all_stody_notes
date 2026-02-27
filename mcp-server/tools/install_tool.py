"""
Tool: download_and_install_apk

Downloads an APK from a URL, optionally uninstalls the existing package
(clean mode), then installs the APK on the target Android device.
"""

import os
import tempfile
import time
from typing import Optional

from utils.adb import get_package_name, install_apk, resolve_device, uninstall_package
from utils.downloader import download_file
from utils.logger import get_logger

logger = get_logger(__name__)

_VALID_MODES = frozenset({"replace", "clean"})


async def download_and_install_apk(
    apk_url: str,
    device_id: Optional[str],
    install_mode: str,
) -> dict:
    """
    Full flow:
      1. Validate install_mode
      2. Download APK to a temp directory
      3. Resolve target device
      4. (clean mode) Extract package name with aapt, then adb uninstall
      5. adb install -r <apk>
      6. Return structured result dict

    Parameters
    ----------
    apk_url : str
        HTTP/HTTPS URL of the APK file.
    device_id : str | None
        Target device serial.  Auto-selected if only one device is connected.
    install_mode : str
        ``"replace"`` — reinstall keeping data (default).
        ``"clean"``   — uninstall first, then install fresh.

    Raises
    ------
    ValueError
        Invalid install_mode.
    RuntimeError
        ADB or aapt failures, device not found, etc.
    """
    if install_mode not in _VALID_MODES:
        raise ValueError(
            f"install_mode must be one of {sorted(_VALID_MODES)}, "
            f"got '{install_mode}'"
        )

    t0 = time.monotonic()
    tmp_dir = tempfile.mkdtemp(prefix="mcp_apk_")

    # ── Step 1: Download ──────────────────────────────────────────────────
    logger.info("[install] Downloading APK from %s", apk_url)
    apk_path = await download_file(apk_url, dest_dir=tmp_dir)
    logger.info("[install] APK saved to %s", apk_path)

    # ── Step 2: Resolve device ────────────────────────────────────────────
    device = await resolve_device(device_id)
    logger.info("[install] Target device: %s", device)

    result: dict = {
        "device_id": device,
        "apk_path": apk_path,
        "apk_size_bytes": os.path.getsize(apk_path),
        "install_mode": install_mode,
    }

    # ── Step 3: Clean install — uninstall first ───────────────────────────
    if install_mode == "clean":
        logger.info("[install] Clean mode: extracting package name")
        package_name = await get_package_name(apk_path)
        result["package_name"] = package_name
        logger.info("[install] Uninstalling %s", package_name)
        uninstall_out = await uninstall_package(device, package_name)
        result["uninstall_output"] = uninstall_out
        logger.info("[install] Uninstall output: %s", uninstall_out)

    # ── Step 4: Install ───────────────────────────────────────────────────
    logger.info("[install] Running adb install on %s", device)
    install_out = await install_apk(device, apk_path)
    result["install_output"] = install_out

    result["elapsed_sec"] = round(time.monotonic() - t0, 3)
    logger.info("[install] Done in %.3fs — %s", result["elapsed_sec"], install_out)
    return result
