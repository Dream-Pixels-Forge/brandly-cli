"""Platform-optimized video exports for TikTok, Instagram, YouTube, etc."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

from brandly_cli.brand_kit import OverlaySpec
from brandly_cli.io import proc_output
from brandly_cli.stitch import probe_video_dims, ratio_crop_filter

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
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
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


def _build_base_cmd(
    input_video: Path,
    output_path: Path,
    duration: float,
    filter_parts: list[str],
) -> list[str]:
    """The stock ffmpeg command (G4 semantics; unchanged behaviour)."""
    cmd = ["ffmpeg", "-y", "-i", str(input_video)]
    if filter_parts:
        cmd += ["-vf", ",".join(filter_parts)]
    cmd += [
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    return cmd


def brand_overlay_position(width: int, height: int, spec) -> tuple[str, str]:
    """Deterministic (x, y) overlay expressions for a logo (G7 PR 2).

    The margin is ``safe_zone`` of the side length per axis; the logo's own
    size enters as ffmpeg's ``w``/``h`` overlay expressions so placement
    stays correct for any logo aspect ratio.
    """
    mx = int(round(spec.safe_zone * width))
    my = int(round(spec.safe_zone * height))
    if spec.corner == "top-left":
        return str(mx), str(my)
    if spec.corner == "top-right":
        return f"W-w-{mx}", str(my)
    if spec.corner == "bottom-left":
        return str(mx), f"H-h-{my}"
    return f"W-w-{mx}", f"H-h-{my}"  # bottom-right (default)


def build_export_cmd(
    input_video: Path,
    output_path: Path,
    duration: float,
    filter_parts: list[str],
    brand_logo: Path | None,
    brand_overlay,
    target_dims: tuple[int, int] | None,
) -> list[str]:
    """FFmpeg command for an export, optionally with the brand logo overlay.

    Without a logo the command is byte-identical to the pre-G7 behaviour
    (``-vf`` pipeline). With a logo the pipeline switches to
    ``-filter_complex``: main chain → logo scale (10% of output height) →
    optional opacity → corner overlay, with audio remapped from input 0.
    """
    if not brand_logo:
        return _build_base_cmd(input_video, output_path, duration, filter_parts)

    w, h = target_dims or (1920, 1080)
    logo_h = int(round(0.1 * h))
    logo_chain = [f"scale=-2:{logo_h}"]
    if brand_overlay is not None and brand_overlay.opacity < 1.0:
        logo_chain.append("format=rgba")
        logo_chain.append(f"colorchannelmixer=aa={brand_overlay.opacity}")
    main_chain = ",".join(filter_parts) if filter_parts else "null"
    x, y = brand_overlay_position(w, h, brand_overlay or OverlaySpec())
    filter_complex = (
        f"[0:v]{main_chain}[vmain];"
        f"[1:v]{','.join(logo_chain)}[vlogo];"
        f"[vmain][vlogo]overlay={x}:{y}[vout]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-i",
        str(brand_logo),
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "0:a?",
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    return cmd


async def export_for_platform(
    input_video: Path,
    platform: str,
    output_dir: Path,
    *,
    add_captions: bool = True,
    captions_text: str | None = None,
    root: Path | None = None,
    fit: str = "crop",
    brand_logo: str | None = None,
    brand_overlay: OverlaySpec | None = None,
) -> dict[str, Any]:
    """Export video optimized for a specific platform.

    Args:
        input_video: Path to the source video.
        platform: Platform name (e.g., "tiktok", "instagram_reel", "youtube_standard").
        output_dir: Directory to write exported video.
        add_captions: Whether to add text overlay captions.
        captions_text: Text to overlay (if any).
        root: Optional project root for relative paths.
        fit: G4 ratio semantics — ``"crop"`` (default; center-crop to the
            platform ratio at source scale, no bars) or ``"pad"`` (letterbox
            to the platform's standard resolution with black bars).
        brand_logo: G7 PR 2 — optional brand mark file to composite onto the
            export (``export-platforms --brand`` passes the kit's logo).
        brand_overlay: G7 PR 2 — the kit's overlay spec (corner / safe-zone
            / opacity). Ignored unless ``brand_logo`` is given.

    Returns:
        Dict with platform, output_path, duration_seconds, file_size_bytes, captions_added.
        On failure, returns {"error": <message>}.
    """
    input_video = Path(input_video)
    output_dir = Path(output_dir)
    crop_filter = None
    src_dims = None

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

    # G4 ratio policy: reuse the shared stitch filter builders — crop for
    # feed aspects by default, pad (letterbox) only when explicitly requested.
    target_ratio = preset["ratio"]
    if fit not in ("crop", "pad"):
        return {"error": f"Unknown fit mode: {fit}. Choose from crop, pad."}

    filter_parts: list[str] = []
    if fit == "crop":
        # Center-crop to the platform ratio at source scale. A no-op when the
        # source already matches the ratio (the stitch -> export pipeline
        # never double-crops).
        src_dims = probe_video_dims(input_video)
        if src_dims is None:
            return {"error": f"Could not probe dimensions of {input_video}"}
        crop_filter = ratio_crop_filter(src_dims[0], src_dims[1], target_ratio)
        if crop_filter:
            filter_parts.append(crop_filter)
    else:
        # pad: scale to the platform's standard resolution, black bars.
        ratio_to_dims: dict[str, tuple[int, int]] = {
            "9:16": (1080, 1920),
            "4:5": (1080, 1350),
            "1:1": (1080, 1080),
            "16:9": (1920, 1080),
            "4:3": (1080, 810),
        }
        target_w, target_h = ratio_to_dims.get(target_ratio, (1920, 1080))
        scale_filter = f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease"
        filter_parts.append(scale_filter)
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

    # G7 PR 2: brand logo overlay (fail-closed — a missing logo file
    # aborts the export instead of silently dropping the lock).
    if brand_logo:
        logo_path = Path(brand_logo)
        if not logo_path.is_file():
            return {"error": f"brand logo not found: {brand_logo}"}
    else:
        logo_path = None

    # Final frame dimensions the overlay math runs against.
    target_dims: tuple[int, int] | None = None
    if fit == "pad":
        target_dims = ratio_to_dims.get(target_ratio, (1920, 1080))
    elif crop_filter:
        import re as _re

        m = _re.match(r"crop=(\d+):(\d+)", crop_filter)
        if m:
            target_dims = (int(m.group(1)), int(m.group(2)))
        else:
            target_dims = src_dims

    # Build FFmpeg command (no -vf at all when there are no filters)
    cmd = build_export_cmd(
        input_video,
        output_path,
        min(source_duration, max_duration),
        filter_parts,
        logo_path,
        brand_overlay,
        target_dims,
    )

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
        "fit": fit,
        "duration_seconds": final_duration,
        "file_size_bytes": file_size,
        "captions_added": add_captions and bool(captions_text),
    }
