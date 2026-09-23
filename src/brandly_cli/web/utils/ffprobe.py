"""FFprobe helpers for clip metadata."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def get_clip_duration(path: Path) -> float:
    """Return duration in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        if result.returncode != 0:
            return 0.0
        data = json.loads(result.stdout.decode())
        return float(data.get("format", {}).get("duration", 0.0))
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, KeyError):
        return 0.0


def get_clip_info(path: Path) -> dict:
    """Return full clip metadata via ffprobe."""
    try:
        import asyncio

        from brandly_cli.edit import get_video_info
        return asyncio.run(get_video_info(path))
    except Exception as e:
        return {"error": str(e)}
