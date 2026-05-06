"""HTTP server (FastAPI) and lightweight static frontend for the
video-assertion pipeline."""

from .api import app, run

__all__ = ["app", "run"]
