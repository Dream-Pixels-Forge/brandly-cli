"""Multi-shot video assembly — concatenate clips with transitions and color grading."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# FFmpeg availability helpers (mirrors edit.py conventions)
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


# ---------------------------------------------------------------------------
# Transitions & color grades
# ---------------------------------------------------------------------------

TRANSITIONS = ("fade", "dissolve", "wipe", "slide")

COLOR_GRADES: dict[str, str] = {
    "cinematic": "eq=brightness=0.02:contrast=1.1:saturation=1.2",
    "warm": "colorbalance=rs=0.05:gs=0.02:bs=-0.02",
    "cool": "colorbalance=rs=-0.02:gs=-0.01:bs=0.05",
    "desaturated": "eq=saturation=0.5",
    "none": "",
}


def get_clip_duration(path: Path) -> float:
    """Return the duration of a clip in seconds using ffprobe."""
    if not _ffprobe_available():
        return 0.0
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=30)
    if proc.returncode != 0:
        return 0.0
    try:
        data = json.loads(proc.stdout.decode())
        return float(data.get("format", {}).get("duration", 0.0))
    except (ValueError, TypeError):
        return 0.0


# ---------------------------------------------------------------------------
# Core stitch
# ---------------------------------------------------------------------------

async def stitch_videos(
    clips: list[Path],
    output: Path,
    *,
    transition: str = "fade",
    transition_duration: float = 0.5,
    color_grade: str = "cinematic",
    root: Path | None = None,
) -> dict[str, Any]:
    """Concatenate video clips with transitions and color grading.

    Args:
        clips: Ordered list of input video paths.
        output: Destination file path.
        transition: One of fade | dissolve | wipe | slide.
        transition_duration: Duration of each transition in seconds.
        color_grade: One of cinematic | warm | cool | desaturated | none.
        root: Optional project root (used for resolving relative outputs).

    Returns:
        Dict with output metadata, or an ``{"error": ...}`` dict on failure.
    """
    clips = [Path(c) for c in clips]
    output = Path(output)

    # --- validation ---------------------------------------------------------
    for clip in clips:
        if not clip.exists():
            return {"error": f"Input file not found: {clip}"}
    if not clips:
        return {"error": "No clips provided."}
    if not _ffmpeg_available():
        return {"error": "ffmpeg not found. Install FFmpeg first."}
    if transition not in TRANSITIONS:
        return {"error": f"Unknown transition: {transition}. Choose from {TRANSITIONS}."}
    if color_grade not in COLOR_GRADES:
        return {"error": f"Unknown color grade: {color_grade}. Choose from {list(COLOR_GRADES)}."}

    output.parent.mkdir(parents=True, exist_ok=True)

    # --- single clip: pass-through ------------------------------------------
    if len(clips) == 1:
        grade_filter = COLOR_GRADES.get(color_grade, "")
        # grade_filter applied in cmd
        cmd = [
            "ffmpeg", "-y", "-i", str(clips[0]),
            "-vf", grade_filter if grade_filter else "null",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            str(output),
        ]
        rc, stderr = await _run(cmd)
        if rc != 0:
            return {"error": stderr[:500]}
        return _result(output, clips, [], color_grade)

    # --- multi-clip: simple concat -------------------------------------------
    # Write concat file
    concat_file = output.parent / f"_concat_{output.name}.txt"
    concat_lines = []
    durations: list[float] = []
    for c in clips:
        d = get_clip_duration(c) or 1.0
        durations.append(d)
        concat_lines.append(f"file '{c.resolve()}'")
        concat_lines.append(f"duration {d}")
    concat_lines.append("file ''")  # final empty line
    concat_file.write_text("\n".join(concat_lines), encoding="utf-8")

    # Build filter complex for crossfade transitions
    grade_filter = COLOR_GRADES.get(color_grade, "")
    inputs = []
    for c in clips:
        inputs += ["-i", str(c)]

    # Use xfade for video and acrossfade for audio
    n = len(clips)
    offsets: list[float] = []
    offset = durations[0] - transition_duration
    for i in range(n - 1):
        offsets.append(max(offset, 0.1))
        offset += durations[i + 1] - transition_duration

    # Build video filter chain
    vf_chain = "[0:v]"
    for i in range(1, n):
        offset_val = offsets[i - 1]
        vf_chain += (
            f"[{i}:v]xfade=transition={transition}"
            f":duration={transition_duration}"
            f":offset={offset_val}"
        )
        if i < n - 1:
            vf_chain += f"[v{i}];"
        else:
            vf_chain += "[vout];"

    if grade_filter:
        vf_chain += f"[vout]{grade_filter}[final_v]"
    else:
        vf_chain += "[vout]"

    # Build audio filter chain with acrossfade
    af_chain = "[0:a]"
    for i in range(1, n):
        af_chain += f"[{i}:a]acrossfade=d={transition_duration}:c1=tri:c2=tri"
        if i < n - 1:
            af_chain += f"[a{i}];"
        else:
            af_chain += "[aout]"

    filter_complex = f"{vf_chain};{af_chain}"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[final_v]" if grade_filter else "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(output),
    ]

    rc, stderr = await _run(cmd)
    concat_file.unlink(missing_ok=True)

    if rc != 0:
        return {"error": stderr[:500]}

    transitions_applied = [transition] * (n - 1)
    return _result(output, clips, transitions_applied, color_grade)


async def _run(cmd: list[str]) -> tuple[int, str]:
    """Run an FFmpeg command, returning (returncode, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    return proc.returncode, stderr.decode()


def _result(
    output: Path,
    clips: list[Path],
    transitions_applied: list[str],
    color_grade: str,
) -> dict[str, Any]:
    """Build the standardized result dict."""
    size = output.stat().st_size if output.exists() else 0
    duration = get_clip_duration(output)
    return {
        "output_path": str(output),
        "duration_seconds": duration,
        "size_bytes": size,
        "transitions_applied": transitions_applied,
        "color_grade": color_grade,
        "clips_count": len(clips),
    }
