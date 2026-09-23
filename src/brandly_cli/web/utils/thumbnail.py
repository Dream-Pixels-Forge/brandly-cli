"""Thumbnail extraction for clip cards."""

from __future__ import annotations

import subprocess
from pathlib import Path


def extract_thumbnail(video_path: Path, output_path: Path, *, timestamp: float = 0.5) -> bool:
    """Extract first frame as PNG thumbnail using ffmpeg."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return result.returncode == 0 and output_path.exists()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def ensure_thumbnail(video_path: Path, proj_dir: Path) -> str | None:
    """Ensure a thumbnail exists for a video clip. Returns relative path or None."""
    stem = video_path.stem
    thumb_dir = proj_dir / "thumbnails"
    thumb_path = thumb_dir / f"{stem}.png"

    if thumb_path.exists():
        return f"thumbnails/{stem}.png"

    if extract_thumbnail(video_path, thumb_path):
        return f"thumbnails/{stem}.png"

    return None
