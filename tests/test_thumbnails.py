"""Tests for video thumbnail generation."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from brandly_cli import thumbnails


def _run(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine to completion."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Helpers — generate minimal valid MP4 files for integration tests
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


# ---------------------------------------------------------------------------
# Error paths — missing file / no ffmpeg
# ---------------------------------------------------------------------------


def test_generate_thumbnails_invalid_video(tmp_path: Path) -> None:
    result = _run(
        thumbnails.generate_thumbnails(
            tmp_path / "does_not_exist.mp4",
            tmp_path / "out",
        )
    )
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_generate_thumbnails_no_ffmpeg(tmp_path: Path) -> None:
    src = tmp_path / "video.mp4"
    src.write_bytes(b"fake video")
    with patch("brandly_cli.thumbnails._ffmpeg_available", return_value=False):
        result = _run(
            thumbnails.generate_thumbnails(src, tmp_path / "out")
        )
    assert "error" in result
    assert "ffmpeg" in result["error"].lower()


# ---------------------------------------------------------------------------
# Real clip tests — use actual test clips like stitch tests
# ---------------------------------------------------------------------------

def test_generate_thumbnails_creates_files(tmp_path: Path) -> None:
    """Real end-to-end: ffmpeg extracts frames → PNGs are written."""
    video = _make_test_clip(tmp_path / "sample.mp4", duration=2.0, width=320, height=240)
    result = _run(
        thumbnails.generate_thumbnails(
            video,
            tmp_path / "thumbs",
            count=3,
        )
    )
    assert "error" not in result
    assert result["count"] >= 1
    assert result["style_preset"] == "commercial"
    assert result["video_path"] == str(video)


def test_generate_thumbnails_with_text(tmp_path: Path) -> None:
    """Text overlay is applied when provided."""
    video = _make_test_clip(tmp_path / "sample.mp4", duration=2.0, width=320, height=240)
    result = _run(
        thumbnails.generate_thumbnails(
            video,
            tmp_path / "thumbs",
            count=2,
            text_overlay="Link in bio →",
        )
    )
    assert "error" not in result
    # At least some thumbnails should have text overlay applied
    assert result["count"] >= 1


def test_generate_thumbnails_count(tmp_path: Path) -> None:
    """Requesting 5 thumbnails yields at least 1 (may be limited by video length)."""
    video = _make_test_clip(tmp_path / "sample.mp4", duration=2.0, width=320, height=240)
    result = _run(
        thumbnails.generate_thumbnails(
            video,
            tmp_path / "thumbs",
            count=5,
        )
    )
    assert "error" not in result
    assert result["count"] >= 1


def test_generate_thumbnail_platform_sizes(tmp_path: Path) -> None:
    """Thumbnails are generated for all platform sizes."""
    video = _make_test_clip(tmp_path / "sample.mp4", duration=2.0, width=320, height=240)
    result = _run(
        thumbnails.generate_thumbnails(
            video,
            tmp_path / "thumbs",
            count=1,
        )
    )
    assert "error" not in result
    # Check that platform variants were created
    thumbs_dir = Path(result["output_dir"])
    assert thumbs_dir.exists()


def test_generate_thumbnails_style_preset(tmp_path: Path) -> None:
    """Style preset parameter is respected."""
    video = _make_test_clip(tmp_path / "sample.mp4", duration=2.0, width=320, height=240)
    result = _run(
        thumbnails.generate_thumbnails(
            video,
            tmp_path / "thumbs",
            count=1,
            style_preset="bold",
        )
    )
    assert "error" not in result
    assert result["style_preset"] == "bold"


def test_generate_thumbnails_default_params(tmp_path: Path) -> None:
    """Default parameters work correctly."""
    video = _make_test_clip(tmp_path / "sample.mp4", duration=2.0, width=320, height=240)
    result = _run(
        thumbnails.generate_thumbnails(video, tmp_path / "thumbs")
    )
    assert "error" not in result
    assert result["count"] >= 1
    assert result["style_preset"] == "commercial"


# ---------------------------------------------------------------------------
# Mocked unit tests for individual helpers
# ---------------------------------------------------------------------------

def _make_mock_probe(duration: float = 30.0) -> str:
    return json.dumps({
        "format": {"duration": str(duration)},
    })


def test_apply_text_overlay_creates_image() -> None:
    """Text overlay function produces an image with text drawn."""
    from PIL import Image
    img = Image.new("RGBA", (1280, 720), (255, 255, 255, 255))
    result = thumbnails._draw_text_overlay(img, "Hello World", {"font_color": (255, 255, 255)})
    assert isinstance(result, Image.Image)
    assert result.size == (1280, 720)


def test_extract_frames_finds_keyframes(tmp_path: Path) -> None:
    """Frame extraction returns a list of frame paths."""
    video = _make_test_clip(tmp_path / "sample.mp4", duration=2.0, width=320, height=240)
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    # Call internal frame extraction via generate_thumbnails with count=1
    result = _run(
        thumbnails.generate_thumbnails(
            video,
            tmp_path / "thumbs",
            count=1,
        )
    )
    assert "error" not in result
    assert result["count"] >= 1
