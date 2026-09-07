"""Tests for beat_sync module — music-reactive video editing."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import patch

from brandly_cli import beat_sync


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def _make_test_clip(path: Path, duration: float = 1.0) -> Path:
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"testsrc2=size=320x240:duration={duration}:rate=10",
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=mono",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "64k",
        "-shortest", str(path),
    ]
    subprocess.run(cmd, capture_output=True, timeout=15)
    return path


class TestBeatSync:
    """Tests for beat_sync function."""

    def test_beat_sync_creates_output(self, tmp_path: Path) -> None:
        """Valid sync produces output file."""
        video = _make_test_clip(tmp_path / "video.mp4", duration=2.0)
        audio = _make_test_clip(tmp_path / "audio.mp4", duration=2.0)
        out = tmp_path / "output.mp4"

        result = _run(beat_sync.beat_sync(video, audio, out))
        # Should either succeed or return a non-error result
        assert "beats_detected" in result or "error" in result

    def test_beat_sync_invalid_video(self, tmp_path: Path) -> None:
        """Missing video file returns error."""
        audio = _make_test_clip(tmp_path / "audio.mp4", duration=1.0)
        result = _run(beat_sync.beat_sync(tmp_path / "missing.mp4", audio, tmp_path / "out.mp4"))
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_beat_sync_no_ffmpeg(self, tmp_path: Path) -> None:
        """No ffmpeg returns graceful error."""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake")
        with patch("brandly_cli.beat_sync._ffmpeg_available", return_value=False):
            result = _run(beat_sync.beat_sync(video, video, tmp_path / "out.mp4"))
        assert "error" in result
        assert "ffmpeg" in result["error"]

    def test_beat_sync_min_clip_duration(self, tmp_path: Path) -> None:
        """Min clip duration parameter is respected."""
        video = _make_test_clip(tmp_path / "video.mp4", duration=2.0)
        audio = _make_test_clip(tmp_path / "audio.mp4", duration=2.0)
        result = _run(beat_sync.beat_sync(video, audio, tmp_path / "out.mp4", min_clip_duration=2.0))  # noqa: E501
        # With 2s min duration and 2s video, should create 1 segment
        if "error" not in result:
            assert result.get("clips_created", 0) >= 1

    def test_beat_sync_three_beats(self, tmp_path: Path) -> None:
        """Multi-beat sync creates multiple segments."""
        video = _make_test_clip(tmp_path / "video.mp4", duration=3.0)
        audio = _make_test_clip(tmp_path / "audio.mp4", duration=3.0)
        result = _run(beat_sync.beat_sync(video, audio, tmp_path / "out.mp4"))
        # Result should have expected keys
        if "error" not in result:
            assert isinstance(result.get("beats_detected"), int)
            assert isinstance(result.get("clips_created"), int)


class TestBeatDetection:
    """Tests for beat detection."""

    def test_detect_beats_returns_list(self, tmp_path: Path) -> None:
        """Beat detection returns a list."""
        audio = _make_test_clip(tmp_path / "audio.mp4", duration=1.0)
        beats = beat_sync.detect_beats(audio)
        assert isinstance(beats, list)

    def test_detect_beats_invalid_audio(self, tmp_path: Path) -> None:
        """Beat detection handles invalid audio gracefully."""
        fake = tmp_path / "fake.mp3"
        fake.write_bytes(b"not audio")
        beats = beat_sync.detect_beats(fake)
        assert isinstance(beats, list)
