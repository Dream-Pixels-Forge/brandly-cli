"""Waveform extraction endpoint — audio RMS envelope via ffmpeg."""

from __future__ import annotations

import json
import struct
import subprocess
from pathlib import Path

from fastapi import APIRouter, Request

from brandly_cli.io import proc_output
from brandly_cli.web import deps

router = APIRouter(prefix="/api/projects/{project_id}", tags=["waveform"])


def _ffmpeg_available() -> bool:
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _has_audio_stream(media_path: Path) -> bool:
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "json",
            str(media_path),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        if result.returncode != 0:
            return False
        data = json.loads(proc_output(result.stdout))
        streams = data.get("streams", [])
        return any(s.get("codec_type") == "audio" for s in streams)
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, KeyError):
        return False


def _extract_waveform(media_path: Path, num_points: int = 200) -> list[dict]:
    """Extract RMS envelope at ~num_points evenly-spaced positions."""
    try:
        duration_cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(media_path),
        ]
        dur_result = subprocess.run(duration_cmd, capture_output=True, timeout=10)
        if dur_result.returncode != 0:
            return []
        duration = float(json.loads(proc_output(dur_result.stdout)).get("format", {}).get("duration", 0))
        if duration <= 0:
            return []

        # Extract raw PCM, resampled to mono 8 kHz.
        pcm_cmd = [
            "ffmpeg", "-y", "-i", str(media_path),
            "-vn",
            "-ac", "1", "-ar", "8000",
            "-f", "s16le", "-acodec", "pcm_s16le",
            "pipe:1",
        ]
        pcm_result = subprocess.run(pcm_cmd, capture_output=True, timeout=60)
        if pcm_result.returncode != 0 or not pcm_result.stdout:
            return []

        raw = pcm_result.stdout
        num_samples = len(raw) // 2  # signed 16-bit
        if num_samples == 0:
            return []

        samples = struct.unpack(f"<{num_samples}h", raw)
        step = max(1, num_samples // num_points)
        points: list[dict] = []

        for i in range(num_points):
            start = i * step
            end = min(start + step, num_samples)
            chunk = samples[start:end]
            if not chunk:
                continue
            rms = (sum(s * s for s in chunk) / len(chunk)) ** 0.5
            # Normalize to [0, 1] using max possible RMS for int16
            norm = min(1.0, rms / 32767.0)
            t = (start + len(chunk) / 2) / num_samples * duration if num_samples else 0
            points.append({"x": round(t, 4), "amplitude": round(norm, 6)})

        return points
    except (FileNotFoundError, subprocess.TimeoutExpired, struct.error, ZeroDivisionError):
        return []


@router.get("/clips/{clip_id}/waveform", response_model=dict)
async def get_waveform(project_id: str, clip_id: str, request: Request) -> dict:
    """Return an RMS envelope for a clip's audio stream."""
    if not _ffmpeg_available():
        return {"points": []}

    root = request.app.state.root
    _, media = deps.require_clip_media(root, project_id, clip_id)

    if not _has_audio_stream(media):
        return {"points": []}

    points = _extract_waveform(media)
    return {"points": points}
