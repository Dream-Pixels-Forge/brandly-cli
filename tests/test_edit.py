"""Tests for video editing FFmpeg wrappers and caption utilities."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from brandly_cli import captions, edit


def _run(coro):    # type: ignore[no-untyped-def]
    """Run an async coroutine to completion."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# edit.py — error paths (testable without FFmpeg installed)
# ---------------------------------------------------------------------------


def test_get_video_info_missing_file() -> None:
    result = _run(edit.get_video_info("/nonexistent/path.mp4"))
    assert "error" in result
    assert "File not found" in result["error"]


def test_trim_video_missing_input(tmp_path: Path) -> None:
    result = _run(edit.trim_video(tmp_path / "missing.mp4", tmp_path / "out.mp4"))
    assert "error" in result
    assert "Input file not found" in result["error"]


def test_trim_video_no_ffmpeg(tmp_path: Path) -> None:
    """When ffmpeg is not installed, trim returns error dict."""
    src = tmp_path / "src.mp4"
    src.write_bytes(b"fake")
    with patch("brandly_cli.edit._ffmpeg_available", return_value=False):
        result = _run(edit.trim_video(src, tmp_path / "out.mp4"))
    assert "error" in result
    assert "ffmpeg" in result["error"]


def test_resize_video_missing_input(tmp_path: Path) -> None:
    result = _run(edit.resize_video(tmp_path / "missing.mp4", tmp_path / "out.mp4", width=640))
    assert "error" in result
    assert "Input file not found" in result["error"]


def test_resize_video_no_ffmpeg(tmp_path: Path) -> None:
    src = tmp_path / "src.mp4"
    src.write_bytes(b"fake")
    with patch("brandly_cli.edit._ffmpeg_available", return_value=False):
        result = _run(edit.resize_video(src, tmp_path / "out.mp4", width=640))
    assert "error" in result


def test_concatenate_videos_too_few_inputs(tmp_path: Path) -> None:
    result = _run(edit.concatenate_videos([tmp_path / "only.mp4"], tmp_path / "out.mp4"))
    assert "error" in result
    assert "at least 2" in result["error"]


def test_concatenate_videos_no_ffmpeg(tmp_path: Path) -> None:
    src1 = tmp_path / "a.mp4"
    src2 = tmp_path / "b.mp4"
    src1.write_bytes(b"a")
    src2.write_bytes(b"b")
    with patch("brandly_cli.edit._ffmpeg_available", return_value=False):
        result = _run(edit.concatenate_videos([src1, src2], tmp_path / "out.mp4"))
    assert "error" in result


def test_concatenate_videos_missing_file(tmp_path: Path) -> None:
    src1 = tmp_path / "a.mp4"
    src1.write_bytes(b"a")
    result = _run(
        edit.concatenate_videos([src1, tmp_path / "missing.mp4"], tmp_path / "out.mp4")
    )
    assert "error" in result
    assert "Missing files" in result["error"]


def test_extract_audio_missing_input(tmp_path: Path) -> None:
    result = _run(edit.extract_audio(tmp_path / "missing.mp4", tmp_path / "out.mp3"))
    assert "error" in result


def test_extract_audio_no_ffmpeg(tmp_path: Path) -> None:
    src = tmp_path / "src.mp4"
    src.write_bytes(b"fake")
    with patch("brandly_cli.edit._ffmpeg_available", return_value=False):
        result = _run(edit.extract_audio(src, tmp_path / "out.mp3"))
    assert "error" in result


def test_change_speed_missing_input(tmp_path: Path) -> None:
    result = _run(edit.change_speed(tmp_path / "missing.mp4", tmp_path / "out.mp4", 1.5))
    assert "error" in result


def test_change_speed_no_ffmpeg(tmp_path: Path) -> None:
    src = tmp_path / "src.mp4"
    src.write_bytes(b"fake")
    with patch("brandly_cli.edit._ffmpeg_available", return_value=False):
        result = _run(edit.change_speed(src, tmp_path / "out.mp4", 1.5))
    assert "error" in result


# ---------------------------------------------------------------------------
# add_subtitles (in edit.py)
# ---------------------------------------------------------------------------


def test_add_subtitles_missing_input(tmp_path: Path) -> None:
    result = _run(
        edit.add_subtitles(tmp_path / "missing.mp4", tmp_path / "out.mp4", "Hello")
    )
    assert "error" in result


def test_add_subtitles_no_ffmpeg(tmp_path: Path) -> None:
    src = tmp_path / "src.mp4"
    src.write_bytes(b"fake")
    with patch("brandly_cli.edit._ffmpeg_available", return_value=False):
        result = _run(edit.add_subtitles(src, tmp_path / "out.mp4", "Hello"))
    assert "error" in result


# ---------------------------------------------------------------------------
# Mocked success paths
# ---------------------------------------------------------------------------


def test_get_video_info_parses_metadata(tmp_path: Path) -> None:
    """Mock ffprobe and verify metadata parsing."""
    fake_json = json.dumps(
        {
            "format": {
                "duration": "12.345",
                "size": "1234567",
                "bit_rate": "800000",
                "format_long_name": "MP4",
            },
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1280,
                    "height": 720,
                    "display_aspect_ratio": "16:9",
                    "r_frame_rate": "24/1",
                },
            ],
        }
    )

    fake_proc = MagicMock()
    fake_proc.communicate = AsyncMock(return_value=(fake_json.encode(), b""))
    fake_proc.returncode = 0

    src = tmp_path / "video.mp4"
    src.write_bytes(b"fake")

    async def fake_exec(*args, **kwargs):    # type: ignore[no-untyped-def]
        return fake_proc

    with (
        patch("brandly_cli.edit._ffprobe_available", return_value=True),
        patch("asyncio.create_subprocess_exec", side_effect=fake_exec),
    ):
        result = _run(edit.get_video_info(src))
    assert result["duration_seconds"] == 12.345
    assert result["video_width"] == 1280
    assert result["video_codec"] == "h264"
    assert result["has_audio"] is False


def test_get_video_info_ffprobe_unavailable(tmp_path: Path) -> None:
    src = tmp_path / "video.mp4"
    src.write_bytes(b"fake")
    with patch("brandly_cli.edit._ffprobe_available", return_value=False):
        result = _run(edit.get_video_info(src))
    assert "error" in result
    assert "ffprobe" in result["error"]


def test_get_video_info_probe_error(tmp_path: Path) -> None:
    """When ffprobe returns non-zero exit code, capture stderr."""
    fake_proc = MagicMock()
    fake_proc.communicate = AsyncMock(return_value=(b"", b"ffprobe error message"))
    fake_proc.returncode = 1

    src = tmp_path / "video.mp4"
    src.write_bytes(b"fake")

    async def fake_exec(*args, **kwargs):    # type: ignore[no-untyped-def]
        return fake_proc

    with (
        patch("brandly_cli.edit._ffprobe_available", return_value=True),
        patch("asyncio.create_subprocess_exec", side_effect=fake_exec),
    ):
        result = _run(edit.get_video_info(src))
    assert "error" in result
    assert "ffprobe error" in result["error"]


# ---------------------------------------------------------------------------
# captions.py — pure helpers (no FFmpeg required)
# ---------------------------------------------------------------------------


def test_split_into_captions_basic() -> None:
    result = captions.split_into_captions("Hello world this is a test of caption splitting")
    assert isinstance(result, list)
    assert len(result) > 0
    for chunk in result:
        assert "text" in chunk
        assert "start" in chunk
        assert "end" in chunk


def test_split_into_captions_empty() -> None:
    assert captions.split_into_captions("") == []


def test_split_into_captions_short_text() -> None:
    result = captions.split_into_captions("Hi")
    assert len(result) == 1
    assert result[0]["text"] == "Hi"


def test_generate_srt_format() -> None:
    chunks = [
        {"text": "First line", "start": 0.0, "end": 2.5},
        {"text": "Second line", "start": 2.5, "end": 5.0},
    ]
    srt = captions.generate_srt(chunks)
    assert "1" in srt
    assert "First line" in srt
    assert "00:00:00.000" in srt  # Note: implementation uses . not , for ms
    assert "00:00:02.500" in srt
    assert "Second line" in srt


def test_generate_vtt_format() -> None:
    chunks = [
        {"text": "Hello", "start": 0.0, "end": 1.0},
    ]
    vtt = captions.generate_vtt(chunks)
    assert vtt.startswith("WEBVTT")
    assert "Hello" in vtt


def test_generate_cc_xml_format() -> None:
    chunks = [{"text": "Hello world", "start": 0.0, "end": 1.0}]
    xml = captions.generate_cc_xml(chunks)
    assert "<?xml" in xml
    assert "<captions>" in xml
    assert "Hello world" in xml


def test_auto_capitalize() -> None:
    assert captions.auto_capitalize("hello world") == "Hello world"
    assert captions.auto_capitalize("") == ""
