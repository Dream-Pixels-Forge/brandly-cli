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


def _parse_aspect(text: str) -> float | None:
    """Parse ``W:H`` (ints or decimals, e.g. ``16:9``, ``2.39:1``) to W/H.

    Returns ``None`` for anything that is not two positive numbers — the
    caller fails closed with a clear message instead of building a broken
    ffmpeg filter (issue #123).
    """
    try:
        left, right = text.split(":", 1)
        w = float(left.strip())
        h = float(right.strip())
    except ValueError:
        return None
    if w <= 0 or h <= 0:
        return None
    return w / h


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
    if aspect is not None:
        # Issue #123: parse arbitrary W:H ratios (2.39:1, 16:9, ...) and
        # center-crop to the target ratio at source scale (the G4 ratio
        # policy), then optionally scale to explicit dimensions.
        ratio = _parse_aspect(aspect)
        if ratio is None:
            return {"error": f"Invalid aspect ratio {aspect!r} - use W:H like 16:9 or 2.39:1"}
        vf = f"crop=w='min(iw,ih*{ratio})':h='min(ih,iw/{ratio})'"
        if width and height:
            vf += f",scale={width}:{height}"
        elif width:
            vf += f",scale={width}:-2"
        elif height:
            vf += f",scale=-2:{height}"
        cmd += ["-vf", vf]
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


async def mux_audio(
    input_path: str | Path,
    audio_paths: list[str | Path],
    output_path: str | Path,
    *,
    mode: str = "duck",
    duck_threshold: float = 0.05,
    duck_ratio: float = 8.0,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
    offset: float = 0.0,
    audio_gain: float = 1.0,
    codec: str = "libx264",
) -> dict[str, Any]:
    """Mix one or more audio tracks into a video (issue #119).

    Modes:
      * ``replace`` — the added audio(s) replace any audio the video carries
      * ``mix``     — the added audio(s) are summed with the video's own audio
      * ``duck``    — the added bed is sidechain-compressed under the video's
        own audio (VO/ambient), so music swells in the silent parts

    The added inputs are first mixed into a single ``[bed]`` (per-input gain,
        fade-in, tail fade via areverse trick, and delay/offset). Videos with
    no audio stream fall back to replace semantics in every mode.

    Fail-closed: missing files, invalid mode, or non-positive gains/offsets
    return ``{"error": ...}`` without touching ffmpeg.
    """
    inp = Path(input_path)
    audios = [Path(a) for a in audio_paths]
    out = Path(output_path)
    if not inp.exists():
        return {"error": f"Input file not found: {inp}"}
    missing = [str(a) for a in audios if not a.exists()]
    if missing:
        return {"error": f"Audio file not found: {', '.join(missing)}"}
    if not audios:
        return {"error": "At least one audio input is required"}
    if mode not in ("replace", "mix", "duck"):
        return {"error": f"Invalid mode {mode!r} - use replace, mix or duck"}
    if not 0 < duck_threshold <= 1:
        return {"error": "duck_threshold must be in (0, 1]"}
    if duck_ratio < 1:
        return {"error": "duck_ratio must be >= 1"}
    if fade_in < 0 or fade_out < 0 or offset < 0:
        return {"error": "fade_in, fade_out and offset must be >= 0"}
    if audio_gain <= 0:
        return {"error": "audio_gain must be > 0"}
    if not _ffmpeg_available():
        return {"error": "ffmpeg not found. Install FFmpeg first."}

    # Does the video already carry audio (VO / ambient)?
    info = await get_video_info(inp)
    video_has_audio = bool(info.get("has_audio"))

    # --- build the audio bed: one branch per added input ------------------
    parts: list[str] = []
    labels: list[str] = []
    for idx, _audio in enumerate(audios):
        chain: list[str] = []
        if audio_gain != 1.0:
            chain.append(f"volume={audio_gain:g}")
        if offset > 0:
            chain.append(f"adelay={int(offset * 1000)}")
        if fade_in > 0:
            chain.append(f"afade=t=in:st=0:d={fade_in:g}")
        if fade_out > 0:
            # areverse/afade/areverse = tail fade without probing the duration
            chain.append(f"areverse,afade=t=in:st=0:d={fade_out:g},areverse")
        label = f"a{idx + 1}"
        joined = ",".join(chain) if chain else "anull"
        parts.append(f"[{idx + 1}:a]{joined}[{label}]")
        labels.append(f"[{label}]")

    if len(labels) > 1:
        parts.append(
            "".join(labels)
            + f"amix=inputs={len(labels)}:duration=longest:normalize=0[bed]"
        )
    else:
        parts.append(f"{labels[0]}anull[bed]")

    # --- combine the bed with the video's own audio per mode --------------
    maps: list[str] = ["0:v"]
    tail: list[str] = []
    if mode == "replace" or not video_has_audio:
        maps.append("[bed]")
        tail = ["-shortest"]
    elif mode == "mix":
        parts.append("[0:a][bed]amix=inputs=2:duration=first:normalize=0[aout]")
        maps.append("[aout]")
    else:  # duck
        parts.append(
            f"[bed][0:a]sidechaincompress=threshold={duck_threshold:g}"
            f":ratio={duck_ratio:g}:attack=50:release=400[ducked]"
        )
        parts.append("[0:a][ducked]amix=inputs=2:duration=first:normalize=0[aout]")
        maps.append("[aout]")

    cmd: list[str] = ["ffmpeg", "-y", "-i", str(inp)]
    for a in audios:
        cmd += ["-i", str(a)]
    cmd += ["-filter_complex", ";".join(parts)]
    for m in maps:
        cmd += ["-map", m]
    cmd += ["-c:v", codec, "-c:a", "aac", "-b:a", "192k", *tail, str(out)]

    out.parent.mkdir(parents=True, exist_ok=True)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        return {"error": proc_output(stderr)[:500]}
    info = await get_video_info(out)
    info["action"] = "mux"
    info["mode"] = mode
    return info
