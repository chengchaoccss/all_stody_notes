"""
Async HTTP/HTTPS file downloader.

Security policy: only http:// and https:// URLs are accepted.
"""

import os
import tempfile
import urllib.parse
from typing import Optional

import httpx

from utils.logger import get_logger

logger = get_logger(__name__)

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def _validate_url(url: str) -> None:
    """Raise ValueError if *url* is not a safe http/https URL."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"URL scheme '{parsed.scheme}' is not allowed. "
            "Only http and https are supported."
        )
    if not parsed.netloc:
        raise ValueError(f"URL has no host: '{url}'")


async def download_file(url: str, dest_dir: Optional[str] = None) -> str:
    """
    Download *url* to *dest_dir* (or a fresh temp directory) and return the
    local file path.

    Raises
    ------
    ValueError
        If the URL scheme is not http/https.
    httpx.HTTPStatusError
        If the server returns a non-2xx response.
    RuntimeError
        If the download produces an empty file.
    """
    _validate_url(url)

    if dest_dir is None:
        dest_dir = tempfile.mkdtemp(prefix="mcp_dl_")
    os.makedirs(dest_dir, exist_ok=True)

    # Derive a safe filename from the URL path component
    parsed = urllib.parse.urlparse(url)
    raw_name = os.path.basename(parsed.path) or "download"
    # Strip potentially dangerous characters from the filename
    filename = "".join(c for c in raw_name if c.isalnum() or c in "._-")
    if not filename:
        filename = "download"
    local_path = os.path.join(dest_dir, filename)

    logger.info("Downloading %s → %s", url, local_path)

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=5.0),
    ) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(local_path, "wb") as fout:
                async for chunk in resp.aiter_bytes(chunk_size=65_536):
                    fout.write(chunk)

    size = os.path.getsize(local_path)
    if size == 0:
        raise RuntimeError(f"Downloaded file is empty: {local_path}")

    logger.info("Download complete: %s (%d bytes)", local_path, size)
    return local_path
