"""Issue #119: brandly mux — mix narration VO + music bed into a video.

Closes the post-production loop: tts/music produce audio files, but nothing
could add them to an assembled film. mux_audio supports replace/mix/duck
modes (duck = sidechain-compress the music bed under the video's own audio),
with gain/fades/offset per added audio.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from brandly_cli import edit


def _run(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine to completion."""
    return asyncio.run(coro)


def _fake_exec_capture(argvs: list):  # type: ignore[no-untyped-def]
    """Return a fake create_subprocess_exec that records argv and succeeds."""
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b"", b""))
    proc.returncode = 0

    async def fake_exec(*args, **kwargs):  # type: ignore[no-untyped-def]
        argvs.append(list(args))
        return proc

    return fake_exec


def _write(p: Path) -> Path:  # type: ignore[no-untyped-def]
    p.write_bytes(b"fake")
    return p


def _video_info(has_audio: bool) -> dict:  # type: ignore[no-untyped-def]
    return {"duration_seconds": 10.0, "has_audio": has_audio}


def test_mux_missing_input(tmp_path: Path) -> None:
    result = _run(edit.mux_audio(tmp_path / "missing.mp4", [_write(tmp_path / "a.mp3")], tmp_path / "out.mp4"))
    assert "error" in result


def test_mux_missing_audio(tmp_path: Path) -> None:
    result = _run(edit.mux_audio(_write(tmp_path / "v.mp4"), [tmp_path / "missing.mp3"], tmp_path / "out.mp4"))
    assert "error" in result


def test_mux_no_ffmpeg(tmp_path: Path) -> None:
    with patch("brandly_cli.edit._ffmpeg_available", return_value=False):
        result = _run(
            edit.mux_audio(_write(tmp_path / "v.mp4"), [_write(tmp_path / "a.mp3")], tmp_path / "out.mp4")
        )
    assert "error" in result


def test_mux_invalid_mode(tmp_path: Path) -> None:
    result = _run(
        edit.mux_audio(
            _write(tmp_path / "v.mp4"),
            [_write(tmp_path / "a.mp3")],
            tmp_path / "out.mp4",
            mode="explode",
        )
    )
    assert "error" in result
    assert "mode" in result["error"]


def test_mux_replace_maps_bed_only(tmp_path: Path) -> None:
    argvs: list = []
    with (
        patch("brandly_cli.edit._ffmpeg_available", return_value=True),
        patch("brandly_cli.edit.get_video_info", AsyncMock(return_value=_video_info(True))),
        patch("asyncio.create_subprocess_exec", side_effect=_fake_exec_capture(argvs)),
    ):
        result = _run(
            edit.mux_audio(_write(tmp_path / "v.mp4"), [_write(tmp_path / "a.mp3")], tmp_path / "o.mp4", mode="replace")
        )
    assert "error" not in result
    argv = argvs[0]
    assert "-shortest" in argv
    graph = argv[argv.index("-filter_complex") + 1]
    assert "sidechaincompress" not in graph
    assert "[bed]" in graph
    assert argv[argv.index("-map") + 1] == "0:v"


def test_mux_mix_combines_bed_and_video_audio(tmp_path: Path) -> None:
    argvs: list = []
    with (
        patch("brandly_cli.edit._ffmpeg_available", return_value=True),
        patch("brandly_cli.edit.get_video_info", AsyncMock(return_value=_video_info(True))),
        patch("asyncio.create_subprocess_exec", side_effect=_fake_exec_capture(argvs)),
    ):
        _run(edit.mux_audio(_write(tmp_path / "v.mp4"), [_write(tmp_path / "a.mp3")], tmp_path / "o.mp4", mode="mix"))
    graph = argvs[0][argvs[0].index("-filter_complex") + 1]
    assert "amix" in graph
    assert "sidechaincompress" not in graph
    assert "[aout]" in graph


def test_mux_duck_compresses_bed_under_video_audio(tmp_path: Path) -> None:
    argvs: list = []
    with (
        patch("brandly_cli.edit._ffmpeg_available", return_value=True),
        patch("brandly_cli.edit.get_video_info", AsyncMock(return_value=_video_info(True))),
        patch("asyncio.create_subprocess_exec", side_effect=_fake_exec_capture(argvs)),
    ):
        _run(edit.mux_audio(_write(tmp_path / "v.mp4"), [_write(tmp_path / "a.mp3")], tmp_path / "o.mp4", mode="duck"))
    graph = argvs[0][argvs[0].index("-filter_complex") + 1]
    assert "sidechaincompress" in graph
    assert "threshold=0.05" in graph


def test_mux_duck_without_video_audio_falls_back_to_replace(tmp_path: Path) -> None:
    argvs: list = []
    with (
        patch("brandly_cli.edit._ffmpeg_available", return_value=True),
        patch("brandly_cli.edit.get_video_info", AsyncMock(return_value=_video_info(False))),
        patch("asyncio.create_subprocess_exec", side_effect=_fake_exec_capture(argvs)),
    ):
        _run(edit.mux_audio(_write(tmp_path / "v.mp4"), [_write(tmp_path / "a.mp3")], tmp_path / "o.mp4", mode="duck"))
    graph = argvs[0][argvs[0].index("-filter_complex") + 1]
    assert "sidechaincompress" not in graph
    assert "[aout]" not in graph


def test_mux_two_audio_inputs_and_styling(tmp_path: Path) -> None:
    argvs: list = []
    with (
        patch("brandly_cli.edit._ffmpeg_available", return_value=True),
        patch("brandly_cli.edit.get_video_info", AsyncMock(return_value=_video_info(True))),
        patch("asyncio.create_subprocess_exec", side_effect=_fake_exec_capture(argvs)),
    ):
        _run(
            edit.mux_audio(
                _write(tmp_path / "v.mp4"),
                [_write(tmp_path / "music.mp3"), _write(tmp_path / "vo.wav")],
                tmp_path / "o.mp4",
                mode="mix",
                fade_in=2.0,
                fade_out=3.0,
                offset=1.5,
                audio_gain=0.8,
            )
        )
    argv = argvs[0]
    assert argv.count("-i") == 3  # 1 video + 2 audio inputs
    graph = argv[argv.index("-filter_complex") + 1]
    assert "adelay=1500" in graph
    assert "afade=t=in:st=0:d=2" in graph
    assert "volume=0.8" in graph
    assert "areverse" in graph  # fade-out without needing the audio duration
    assert "amix=inputs=2" in graph  # the two audio inputs mix into [bed]


def test_mux_invalid_values_fail_closed(tmp_path: Path) -> None:
    result = _run(
        edit.mux_audio(
            _write(tmp_path / "v.mp4"),
            [_write(tmp_path / "a.mp3")],
            tmp_path / "o.mp4",
            fade_in=-1.0,
        )
    )
    assert "error" in result
