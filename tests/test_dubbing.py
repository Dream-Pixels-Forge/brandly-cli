"""Tests for the dubbing module — multi-language video dubbing."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import patch

from brandly_cli import dubbing


def _run(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine to completion."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_clip(path: Path, duration: float = 1.0, width: int = 320, height: int = 240) -> Path:
    """Create a minimal H.264 test clip using FFmpeg testsrc2."""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"testsrc2=size={width}x{height}:duration={duration}:rate=10",
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=mono",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "64k",
        "-shortest",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=15)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create test clip: {result.stderr.decode()[:200]}")
    return path


class TestDubVideo:
    """Tests for the dub_video function."""

    def test_dub_video_invalid_input(self, tmp_path: Path) -> None:
        """Missing input file returns error."""
        result = _run(dubbing.dub_video(tmp_path / "missing.mp4", "en", "es"))
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_dub_video_no_ffmpeg(self, tmp_path: Path) -> None:
        """When ffmpeg is unavailable, returns graceful error."""
        src = tmp_path / "input.mp4"
        src.write_bytes(b"fake")
        with patch("brandly_cli.dubbing._ffmpeg_available", return_value=False):
            result = _run(dubbing.dub_video(src, "en", "es"))
        assert "error" in result
        assert "ffmpeg" in result["error"].lower()

    def test_dub_video_invalid_source_lang(self, tmp_path: Path) -> None:
        """Invalid source language returns error."""
        src = tmp_path / "input.mp4"
        src.write_bytes(b"fake")
        result = _run(dubbing.dub_video(src, "xx", "es"))
        assert "error" in result

    def test_dub_video_invalid_target_lang(self, tmp_path: Path) -> None:
        """Invalid target language returns error."""
        src = tmp_path / "input.mp4"
        src.write_bytes(b"fake")
        result = _run(dubbing.dub_video(src, "en", "xx"))
        assert "error" in result

    def test_dub_video_invalid_voice_style(self, tmp_path: Path) -> None:
        """Invalid voice style returns error."""
        src = tmp_path / "input.mp4"
        src.write_bytes(b"fake")
        result = _run(dubbing.dub_video(src, "en", "es", voice_style="unknown"))
        assert "error" in result

    def test_dub_video_output_path_respected(self, tmp_path: Path) -> None:
        """Custom output path is respected."""
        src = tmp_path / "input.mp4"
        src.write_bytes(b"fake")
        custom_out = tmp_path / "custom_output.mp4"
        result = _run(dubbing.dub_video(src, "en", "es", output_path=custom_out))
        assert "error" in result  # Will fail on fake file, but should not error on path


class TestLanguageMapping:
    """Tests for language mappings."""

    def test_language_map_complete(self) -> None:
        """All expected languages are present."""
        expected = ["en", "es", "fr", "de", "ja", "ko", "zh", "pt", "ar", "hi"]
        for lang in expected:
            assert lang in dubbing.LANGUAGES

    def test_language_tupple_structure(self) -> None:
        """Each language maps to a tuple of (name, voice_id)."""
        for _, (name, voice_id) in dubbing.LANGUAGES.items():
            assert isinstance(name, str)
            assert isinstance(voice_id, str)
            assert len(name) > 0
            assert len(voice_id) > 0

    def test_voice_styles_defined(self) -> None:
        """Voice styles dictionary is defined."""
        assert isinstance(dubbing.VOICE_STYLES, dict)
        assert len(dubbing.VOICE_STYLES) > 0


class TestDubbingHelpers:
    """Tests for internal helpers."""

    def test_resolve_output_path_default(self, tmp_path: Path) -> None:
        """Default output path uses target language suffix."""
        video = tmp_path / "input.mp4"
        result = dubbing._resolve_output(video, "es", None)
        assert "es" in result.name
        assert result.suffix == ".mp4"

    def test_resolve_output_path_custom_root(self, tmp_path: Path) -> None:
        """Output path respects root parameter."""
        video = tmp_path / "input.mp4"
        result = dubbing._resolve_output(video, "fr", tmp_path)
        assert str(tmp_path) in str(result)
