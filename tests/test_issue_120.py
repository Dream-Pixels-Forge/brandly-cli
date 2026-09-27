"""Issue #120: captions accepts SRT/VTT files for timed subtitles.

add_subtitles previously burned ONE static ASS event across the whole video
(0:00-10:00) - fine for a title card, useless for narration subtitles. A
subtitle file path (.srt/.vtt) now expands into one ASS Dialogue per cue
with real start/end times; the single-string mode is unchanged.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from brandly_cli import edit
from brandly_cli.captions import parse_subtitle_file


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


SRT = """1
00:00:01,500 --> 00:00:03,000
Hello there

2
00:00:04,000 --> 00:00:06,250
Second line
with two rows

3
00:01:02,100 --> 00:01:04,000
Later cue
"""

VTT = """WEBVTT

00:00:01.500 --> 00:00:03.000
Hello there

00:00:04.000 --> 00:00:06.250
Second line
"""


def test_parse_srt(tmp_path: Path) -> None:
    path = tmp_path / "subs.srt"
    path.write_text(SRT, encoding="utf-8")
    cues = parse_subtitle_file(path)
    assert len(cues) == 3
    assert cues[0]["start"] == 1.5 and cues[0]["end"] == 3.0
    assert cues[0]["text"] == "Hello there"
    assert "with two rows" in cues[1]["text"]
    assert cues[2]["start"] == 62.1 and cues[2]["end"] == 64.0


def test_parse_vtt(tmp_path: Path) -> None:
    path = tmp_path / "subs.vtt"
    path.write_text(VTT, encoding="utf-8")
    cues = parse_subtitle_file(path)
    assert len(cues) == 2
    assert cues[0]["start"] == 1.5 and cues[0]["end"] == 3.0


def test_parse_bad_file_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "subs.srt"
    path.write_text("no timestamps here\n\nat all", encoding="utf-8")
    cues = parse_subtitle_file(path)
    assert cues == []


def _fake_exec_capture_ass(contents: list):  # type: ignore[no-untyped-def]
    """Capture the ASS content at ffmpeg-invocation time (the temp .ass dir is
    removed in add_subtitles' finally block)."""
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b"", b""))
    proc.returncode = 0

    async def fake_exec(*args, **kwargs):  # type: ignore[no-untyped-def]
        for a in args:
            s = str(a)
            if s.startswith("ass="):
                try:
                    contents.append(Path(s[4:]).read_text(encoding="utf-8"))
                except OSError:
                    pass
        return proc

    return fake_exec


def test_add_subtitles_srt_expands_to_timed_dialogues(tmp_path: Path) -> None:
    src = tmp_path / "v.mp4"
    src.write_bytes(b"fake")
    subs = tmp_path / "subs.srt"
    subs.write_text(SRT, encoding="utf-8")
    contents: list = []
    with (
        patch("brandly_cli.edit._ffmpeg_available", return_value=True),
        patch("brandly_cli.edit.get_video_info", AsyncMock(return_value={"duration_seconds": 70.0})),
        patch("asyncio.create_subprocess_exec", side_effect=_fake_exec_capture_ass(contents)),
    ):
        result = _run(edit.add_subtitles(src, tmp_path / "out.mp4", str(subs)))
    assert "error" not in result
    assert len(contents) == 1
    ass = contents[0]
    assert ass.count("Dialogue:") == 3
    assert "0:00:01.50" in ass and "0:00:03.00" in ass
    assert "0:01:02.10" in ass
    assert "Hello there" in ass


def test_add_subtitles_plain_string_stays_static(tmp_path: Path) -> None:
    src = tmp_path / "v.mp4"
    src.write_bytes(b"fake")
    contents: list = []
    with (
        patch("brandly_cli.edit._ffmpeg_available", return_value=True),
        patch("brandly_cli.edit.get_video_info", AsyncMock(return_value={"duration_seconds": 70.0})),
        patch("asyncio.create_subprocess_exec", side_effect=_fake_exec_capture_ass(contents)),
    ):
        _run(edit.add_subtitles(src, tmp_path / "out2.mp4", "STATIC TITLE"))
    assert len(contents) == 1
    ass = contents[0]
    assert ass.count("Dialogue:") == 1
    assert "0:00:00.00,0:10:00.00" in ass
    assert "STATIC TITLE" in ass
