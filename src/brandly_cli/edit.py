"""Video editing utilities — trim, crop, resize, concatenate, speed."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

from brandly_cli.io import proc_output


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


async def get_video_info(input_path: str | Path) -> dict[str, Any]:
    """Extract video metadata using ffprobe."""
    path = Path(input_path)
    if not path.exists():
        return {"error": f"File not found: {path}"}
    if not _ffprobe_available():
        return {"error": "ffprobe not found. Install FFmpeg first."}

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            return {"error": proc_output(stderr)[:200]}
        data = json.loads(proc_output(stdout))
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        video_stream: dict[str, Any] = next(
            (s for s in streams if s.get("codec_type") == "video"), {}
        )
        audio_stream: dict[str, Any] = next(
            (s for s in streams if s.get("codec_type") == "audio"), {}
        )
        return {
            "file": str(path),
            "duration_seconds": float(fmt.get("duration", 0)),
            "size_bytes": int(fmt.get("size", 0)),
            "bitrate_bps": int(fmt.get("bit_rate", 0)),
            "format": fmt.get("format_long_name", fmt.get("format_name", "")),
            "video_codec": video_stream.get("codec_name", ""),
            "video_width": video_stream.get("width", 0),
            "video_height": video_stream.get("height", 0),
            "video_aspect": video_stream.get("display_aspect_ratio", ""),
            "video_fps": video_stream.get("r_frame_rate", ""),
            "audio_codec": audio_stream.get("codec_name", ""),
            "audio_sample_rate": audio_stream.get("sample_rate", ""),
            "has_audio": bool(audio_stream),
        }
    except Exception as e:
        return {"error": str(e)}


async def trim_video(
    input_path: str | Path,
    output_path: str | Path,
    *,
    start: float = 0.0,
    end: float | None = None,
    duration: float | None = None,
    codec: str = "libx264",
    preset: str = "fast",
) -> dict[str, Any]:
    """Trim a video to a segment. Returns info about the output."""
    inp = Path(input_path)
    out = Path(output_path)
    if not inp.exists():
        return {"error": f"Input file not found: {inp}"}
    if not _ffmpeg_available():
        return {"error": "ffmpeg not found. Install FFmpeg first."}

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-i", str(inp)]
    if start > 0:
        cmd += ["-ss", str(start)]
    if duration is not None:
        cmd += ["-t", str(duration)]
    elif end is not None:
        cmd += ["-to", str(end)]
    cmd += [
        "-c:v", codec,
        "-preset", preset,
        "-c:a", "aac", "-b:a", "128k",
        str(out),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        return {"error": proc_output(stderr)[:500]}
    info = await get_video_info(out)
    info["action"] = "trim"
    return info


async def resize_video(
    input_path: str | Path,
    output_path: str | Path,
    *,
    width: int | None = None,
    height: int | None = None,
    aspect: str | None = None,
    codec: str = "libx264",
) -> dict[str, Any]:
    """Resize a video to given dimensions or aspect ratio."""
    inp = Path(input_path)
    out = Path(output_path)
    if not inp.exists():
        return {"error": f"Input file not found: {inp}"}
    if not _ffmpeg_available():
        return {"error": "ffmpeg not found. Install FFmpeg first."}

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-i", str(inp)]
    if aspect:
        # Parse common aspect ratios
        cmd += [
            "-vf",
            f"scale='if(gt(iw,ih),{-width if width else -1}:"
            f"{-height if height else -1})':"
            f"'if(gt(iw,ih),{-width if width else -1}:"
            f"{-height if height else -1}'",
        ]
    elif width and height:
        cmd += ["-vf", f"scale={width}:{height}"]
    elif width:
        cmd += ["-vf", f"scale={width}:-1"]
    elif height:
        cmd += ["-vf", f"scale=-1:{height}"]
    cmd += ["-c:v", codec, "-c:a", "copy", str(out)]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        return {"error": proc_output(stderr)[:500]}
    info = await get_video_info(out)
    info["action"] = "resize"
    return info


async def concatenate_videos(
    input_paths: list[str | Path],
    output_path: str | Path,
    *,
    codec: str = "libx264",
    safe: bool = True,
) -> dict[str, Any]:
    """Concatenate multiple videos into one. Uses concat demuxer or filter."""
    if len(input_paths) < 2:
        return {"error": "Need at least 2 input videos to concatenate."}
    if not _ffmpeg_available():
        return {"error": "ffmpeg not found. Install FFmpeg first."}

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    inputs = [Path(p) for p in input_paths]
    missing = [p for p in inputs if not p.exists()]
    if missing:
        return {"error": f"Missing files: {', '.join(str(p) for p in missing)}"}

    list_file = out.parent / f"_concat_{out.name}.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in inputs),
        encoding="utf-8",
    )
    try:
        if safe:
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(list_file),
                "-c:v", codec,
                "-c:a", "aac", "-b:a", "128k",
                str(out),
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(inputs[0]),
                "-i", str(inputs[1]),
                "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]",
                "-map", "[v]", "-map", "[a]",
                "-c:v", codec,
                "-c:a", "aac", "-b:a", "128k",
                str(out),
            ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            return {"error": proc_output(stderr)[:500]}
        info = await get_video_info(out)
        info["action"] = "concat"
        info["input_count"] = len(inputs)
        return info
    finally:
        list_file.unlink(missing_ok=True)


async def extract_audio(
    input_path: str | Path,
    output_path: str | Path,
    *,
    format: str = "mp3",
    bitrate: str = "192k",
) -> dict[str, Any]:
    """Extract audio track from a video file."""
    inp = Path(input_path)
    out = Path(output_path)
    if not inp.exists():
        return {"error": f"Input file not found: {inp}"}
    if not _ffmpeg_available():
        return {"error": "ffmpeg not found. Install FFmpeg first."}

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(inp),
        "-vn",
        "-acodec", "libmp3lame" if format == "mp3" else "copy",
        "-b:a", bitrate,
        str(out),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        return {"error": proc_output(stderr)[:500]}
    size = out.stat().st_size if out.exists() else 0
    return {
        "action": "extract_audio",
        "output": str(out),
        "size_bytes": size,
        "format": format,
        "bitrate": bitrate,
    }


async def add_subtitles(
    input_path: str | Path,
    output_path: str | Path,
    subtitle_text: str,
    *,
    font_size: int = 24,
    font_color: str = "white",
    position: str = "bottom",
    codec: str = "libx264",
) -> dict[str, Any]:
    """Burn subtitles into video using ASS format."""
    inp = Path(input_path)
    out = Path(output_path)
    if not inp.exists():
        return {"error": f"Input file not found: {inp}"}
    if not _ffmpeg_available():
        return {"error": "ffmpeg not found. Install FFmpeg first."}

    out.parent.mkdir(parents=True, exist_ok=True)
    # Build ASS subtitle file
    ass_dir = out.parent / ".ass_tmp"
    ass_dir.mkdir(exist_ok=True)
    ass_file = ass_dir / "subs.ass"
    y_pos = {"top": "10%", "middle": "50%", "bottom": "85%"}.get(position, "85%")
    style_format_line = (
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding"
    )
    style_line = (
        f"Style: Default,{font_color}, {font_size}, &H00FFFFFF, &H000000FF, "
        f"&H00000000, &H80000000, 0, 0, 0, 0, 100, 100, 0, 0, 1, 2, 1, 2, "
        f"20, 20, {y_pos.replace('%', '') * 10}, 1"
    )
    ass_content = f"""\
[Script Info]
Title: Brandly Subtitles
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
{style_format_line}
{style_line}

[Events]
Format: Layer, Start, End, Style, Text
Dialogue: 0,0:00:00.00,0:10:00.00,Default,{subtitle_text}
"""
    ass_file.write_text(ass_content, encoding="utf-8")
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(inp),
            "-vf", f"ass={ass_file.as_posix()}",
            "-c:v", codec,
            "-c:a", "copy",
            str(out),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            return {"error": proc_output(stderr)[:500]}
        info = await get_video_info(out)
        info["action"] = "subtitles"
        return info
    finally:
        import shutil
        shutil.rmtree(ass_dir, ignore_errors=True)


async def change_speed(
    input_path: str | Path,
    output_path: str | Path,
    speed: float,
    *,
    codec: str = "libx264",
) -> dict[str, Any]:
    """Change video playback speed (0.5 = half, 2.0 = double)."""
    inp = Path(input_path)
    out = Path(output_path)
    if not inp.exists():
        return {"error": f"Input file not found: {inp}"}
    if not _ffmpeg_available():
        return {"error": "ffmpeg not found. Install FFmpeg first."}

    out.parent.mkdir(parents=True, exist_ok=True)
    if speed >= 0.5 and speed <= 2.0:
        cmd = [
            "ffmpeg", "-y", "-i", str(inp),
            "-filter:v", f"setpts={1.0 / speed}*PTS",
            "-filter:a", f"atempo={speed}",
            "-c:v", codec,
            "-c:a", "aac", "-b:a", "128k",
            str(out),
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", str(inp),
            "-filter:v", f"setpts={1.0 / speed}*PTS",
            "-filter:a", f"atempo={min(max(speed, 0.5), 2.0)}",
            "-c:v", codec,
            "-c:a", "aac", "-b:a", "128k",
            str(out),
        ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        return {"error": proc_output(stderr)[:500]}
    info = await get_video_info(out)
    info["action"] = "speed"
    info["speed"] = speed
    return info
