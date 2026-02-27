"""
Tool: trigger_pipeline

Reads a YAML mapping (config/ci_mapping.yaml), finds the requested
pipeline entry, and executes the associated Python script.

Security guarantees
-------------------
* Only scripts declared in ci_mapping.yaml can be executed.
* Script paths must be relative and cannot escape the project root.
* extra_args are validated — shell metacharacters are rejected.
* The executor is always sys.executable (the same Python interpreter),
  never an arbitrary shell.
"""

import asyncio
import os
import sys
from typing import List

import yaml

from utils.logger import get_logger

logger = get_logger(__name__)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config", "ci_mapping.yaml")

# Characters that could be used for shell injection in extra_args
_SHELL_META = frozenset({";", "&", "|", "$", "`", "\n", "\r", ">", "<", "!"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_mapping() -> dict:
    if not os.path.exists(_CONFIG_PATH):
        raise FileNotFoundError(
            f"CI mapping config not found: {_CONFIG_PATH}"
        )
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _resolve_script(relative_path: str) -> str:
    """
    Resolve *relative_path* to an absolute path inside the project root.

    Raises ValueError if the path is absolute, contains ``..``, or would
    land outside the project root.
    """
    if os.path.isabs(relative_path):
        raise ValueError(
            f"Script path must be relative, got absolute path: '{relative_path}'"
        )
    if ".." in relative_path.split(os.sep) or ".." in relative_path.split("/"):
        raise ValueError(
            f"Script path must not contain '..': '{relative_path}'"
        )
    abs_path = os.path.normpath(os.path.join(_PROJECT_ROOT, relative_path))
    # Final guard: make sure the resolved path is still inside the project
    if not abs_path.startswith(_PROJECT_ROOT + os.sep):
        raise ValueError(
            f"Script '{relative_path}' resolves outside the project root — rejected."
        )
    return abs_path


def _validate_extra_args(extra_args: List[str]) -> None:
    for arg in extra_args:
        for ch in arg:
            if ch in _SHELL_META:
                raise ValueError(
                    f"Forbidden character '{ch}' in extra_arg: '{arg}'"
                )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def trigger_pipeline(pipeline_name: str, extra_args: List[str]) -> dict:
    """
    Execute the CI pipeline named *pipeline_name*.

    Parameters
    ----------
    pipeline_name : str
        Key in config/ci_mapping.yaml.
    extra_args : list[str]
        Additional CLI arguments appended to the script's default args.

    Returns
    -------
    dict with keys: pipeline_name, command, returncode, stdout, stderr
    """
    mapping = _load_mapping()

    if pipeline_name not in mapping:
        raise ValueError(
            f"Pipeline '{pipeline_name}' not found in CI mapping. "
            f"Available pipelines: {sorted(mapping.keys())}"
        )

    pipeline_cfg = mapping[pipeline_name]
    if not isinstance(pipeline_cfg, dict):
        raise ValueError(
            f"Pipeline '{pipeline_name}' config is malformed (expected a dict)"
        )

    script_rel: str = pipeline_cfg.get("script", "")
    if not script_rel:
        raise ValueError(f"Pipeline '{pipeline_name}' has no 'script' defined")

    default_args: List[str] = [str(a) for a in (pipeline_cfg.get("args") or [])]

    # ── Security checks ───────────────────────────────────────────────────
    script_abs = _resolve_script(script_rel)
    if not os.path.exists(script_abs):
        raise FileNotFoundError(
            f"Script not found: {script_abs}. "
            "Add the script file or update ci_mapping.yaml."
        )
    _validate_extra_args(extra_args)

    # ── Build command ─────────────────────────────────────────────────────
    cmd: List[str] = (
        [sys.executable, script_abs] + default_args + [str(a) for a in extra_args]
    )
    logger.info(
        "[ci] Triggering pipeline '%s': %s", pipeline_name, " ".join(cmd)
    )

    # ── Execute ───────────────────────────────────────────────────────────
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=_PROJECT_ROOT,
    )

    timeout_sec: int = int(pipeline_cfg.get("timeout_sec", 300))
    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_sec
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(
            f"Pipeline '{pipeline_name}' timed out after {timeout_sec}s"
        )

    stdout_str = stdout_b.decode("utf-8", errors="replace")
    stderr_str = stderr_b.decode("utf-8", errors="replace")

    if proc.returncode != 0:
        raise RuntimeError(
            f"Pipeline '{pipeline_name}' exited with code {proc.returncode}. "
            f"stderr: {stderr_str.strip()}"
        )

    logger.info(
        "[ci] Pipeline '%s' finished (rc=%d)", pipeline_name, proc.returncode
    )
    return {
        "pipeline_name": pipeline_name,
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": stdout_str,
        "stderr": stderr_str,
    }
