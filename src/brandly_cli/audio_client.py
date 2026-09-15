"""Audio generation client for MiniMax Audio (music + TTS)."""

from __future__ import annotations

import os
from typing import Any

import httpx

MINIMAX_BASE_URL = os.getenv(
    "MINIMAX_BASE_URL",
    "https://api.minimax.io/v1",
)

# Default TTS model and voice IDs
TTS_MODELS = ["speech-2.8-hd", "speech-2.8-turbo", "speech-2.6-hd", "speech-2.6-turbo"]
DEFAULT_TTS_MODEL = "speech-2.8-hd"

# Common voice IDs (male / female / multilingual)
DEFAULT_VOICES: dict[str, str] = {
    "english_male": "English_Persuasive_Man",
    "english_female": "English_Insightful_Speaker",
    "chinese_female": "Chinese (Mandarin)_Lyrical_Voice",
    "cantonese_female": "Cantonese_GentleLady",
    "japanese_female": "Japanese_Whisper_Belle",
}

# Music generation models
MUSIC_MODELS = ["music-3.0", "music-2.6", "music-cover"]
DEFAULT_MUSIC_MODEL = "music-3.0"


def _get_api_key() -> str:
    key = os.getenv("MINIMAX_API_KEY")
    if not key:
        raise OSError(
            "MINIMAX_API_KEY environment variable is not set. "
            "Get your API key from https://platform.minimaxi.com and set it:\n"
            "  export MINIMAX_API_KEY=your_key"
        )
    return key


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Text-to-Speech
# ---------------------------------------------------------------------------


async def generate_tts(
    text: str,
    *,
    model: str = DEFAULT_TTS_MODEL,
    voice_id: str = "English_Insightful_Speaker",
    output_format: str = "url",
    speed: float = 1.0,
    vol: float = 1.0,
    pitch: int = 0,
    emotion: str | None = None,
) -> dict[str, Any]:
    """Generate voiceover via MiniMax TTS. Returns {url, duration_ms, model, voice_id}.

    Args:
        text: Text to synthesise. Supports inline tags like (laughs), (sighs)
            and pause markers.
        model: TTS model — speech-2.8-hd / speech-2.8-turbo /
            speech-2.6-hd / speech-2.6-turbo.
        voice_id: Voice preset (e.g. English_Insightful_Speaker).
        output_format: "url" or "hex".
        speed: Speech rate (0.5-2.0).
        vol: Volume (0.1-2.0).
        pitch: Pitch shift in semitones (-12 to 12).
        emotion: Optional emotion tag — "happy", "sad", "angry", "fearful",
            "neutral" (speech 2.6 / 2.8 only).
    """
    body: dict[str, Any] = {
        "model": model,
        "text": text,
        "stream": False,
        "output_format": output_format,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": speed,
            "vol": vol,
            "pitch": pitch,
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
    }
    if emotion is not None:
        body["voice_setting"]["emotion"] = emotion
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{MINIMAX_BASE_URL}/t2a_v2",
            headers=_headers(),
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    # output_format=url → data.audio is a URL; hex → save from data.audio hex string
    audio_data = data.get("data", {}).get("audio", "") if isinstance(data.get("data"), dict) else ""
    if not audio_data:
        audio_data = data.get("audio", "")

    return {
        "url": audio_data if output_format == "url" else None,
        "hex": audio_data if output_format == "hex" and audio_data else None,
        "model": model,
        "voice_id": voice_id,
    }


# ---------------------------------------------------------------------------
# Music Generation
# ---------------------------------------------------------------------------


async def generate_music(
    prompt: str,
    *,
    model: str = DEFAULT_MUSIC_MODEL,
    duration_seconds: int = 30,
    instrumental: bool = True,
    lyrics: str | None = None,
    sample_rate: int = 44100,
    bitrate: int = 256000,
    format: str = "mp3",
) -> dict[str, Any]:
    """Generate background music via MiniMax. Returns {url, duration_ms, model}.

    Note: As of August 2026, paid music-generation APIs may require existing
    account balance. Use music-3.0 (or fall back to music-2.6) when available.
    """
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "output_format": "url",
        "is_instrumental": instrumental,
        "audio_setting": {
            "sample_rate": sample_rate,
            "bitrate": bitrate,
            "format": format,
        },
    }
    if lyrics:
        body["lyrics"] = lyrics

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{MINIMAX_BASE_URL}/music_generation",
            headers=_headers(),
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    audio_data = data.get("data", {}).get("audio", "") if isinstance(data.get("data"), dict) else ""
    extra = data.get("extra_info", {}) or {}

    return {
        "url": audio_data or None,
        "duration_ms": extra.get("music_duration"),
        "model": model,
        "sample_rate": extra.get("music_sample_rate", sample_rate),
        "bitrate": extra.get("bitrate", bitrate),
    }


# ---------------------------------------------------------------------------
# Voice listing
# ---------------------------------------------------------------------------


async def list_voices() -> list[dict[str, Any]]:
    """List default known voice IDs. MiniMax has no public voices list endpoint
    for the speech API, so we return the documented defaults plus a note."""
    return [
        {"voice_id": vid, "language": lang, "gender": gender}
        for lang_voices in [
            ("English", "male", "English_Persuasive_Man"),
            ("English", "female", "English_Insightful_Speaker"),
            ("Chinese (Mandarin)", "female", "Chinese (Mandarin)_Lyrical_Voice"),
            ("Cantonese", "female", "Cantonese_GentleLady"),
            ("Japanese", "female", "Japanese_Whisper_Belle"),
        ]
        for vid, lang, gender in [(lang_voices[2], lang_voices[0], lang_voices[1])]
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_tts_model_options() -> list[str]:
    return TTS_MODELS


def get_music_model_options() -> list[str]:
    return MUSIC_MODELS
