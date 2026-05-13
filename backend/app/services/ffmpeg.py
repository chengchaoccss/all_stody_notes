import json
import subprocess
from pathlib import Path


class FFmpegError(RuntimeError):
    pass


def extract_audio(video_path: Path, audio_path: Path, sample_rate: int = 16000) -> Path:
    """Extract a mono 16kHz WAV from any video container. Doubao ASR works well with 16k mono."""
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-acodec",
        "pcm_s16le",
        str(audio_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FFmpegError(proc.stderr[-2000:])
    return audio_path


def probe_duration(media_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(media_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FFmpegError(proc.stderr[-2000:])
    data = json.loads(proc.stdout)
    return float(data["format"]["duration"])
