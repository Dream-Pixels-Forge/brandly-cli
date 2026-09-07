"""Multi-language video dubbing using MiniMax TTS and FFmpeg."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from brandly_cli.utils import async_run_ffmpeg

# ---------------------------------------------------------------------------
# Language & voice mappings
# ---------------------------------------------------------------------------

LANGUAGES: dict[str, tuple[str, str]] = {
    "en": ("English", "English_Insightful_Speaker"),
    "es": ("Spanish", "Spanish_Energetic_Woman"),
    "fr": ("French", "French_Elegant_Woman"),
    "de": ("German", "German_Professional_Man"),
    "ja": ("Japanese", "Japanese_Gentle_Woman"),
    "ko": ("Korean", "Korean_Clear_Woman"),
    "zh": ("Chinese (Mandarin)", "Chinese_Mandarin_Lyrical_Voice"),
    "pt": ("Portuguese", "Portuguese_Brazilian_Woman"),
    "ar": ("Arabic", "Arabic_Professional_Man"),
    "hi": ("Hindi", "Hindi_Warm_Woman"),
}

VOICE_STYLES: dict[str, str] = {
    "professional": "professional",
    "casual": "casual",
    "friendly": "friendly",
    "energetic": "energetic",
    "calm": "calm",
}

MINIMAX_TTS_URL = os.getenv(
    "MINIMAX_TTS_URL",
    "https://api.minimax.io/v1/tts",
)


# ---------------------------------------------------------------------------
# FFmpeg availability helpers
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
# Internal helpers
# ---------------------------------------------------------------------------

def _get_duration(path: Path) -> float:
    """Return the duration of a media file in seconds using ffprobe."""
    if not _ffprobe_available():
        return 0.0
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
        if proc.returncode != 0:
            return 0.0
        data = json.loads(proc.stdout.decode())
        return float(data.get("format", {}).get("duration", 0.0))
    except (ValueError, TypeError, FileNotFoundError):
        return 0.0


def _resolve_output(video_path: Path, target_lang: str, root: Path | None) -> Path:
    """Determine the output video path."""
    if root:
        video_path = Path(root) / video_path
    stem = video_path.stem
    suffix = video_path.suffix or ".mp4"
    return video_path.parent / f"{stem}_{target_lang}{suffix}"


# ---------------------------------------------------------------------------
# MiniMax TTS stub
# ---------------------------------------------------------------------------

async def _generate_tts_audio(
    text: str,
    voice_id: str,
    output_path: Path,
) -> dict[str, Any]:
    """Generate TTS audio via MiniMax API (stub — no real API call).

    TODO: Implement real MiniMax TTS integration when the API endpoint is stable.
          Replace this stub with an actual httpx request to the MiniMax TTS service.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Stub: generate a silent audio file matching expected duration
    # In production this would call the MiniMax TTS API and stream the result
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=mono",
        "-t", "1.0",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        return {"error": stderr.decode()[:200]}
    return {
        "voice_id": voice_id,
        "text_length": len(text),
        "audio_path": str(output_path),
        "duration_seconds": _get_duration(output_path),
    }


# ---------------------------------------------------------------------------
# Core dubbing pipeline
# ---------------------------------------------------------------------------

async def dub_video(
    video_path: Path,
    source_lang: str,
    target_lang: str,
    *,
    voice_style: str = "professional",
    output_path: Path | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Dub a video to a target language while preserving timing.

    Pipeline:
        1. Extract audio from video using FFmpeg
        2. Transcribe / translate source audio to target language (TODO stub)
        3. Generate new TTS audio using MiniMax
        4. Replace the original audio track in the video

    Args:
        video_path: Path to the source video file.
        source_lang: ISO 639-1 code of the source language (e.g. "en").
        target_lang: ISO 639-1 code of the target language (e.g. "es").
        voice_style: Style preset for the voice — one of professional, casual,
            friendly, energetic, calm.
        output_path: Optional explicit output path. Defaults to
            ``<stem>_<target_lang><suffix>`` in the same directory.
        root: Optional project root used to resolve relative paths.

    Returns:
        Dict with keys: video_path, source_lang, target_lang, output_path,
        duration_seconds, voice_id.
        On failure returns ``{"error": <message>}``.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        return {"error": f"Input file not found: {video_path}"}
    if not _ffmpeg_available():
        return {"error": "ffmpeg not found. Install FFmpeg first."}
    if source_lang not in LANGUAGES:
        return {
            "error": (
                f"Unknown source language: {source_lang}. "
                f"Supported: {list(LANGUAGES.keys())}"
            )
        }
    if target_lang not in LANGUAGES:
        return {
            "error": (
                f"Unknown target language: {target_lang}. "
                f"Supported: {list(LANGUAGES.keys())}"
            )
        }
    if voice_style not in VOICE_STYLES:
        return {
            "error": (
                f"Unknown voice style: {voice_style}. "
                f"Supported: {list(VOICE_STYLES.keys())}"
            )
        }

    # Resolve output path
    if output_path is None:
        output_path = _resolve_output(video_path, target_lang, root)
    else:
        output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Stage 1: Extract audio from video
    extracted_audio = output_path.parent / f"_dub_audio_{video_path.stem}.wav"
    rc, stderr = await async_run_ffmpeg([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "1",
        str(extracted_audio),
    ])
    if rc != 0:
        return {"error": f"Audio extraction failed: {stderr[:300]}"}

    # Stage 2: Transcribe and translate (TODO stub)
    # TODO: Replace with real transcription (Whisper etc.) + translation pipeline.
    #       For now we assume the source transcript is provided externally or
    #       we use a placeholder text for testing.
    #       The transcription/translation step is intentionally left as a stub
    #       until the upstream speech-to-text service is integrated.
    translated_text = f"[dubbed_to_{target_lang}]"  # placeholder

    # Stage 3: Generate TTS audio via MiniMax
    voice_id = LANGUAGES[target_lang][1]
    tts_audio = output_path.parent / f"_dub_tts_{video_path.stem}.aac"
    tts_result = await _generate_tts_audio(translated_text, voice_id, tts_audio)
    if "error" in tts_result:
        extracted_audio.unlink(missing_ok=True)
        return {"error": f"TTS generation failed: {tts_result['error']}"}

    # Stage 4: Replace audio track in video
    duration = _get_duration(video_path)
    rc, stderr = await async_run_ffmpeg([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(tts_audio),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-t", str(duration),
        str(output_path),
    ])
    if rc != 0:
        extracted_audio.unlink(missing_ok=True)
        tts_audio.unlink(missing_ok=True)
        return {"error": f"Audio replacement failed: {stderr[:300]}"}

    # Cleanup intermediates
    extracted_audio.unlink(missing_ok=True)
    tts_audio.unlink(missing_ok=True)

    final_duration = _get_duration(output_path)
    return {
        "video_path": str(video_path),
        "source_lang": source_lang,
        "target_lang": target_lang,
        "output_path": str(output_path),
        "duration_seconds": final_duration,
        "voice_id": voice_id,
    }
