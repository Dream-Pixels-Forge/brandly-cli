"""Video thumbnail generation — keyframe extraction and text overlay."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ffmpeg_available() -> bool:
    """Check whether ffmpeg is installed and reachable."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


async def _run_ffmpeg(cmd: list[str]) -> tuple[bytes, bytes, int | None]:
    """Execute an FFmpeg command and return (stdout, stderr, returncode)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return stdout, stderr, proc.returncode


# ---------------------------------------------------------------------------
# Platform size presets
# ---------------------------------------------------------------------------

PLATFORM_SIZES: dict[str, tuple[int, int]] = {
    "youtube": (1280, 720),       # 16:9
    "instagram_square": (1080, 1080),   # 1:1
    "instagram_portrait": (1080, 1350), # 4:5
    "instagram_story": (1080, 1920),    # 9:16
    "tiktok": (1080, 1920),           # 9:16
    "twitter": (1600, 900),           # 16:9
}

DEFAULT_STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "commercial": {
        "font_color": (255, 255, 255),
        "shadow_color": (0, 0, 0),
        "font_size_ratio": 0.08,
        "overlay_alpha": 128,
        "gradient_top": (0, 0, 0),
        "gradient_bottom": (0, 0, 0, 0),
    },
    "minimal": {
        "font_color": (255, 255, 255),
        "shadow_color": (50, 50, 50),
        "font_size_ratio": 0.06,
        "overlay_alpha": 64,
        "gradient_top": (0, 0, 0),
        "gradient_bottom": (0, 0, 0, 0),
    },
    "bold": {
        "font_color": (255, 220, 50),
        "shadow_color": (0, 0, 0),
        "font_size_ratio": 0.10,
        "overlay_alpha": 180,
        "gradient_top": (0, 0, 0),
        "gradient_bottom": (0, 0, 0, 0),
    },
}


# ---------------------------------------------------------------------------
# Thumbnail generation
# ---------------------------------------------------------------------------

async def generate_thumbnails(
    video_path: Path,
    output_dir: Path,
    *,
    count: int = 5,
    style_preset: str = "commercial",
    text_overlay: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Generate platform-optimized thumbnails from video keyframes.

    Extracts evenly-spaced keyframes from the input video using FFmpeg,
    optionally applies a text overlay, resizes for common platforms,
    and writes the result to *output_dir*.

    Returns a summary dict with paths, dimensions, and metadata.
    """
    if not isinstance(video_path, Path):
        video_path = Path(video_path)
    if not isinstance(output_dir, Path):
        output_dir = Path(output_dir)

    if not video_path.exists():
        return {"error": f"Video file not found: {video_path}"}
    if not _ffmpeg_available():
        return {"error": "ffmpeg not found. Install FFmpeg first."}

    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Probe video duration
    # ------------------------------------------------------------------
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(video_path),
    ]
    stdout, stderr, rc = await _run_ffmpeg(probe_cmd)
    if rc != 0:
        return {"error": f"ffprobe failed: {stderr.decode()[:200]}"}

    probe_data = json.loads(stdout.decode())
    duration = float(probe_data.get("format", {}).get("duration", 0))
    if duration <= 0:
        return {"error": "Could not determine video duration."}

    # ------------------------------------------------------------------
    # 2. Determine frame timestamps
    # ------------------------------------------------------------------
    timestamps = [
        (duration / (count + 1)) * (i + 1)
        for i in range(count)
    ]

    # ------------------------------------------------------------------
    # 3. Extract keyframes via FFmpeg
    # ------------------------------------------------------------------
    extracted: list[Path] = []
    for i, ts in enumerate(timestamps):
        frame_path = output_dir / f"thumb_{i+1:03d}_raw.jpg"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(round(ts, 2)),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(frame_path),
        ]
        _, stderr, rc = await _run_ffmpeg(cmd)
        if rc != 0:
            # Retry without exact seek (grab nearest keyframe)
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-vf", "fps=1/10",
                "-vframes", "1",
                "-q:v", "2",
                str(frame_path),
            ]
            _, stderr, rc = await _run_ffmpeg(cmd)
            if rc != 0:
                return {"error": f"FFmpeg extraction failed: {stderr.decode()[:200]}"}
        if frame_path.exists():
            extracted.append(frame_path)

    if not extracted:
        return {"error": "No keyframes could be extracted from the video."}

    # ------------------------------------------------------------------
    # 4. Apply style preset + text overlay + resize per platform
    # ------------------------------------------------------------------
    preset_cfg = DEFAULT_STYLE_PRESETS.get(style_preset, DEFAULT_STYLE_PRESETS["commercial"])
    thumbnails: list[dict[str, Any]] = []

    for raw_frame in extracted:
        try:
            img = Image.open(raw_frame).convert("RGBA")
        except Exception:
            continue

        # Apply subtle gradient overlay from preset
        if preset_cfg.get("overlay_alpha", 0) > 0:
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            draw_overlay = ImageDraw.Draw(overlay)
            h = img.size[1]
            alpha = preset_cfg["overlay_alpha"]
            draw_overlay.rectangle(
                [(0, h // 2), (img.size[0], h)],
                fill=(0, 0, 0, alpha),
            )
            img = Image.alpha_composite(img, overlay)

        # Text overlay
        if text_overlay:
            img = _draw_text_overlay(img, text_overlay, preset_cfg)

        # Build platform variants
        entry: dict[str, Any] = {
            "path": str(raw_frame),
            "type": "raw",
            "width": img.width,
            "height": img.height,
        }
        thumbnails.append(entry)

        for platform, (pw, ph) in PLATFORM_SIZES.items():
            resized = img.resize((pw, ph), Image.Resampling.LANCZOS)
            out_path = output_dir / f"thumb_{platform}.jpg"
            resized.convert("RGB").save(out_path, "JPEG", quality=90)
            thumbnails.append({
                "path": str(out_path),
                "type": platform,
                "width": pw,
                "height": ph,
            })

        raw_frame.unlink(missing_ok=True)

    return {
        "video_path": str(video_path),
        "output_dir": str(output_dir),
        "thumbnails": thumbnails,
        "count": count,
        "style_preset": style_preset,
        "duration_seconds": duration,
    }


# ---------------------------------------------------------------------------
# Text overlay helper
# ---------------------------------------------------------------------------

def _draw_text_overlay(
    img: Image.Image,
    text: str,
    preset_cfg: dict[str, Any],
) -> Image.Image:
    """Draw centered bold text with shadow on an RGBA image."""
    draw = ImageDraw.Draw(img)
    fw = max(12, img.width // int(1.0 / preset_cfg.get("font_size_ratio", 0.08)))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fw)
    except OSError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", fw)
        except OSError:
            font = ImageFont.load_default()  # type: ignore[assignment]

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (img.width - text_w) // 2
    y = img.height - text_h - int(img.height * 0.12)

    shadow = preset_cfg.get("shadow_color", (0, 0, 0))
    color = preset_cfg.get("font_color", (255, 255, 255))

    # Shadow offset
    draw.text((x + 2, y + 2), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=color)
    return img
