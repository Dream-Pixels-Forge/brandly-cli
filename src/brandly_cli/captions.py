"""Caption and subtitle generation for generated videos."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def split_into_captions(
    text: str,
    *,
    max_chars: int = 40,
    max_lines: int = 2,
) -> list[dict[str, Any]]:
    """Split a text into caption chunks suitable for video subtitles.

    Returns a list of dicts with 'text', 'start', 'end' keys.
    Timing is approximate based on reading speed (characters per second).
    """
    words = text.split()
    if not words:
        return []

    chunks: list[list[str]] = []
    current_chunk: list[str] = []
    current_len = 0

    for word in words:
        word_len = len(word) + 1  # +1 for space
        if current_len + word_len > max_chars and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [word]
            current_len = word_len
        else:
            current_chunk.append(word)
            current_len += word_len

    if current_chunk:
        chunks.append(current_chunk)

    # Merge short chunks to respect max_lines
    merged: list[list[str]] = []
    for chunk in chunks:
        if merged and len(merged[-1]) + len(chunk) <= max_lines:
            merged[-1].extend(chunk)
        else:
            merged.append(chunk)

    # Estimate timing: ~4 chars/sec reading speed
    cps = 4.0
    captions = []
    t = 0.0
    for line_group in merged:
        line_text = " ".join(line_group)
        duration = max(0.5, len(line_text) / cps)
        captions.append({
            "text": line_text,
            "start": round(t, 1),
            "end": round(t + duration, 1),
        })
        t += duration

    return captions


def generate_srt(captions: list[dict[str, Any]], index_start: int = 1) -> str:
    """Convert caption dicts to SRT format string."""

    def format_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    lines = []
    for i, cap in enumerate(captions, start=index_start):
        lines.append(str(i))
        lines.append(f"{format_time(cap['start'])} --> {format_time(cap['end'])}")
        lines.append(cap["text"])
        lines.append("")

    return "\n".join(lines)


def generate_vtt(captions: list[dict[str, Any]], index_start: int = 1) -> str:
    """Convert caption dicts to WebVTT format string."""

    def format_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    lines = ["WEBVTT", ""]
    for _i, cap in enumerate(captions, start=index_start):
        lines.append(f"{format_time(cap['start'])} --> {format_time(cap['end'])}")
        lines.append(cap["text"])
        lines.append("")

    return "\n".join(lines)


def generate_cc_xml(captions: list[dict[str, Any]], index_start: int = 1) -> str:
    """Convert caption dicts to Closed Captions XML format."""
    parts = ['<?xml version="1.0" encoding="UTF-8"?>\n<captions>']
    for cap in captions:
        safe_text = re.sub(
            r"[<>&\"]",
            lambda m: {"<": "&lt;", ">": "&gt;", "&": "&amp;", "\"": "&quot;"}[m.group()],
            cap["text"],
        )
        parts.append(
            f'  <caption begin="{cap["start"]:.3f}" end="{cap["end"]:.3f}">{safe_text}</caption>'
        )
    parts.append("</captions>")
    return "\n".join(parts)


def auto_capitalize(text: str) -> str:
    """Capitalize the first letter of each sentence for caption readability."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(s.capitalize() if s else s for s in sentences)


def build_captions_for_prompt(
    prompt: str,
    *,
    max_chars: int = 35,
    style: str = "bold",
) -> list[dict[str, Any]]:
    """Build caption segments from a video generation prompt.

    Extracts key phrases and creates timed captions.
    """
    # Clean up the prompt
    line_list = [line.strip() for line in prompt.split("\n")
                 if line.strip() and not line.startswith("#")]
    # Filter to meaningful lines
    meaningful = [
        line for line in line_list
        if len(line) > 5 and not line.startswith("SHOT")
        and not line.startswith("Duration")
    ]

    if not meaningful:
        meaningful = [prompt[:200]]

    captions = []
    cps = 3.5
    t = 0.0
    for line in meaningful[:8]:  # Limit to 8 caption segments
        # Wrap long lines
        words = line.split()
        segments: list[str] = []
        current = ""
        for w in words:
            if len(current) + len(w) + 1 > max_chars and current:
                segments.append(current)
                current = w
            else:
                current = f"{current} {w}".strip()
        if current:
            segments.append(current)

        for seg in segments:
            duration = max(0.8, len(seg) / cps)
            captions.append({
                "text": auto_capitalize(seg),
                "start": round(t, 1),
                "end": round(t + duration, 1),
                "style": style,
            })
            t += duration

    return captions


def export_captions(
    captions: list[dict[str, Any]],
    output_dir: Path,
    *,
    basename: str = "captions",
) -> dict[str, Path]:
    """Export captions in multiple formats to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for fmt, generator in [
        ("srt", generate_srt),
        ("vtt", generate_vtt),
        ("cc.xml", generate_cc_xml),
    ]:
        path = output_dir / f"{basename}.{fmt}"
        path.write_text(generator(captions), encoding="utf-8")
        paths[fmt] = path
    return paths
