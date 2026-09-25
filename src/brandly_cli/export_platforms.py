"""Platform-optimized video exports for TikTok, Instagram, YouTube, etc."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

from brandly_cli.io import proc_output

# ---------------------------------------------------------------------------
# Platform presets
# ---------------------------------------------------------------------------

PLATFORM_PRESETS: dict[str, dict[str, Any]] = {
    "tiktok": {
        "ratio": "9:16",
        "max_duration": 60,
        "caption_style": "bold_center",
        "safe_zone": 0.15,
    },
    "instagram_reel": {
        "ratio": "9:16",
        "max_duration": 90,
        "caption_style": "subtle_bottom",
        "safe_zone": 0.10,
    },
    "instagram_post": {
        "ratio": "4:5",
        "max_duration": 90,
        "caption_style": "elegant_bottom",
        "safe_zone": 0.08,
    },
    "youtube_short": {
        "ratio": "9:16",
        "max_duration": 60,
        "caption_style": "bold_center",
        "safe_zone": 0.15,
    },
    "youtube_standard": {
        "ratio": "16:9",
        "max_duration": 300,
        "caption_style": "professional",
        "safe_zone": 0.05,
    },
    "facebook_story": {
        "ratio": "9:16",
        "max_duration": 15,
        "caption_style": "bold_center",
        "safe_zone": 0.20,
    },
}


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


async def _run_ffmpeg(cmd: list[str]) -> tuple[int | None, str]:
    """Run FFmpeg command and return (returncode, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    return proc.returncode, proc_output(stderr)


def _get_duration(path: Path) -> float:
    """Get video duration using ffprobe."""
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
        data = json.loads(proc_output(result.stdout))
        return float(data.get("format", {}).get("duration", 0.0))
    except (ValueError, TypeError):
        return 0.0


# ---------------------------------------------------------------------------
# Export function
# ---------------------------------------------------------------------------

async def export_for_platform(
    input_video: Path,
    platform: str,
    output_dir: Path,
    *,
    add_captions: bool = True,
    captions_text: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Export video optimized for a specific platform.

    Args:
        input_video: Path to the source video.
        platform: Platform name (e.g., "tiktok", "instagram_reel", "youtube_standard").
        output_dir: Directory to write exported video.
        add_captions: Whether to add text overlay captions.
        captions_text: Text to overlay (if any).
        root: Optional project root for relative paths.

    Returns:
        Dict with platform, output_path, duration_seconds, file_size_bytes, captions_added.
        On failure, returns {"error": <message>}.
    """
    input_video = Path(input_video)
    output_dir = Path(output_dir)

    # Validation
    if not input_video.exists():
        return {"error": f"Input file not found: {input_video}"}
    if platform not in PLATFORM_PRESETS:
        raise ValueError(f"Unknown platform: {platform}. Valid: {list(PLATFORM_PRESETS)}")
    if not _ffmpeg_available():
        return {"error": "ffmpeg not found. Install FFmpeg first."}

    preset = PLATFORM_PRESETS[platform]
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine output filename
    output_name = f"{input_video.stem}_{platform}{input_video.suffix}"
    output_path = output_dir / output_name

    # Get source duration
    source_duration = _get_duration(input_video)
    max_duration = preset["max_duration"]

    # Build filter for aspect ratio (scale to target dimensions)
    target_ratio = preset["ratio"]
    filter_parts: list[str] = []

    # Parse ratio to determine target dimensions
    # Use standard resolutions for each ratio
    ratio_to_dims: dict[str, tuple[int, int]] = {
        "9:16": (1080, 1920),
        "4:5": (1080, 1350),
        "1:1": (1080, 1080),
        "16:9": (1920, 1080),
        "4:3": (1080, 810),
    }

    if ":" in target_ratio:
        w_ratio, h_ratio = target_ratio.split(":")
        # Use standard resolution based on ratio
        dims = ratio_to_dims.get(target_ratio, (1920, 1080))
        target_w, target_h = dims
    else:
        target_w, target_h = 1080, 1920

    # Scale to exact target dimensions (letterbox/pillarbox handled by simple scale)
    scale_filter = f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease"
    filter_parts.append(scale_filter)

    # Pad to exact target dimensions with black bars
    if target_w > target_h:
        pad_filter = f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2"
    else:
        pad_filter = f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2"
    filter_parts.append(pad_filter)

    # Add text overlay if requested and text provided
    if add_captions and captions_text:
        # Use drawtext filter for caption overlay
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        text_filter = (
            f"drawtext=fontfile={font_path}"
            f":text='{captions_text}'"
            f":fontcolor=white:fontsize=48"
            f":x=(w-text_w)/2:y=h-80"
        )
        filter_parts.append(text_filter)

    vf_filter = ",".join(filter_parts)

    # Build FFmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_video),
        "-vf", vf_filter,
        "-t", str(min(source_duration, max_duration)),
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    rc, stderr = await _run_ffmpeg(cmd)
    if rc != 0:
        return {"error": stderr[:500]}

    # Get final duration and size
    final_duration = _get_duration(output_path)
    file_size = output_path.stat().st_size if output_path.exists() else 0

    return {
        "platform": platform,
        "output_path": str(output_path),
        "ratio": target_ratio,
        "duration_seconds": final_duration,
        "file_size_bytes": file_size,
        "captions_added": add_captions and bool(captions_text),
    }
