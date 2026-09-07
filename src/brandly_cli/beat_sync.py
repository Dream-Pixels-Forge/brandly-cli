"""Music-reactive video editing — cuts clips to match beat timestamps."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# FFmpeg helpers
# ---------------------------------------------------------------------------

def _ffmpeg_available() -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _ffprobe_available() -> bool:
    try:
        result = subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _get_duration(path: Path) -> float:
    """Get video/audio duration using ffprobe."""
    if not _ffprobe_available():
        return 0.0
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode != 0:
        return 0.0
    try:
        data = json.loads(result.stdout.decode())
        return float(data.get("format", {}).get("duration", 0.0))
    except (ValueError, TypeError):
        return 0.0


async def _run_ffmpeg(cmd: list[str]) -> tuple[int, str]:
    """Run FFmpeg command and return (returncode, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    return proc.returncode, stderr.decode()


# ---------------------------------------------------------------------------
# Beat detection
# ---------------------------------------------------------------------------

def detect_beats(audio_path: Path, threshold: float = 0.5) -> list[float]:
    """Detect beat timestamps in audio file.

    Uses FFmpeg's silencedetect filter to find transient peaks.
    Returns list of beat timestamps in seconds.
    """
    if not _ffmpeg_available():
        return []

    cmd = [
        "ffmpeg", "-i", str(audio_path),
        "-af", f"silencedetect=noise={-threshold*100:.0f}dB:d=0.1",
        "-f", "null", "-"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        beats: list[float] = []

        # Parse output for start_time entries
        for line in result.stderr.split('\n'):
            if 'start_time' in line:
                try:
                    time_str = line.split('=')[1].strip()
                    beats.append(float(time_str))
                except (ValueError, IndexError):
                    continue

        return sorted(beats)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


# ---------------------------------------------------------------------------
# Core beat sync
# ---------------------------------------------------------------------------

async def beat_sync(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    *,
    beat_threshold: float = 0.5,
    min_clip_duration: float = 1.0,
    root: Path | None = None,
) -> dict[str, Any]:
    """Cut video to match beat positions in audio.

    Args:
        video_path: Path to source video.
        audio_path: Path to audio file with beats.
        output_path: Output video path.
        beat_threshold: Silence detection threshold (higher = fewer beats).
        min_clip_duration: Minimum duration for each clip segment.
        root: Optional project root.

    Returns:
        Dict with sync metadata or error on failure.
    """
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)

    # Validation
    if not video_path.exists():
        return {"error": f"Video file not found: {video_path}"}
    if not audio_path.exists():
        return {"error": f"Audio file not found: {audio_path}"}
    if not _ffmpeg_available():
        return {"error": "ffmpeg not found. Install FFmpeg first."}

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Detect beats
    beats = detect_beats(audio_path, beat_threshold)

    if not beats:
        # No beats detected - just copy video with audio
        rc, stderr = await _run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(output_path),
        ])
        if rc != 0:
            return {"error": stderr[:500]}
        return {
            "video_path": str(video_path),
            "audio_path": str(audio_path),
            "output_path": str(output_path),
            "beats_detected": 0,
            "clips_created": 1,
            "total_duration": _get_duration(output_path),
        }

    # Build segment list from beats
    video_duration = _get_duration(video_path)
    segments: list[tuple[float, float]] = []

    # Add start segment (0 to first beat or min duration)
    start = 0.0
    for _, beat in enumerate(beats):
        end = min(beat, start + min_clip_duration)
        if end > video_duration:
            break
        segments.append((start, end))
        start = end

    # Add final segment if there's remaining time
    if start < video_duration:
        segments.append((start, video_duration))

    # Build complex filter for cutting and concatenating segments
    if len(segments) <= 1:
        # Just copy with new audio
        rc, stderr = await _run_ffmpeg([
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(output_path),
        ])
    else:
        # Create concat file for segments
        concat_file = output_path.parent / "_beat_concat.txt"
        concat_lines = []
        for start, end in segments:
            concat_lines.append(f"file '{video_path.resolve()}'")
            concat_lines.append(f"inpoint {start}")
            concat_lines.append(f"outpoint {end}")

        concat_file.write_text("\n".join(concat_lines), encoding="utf-8")

        rc, stderr = await _run_ffmpeg([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-i", str(audio_path),
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(output_path),
        ])
        concat_file.unlink(missing_ok=True)

        if rc != 0:
            return {"error": stderr[:500]}

    final_duration = _get_duration(output_path)
    return {
        "video_path": str(video_path),
        "audio_path": str(audio_path),
        "output_path": str(output_path),
        "beats_detected": len(beats),
        "clips_created": len(segments),
        "total_duration": final_duration,
    }
