"""Tests for the export_platforms module — platform-optimized video exports."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest

from brandly_cli import export_platforms


def _run(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine to completion."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Helpers — generate test clips
# ---------------------------------------------------------------------------

def _make_test_clip(
    path: Path, duration: float = 1.0, width: int = 320, height: int = 240
) -> Path:
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


class TestExportForPlatform:
    """Tests for the export_for_platform function."""

    def test_export_tiktok_creates_video(self, tmp_path: Path) -> None:
        """TikTok export creates valid video file."""
        video = _make_test_clip(tmp_path / "input.mp4", duration=2.0)
        out_dir = tmp_path / "exports"
        result = _run(export_platforms.export_for_platform(video, "tiktok", out_dir))
        assert "error" not in result
        assert Path(result["output_path"]).exists()
        assert result["platform"] == "tiktok"
        assert result["captions_added"] is False

    def test_export_instagram_reel(self, tmp_path: Path) -> None:
        """Instagram Reel export works correctly."""
        video = _make_test_clip(tmp_path / "input.mp4", duration=2.0)
        out_dir = tmp_path / "exports"
        result = _run(
            export_platforms.export_for_platform(video, "instagram_reel", out_dir)
        )
        assert "error" not in result
        assert result["platform"] == "instagram_reel"

    def test_export_youtube_standard(self, tmp_path: Path) -> None:
        """YouTube standard format export works."""
        video = _make_test_clip(tmp_path / "input.mp4", duration=5.0, width=1280, height=720)
        out_dir = tmp_path / "exports"
        result = _run(
            export_platforms.export_for_platform(video, "youtube_standard", out_dir)
        )
        assert "error" not in result
        assert result["platform"] == "youtube_standard"

    def test_export_unknown_platform(self, tmp_path: Path) -> None:
        """Unknown platform raises ValueError."""
        video = _make_test_clip(tmp_path / "input.mp4", duration=1.0)
        out_dir = tmp_path / "exports"
        with pytest.raises(ValueError):
            _run(export_platforms.export_for_platform(video, "unknown", out_dir))

    def test_export_video_too_long(self, tmp_path: Path) -> None:
        """Long video gets trimmed to platform max duration."""
        video = _make_test_clip(tmp_path / "input.mp4", duration=20.0)
        out_dir = tmp_path / "exports"
        result = _run(export_platforms.export_for_platform(video, "tiktok", out_dir))
        assert "error" not in result
        # Duration should be <= 60 (TikTok max)
        assert result["duration_seconds"] <= 60.0

    def test_export_without_captions(self, tmp_path: Path) -> None:
        """Export without captions works."""
        video = _make_test_clip(tmp_path / "input.mp4", duration=1.0)
        out_dir = tmp_path / "exports"
        result = _run(
            export_platforms.export_for_platform(video, "tiktok", out_dir, add_captions=False)
        )
        assert "error" not in result
        assert result["captions_added"] is False

    def test_export_invalid_input(self, tmp_path: Path) -> None:
        """Missing input file handled gracefully."""
        missing = tmp_path / "nonexistent.mp4"
        out_dir = tmp_path / "exports"
        result = _run(export_platforms.export_for_platform(missing, "tiktok", out_dir))
        assert "error" in result
        assert "not found" in result["error"].lower()


class TestPlatformPresets:
    """Tests for platform preset completeness."""

    def test_all_platforms_have_required_fields(self) -> None:
        """All platform presets have required configuration fields."""
        required_fields = {"ratio", "max_duration", "caption_style", "safe_zone"}
        for platform, preset in export_platforms.PLATFORM_PRESETS.items():
            assert required_fields.issubset(set(preset.keys())), \
                f"Platform {platform} missing fields: {required_fields - set(preset.keys())}"

    def test_all_platforms_defined(self) -> None:
        """Common platforms are defined in presets."""
        platforms = [
            "tiktok", "instagram_reel", "instagram_post",
            "youtube_short", "youtube_standard", "facebook_story",
        ]
        for platform in platforms:
            assert platform in export_platforms.PLATFORM_PRESETS, f"Missing platform: {platform}"
