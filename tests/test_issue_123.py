"""Issue #123: polish trio from a real production run.

1. resize --aspect accepts arbitrary W:H ratios (2.39:1) — the old branch
   built a broken negative-dimension scale filter and never parsed the ratio.
2. tts/music without MINIMAX_API_KEY raise a clean ClickException instead of
   a raw OSError traceback.
3. The no-primary-reference warning prints once per project per run, not
   once per shot (35-shot produce runs printed it 35 times).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from brandly_cli import edit
from brandly_cli.cli import cli


def _fake_exec_capture(argvs: list):  # type: ignore[no-untyped-def]
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b"", b""))
    proc.returncode = 0

    async def fake_exec(*args, **kwargs):  # type: ignore[no-untyped-def]
        argvs.append(list(args))
        return proc

    return fake_exec


def _probe_ok(*args, **kwargs):  # type: ignore[no-untyped-def]
    return {
        "duration_seconds": 10.0,
        "video_width": 1280,
        "video_height": 720,
        "has_audio": True,
    }


# ---------------------------------------------------------------------------
# 1. resize --aspect arbitrary ratios
# ---------------------------------------------------------------------------

def test_resize_aspect_239_1_builds_crop_filter(tmp_path: Path) -> None:
    argvs: list = []
    with (
        patch("brandly_cli.edit._ffmpeg_available", return_value=True),
        patch("brandly_cli.edit.get_video_info", AsyncMock(side_effect=_probe_ok)),
        patch("asyncio.create_subprocess_exec", side_effect=_fake_exec_capture(argvs)),
    ):
        result = asyncio.run(
            edit.resize_video(_f(tmp_path / "v.mp4"), tmp_path / "o.mp4", aspect="2.39:1")
        )
    assert "error" not in result
    argv = argvs[0]
    vf = argv[argv.index("-vf") + 1]
    assert "crop=" in vf
    assert "2.39" in vf


def test_resize_aspect_with_dimensions_crops_then_scales(tmp_path: Path) -> None:
    argvs: list = []
    with (
        patch("brandly_cli.edit._ffmpeg_available", return_value=True),
        patch("brandly_cli.edit.get_video_info", AsyncMock(side_effect=_probe_ok)),
        patch("asyncio.create_subprocess_exec", side_effect=_fake_exec_capture(argvs)),
    ):
        asyncio.run(
            edit.resize_video(
                _f(tmp_path / "v.mp4"), tmp_path / "o.mp4", aspect="2.39:1", width=1280, height=534
            )
        )
    vf = argvs[0][argvs[0].index("-vf") + 1]
    assert "crop=" in vf
    assert "scale=1280:534" in vf


def test_resize_aspect_16_9(tmp_path: Path) -> None:
    argvs: list = []
    with (
        patch("brandly_cli.edit._ffmpeg_available", return_value=True),
        patch("brandly_cli.edit.get_video_info", AsyncMock(side_effect=_probe_ok)),
        patch("asyncio.create_subprocess_exec", side_effect=_fake_exec_capture(argvs)),
    ):
        asyncio.run(edit.resize_video(_f(tmp_path / "v.mp4"), tmp_path / "o.mp4", aspect="16:9"))
    vf = argvs[0][argvs[0].index("-vf") + 1]
    assert "1.777" in vf or "1.778" in vf


def test_resize_invalid_aspect_fails_closed(tmp_path: Path) -> None:
    result = asyncio.run(edit.resize_video(_f(tmp_path / "v.mp4"), tmp_path / "o.mp4", aspect="wide"))
    assert "error" in result
    assert "aspect" in result["error"]


# ---------------------------------------------------------------------------
# 2. tts/music key errors surface as clean ClickExceptions
# ---------------------------------------------------------------------------

def test_tts_missing_minimax_key_clean_error(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    runner = CliRunner()
    result = runner.invoke(cli, ["tts", "hello world"])
    assert result.exit_code == 1
    assert "MINIMAX_API_KEY" in result.output
    assert "Traceback" not in result.output


def test_music_missing_minimax_key_clean_error(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    runner = CliRunner()
    result = runner.invoke(cli, ["music", "-p", "solo piano"])
    assert result.exit_code == 1
    assert "MINIMAX_API_KEY" in result.output
    assert "Traceback" not in result.output


# ---------------------------------------------------------------------------
# 3. no-primary-reference warning once per project per run
# ---------------------------------------------------------------------------

def test_reference_warning_once(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from brandly_cli.cmd import generation

    monkeypatch.setattr(generation, "_NO_PRIMARY_REF_WARNED", set())
    assert generation._should_warn_no_primary_reference("proj-a") is True
    assert generation._should_warn_no_primary_reference("proj-a") is False
    assert generation._should_warn_no_primary_reference("proj-b") is True


def _f(p: Path) -> Path:  # type: ignore[no-untyped-def]
    p.write_bytes(b"fake")
    return p
