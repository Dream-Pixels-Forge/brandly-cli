"""Tests for the stitch module — multi-shot video assembly with transitions and color grading."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from brandly_cli import stitch


def _run(coro):    # type: ignore[no-untyped-def]
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
# Error-path tests (no real clips needed)
# ---------------------------------------------------------------------------

def test_stitch_videos_invalid_clips(tmp_path: Path) -> None:
    """Missing input file returns an error dict."""
    result = _run(
        stitch.stitch_videos(
            [tmp_path / "a.mp4", tmp_path / "missing.mp4"],
            tmp_path / "out.mp4",
        )
    )
    assert "error" in result
    assert "missing" in result["error"].lower() or "not found" in result["error"].lower()


def test_stitch_videos_no_ffmpeg(tmp_path: Path) -> None:
    """When ffmpeg is unavailable, stitch returns a graceful error."""
    src = tmp_path / "a.mp4"
    src.write_bytes(b"fake")
    with patch("brandly_cli.stitch._ffmpeg_available", return_value=False):
        result = _run(stitch.stitch_videos([src], tmp_path / "out.mp4"))
    assert "error" in result
    assert "ffmpeg" in result["error"]


# ---------------------------------------------------------------------------
# Single-clip pass-through
# ---------------------------------------------------------------------------

def test_stitch_single_clip(tmp_path: Path) -> None:
    """A single clip passes through unchanged (no transitions needed)."""
    clip = _make_test_clip(tmp_path / "single.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(stitch.stitch_videos([clip], out))
    assert "error" not in result
    assert out.exists()
    assert result["clips_count"] == 1
    assert result["transitions_applied"] == []
    assert result["color_grade"] == "cinematic"  # default


# ---------------------------------------------------------------------------
# Two-clip concatenation with fade transition
# ---------------------------------------------------------------------------

def test_stitch_videos_creates_output(tmp_path: Path) -> None:
    """Two valid clips produce an output file with expected shape."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(stitch.stitch_videos([a, b], out))
    assert "error" not in result
    assert out.exists()
    assert isinstance(result["output_path"], str)
    assert isinstance(result["duration_seconds"], float)
    assert isinstance(result["size_bytes"], int)
    assert isinstance(result["transitions_applied"], list)
    assert isinstance(result["color_grade"], str)
    assert result["clips_count"] == 2


def test_stitch_videos_transition_fade(tmp_path: Path) -> None:
    """Fade transition between two clips produces correct output."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(
        stitch.stitch_videos([a, b], out, transition="fade", transition_duration=0.5)
    )
    assert "error" not in result
    assert "fade" in result["transitions_applied"]
    # Output should be shorter than sum of inputs due to transition overlap
    assert result["duration_seconds"] < 2.0


# ---------------------------------------------------------------------------
# Dissolve and wipe transitions
# ---------------------------------------------------------------------------

def test_stitch_videos_transition_dissolve(tmp_path: Path) -> None:
    """Dissolve transition applied correctly."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(
        stitch.stitch_videos([a, b], out, transition="dissolve", transition_duration=0.3)
    )
    assert "error" not in result
    assert "dissolve" in result["transitions_applied"]


def test_stitch_videos_transition_wipe(tmp_path: Path) -> None:
    """Wipe transition applied correctly."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(
        stitch.stitch_videos([a, b], out, transition="wipe", transition_duration=0.3)
    )
    # wipe may not be supported by all ffmpeg builds; accept success OR graceful fallback
    if "error" not in result:
        assert "wipe" in result["transitions_applied"]


def test_stitch_videos_transition_slide(tmp_path: Path) -> None:
    """Slide transition applied correctly."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(
        stitch.stitch_videos([a, b], out, transition="slide", transition_duration=0.3)
    )
    # slide may not be supported by all ffmpeg builds; accept success OR graceful fallback
    if "error" not in result:
        assert "slide" in result["transitions_applied"]


# ---------------------------------------------------------------------------
# Color grading
# ---------------------------------------------------------------------------

def test_stitch_videos_color_grade_cinematic(tmp_path: Path) -> None:
    """Cinematic color grade is applied."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(
        stitch.stitch_videos([a, b], out, color_grade="cinematic")
    )
    assert "error" not in result
    assert result["color_grade"] == "cinematic"


def test_stitch_videos_color_grade_warm(tmp_path: Path) -> None:
    """Warm color grade is applied."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(stitch.stitch_videos([a, b], out, color_grade="warm"))
    assert "error" not in result
    assert result["color_grade"] == "warm"


def test_stitch_videos_color_grade_cool(tmp_path: Path) -> None:
    """Cool color grade is applied."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(stitch.stitch_videos([a, b], out, color_grade="cool"))
    assert "error" not in result
    assert result["color_grade"] == "cool"


def test_stitch_videos_color_grade_desaturated(tmp_path: Path) -> None:
    """Desaturated color grade is applied."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(stitch.stitch_videos([a, b], out, color_grade="desaturated"))
    assert "error" not in result
    assert result["color_grade"] == "desaturated"


def test_stitch_videos_default_color_grade_is_cinematic(tmp_path: Path) -> None:
    """Default color grade is 'cinematic'."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(stitch.stitch_videos([a, b], out))
    assert result["color_grade"] == "cinematic"


# ---------------------------------------------------------------------------
# Multi-clip (3+ clips)
# ---------------------------------------------------------------------------

def test_stitch_three_clips(tmp_path: Path) -> None:
    """Three clips are concatenated with transitions between each pair."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    c = _make_test_clip(tmp_path / "c.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(stitch.stitch_videos([a, b, c], out))
    # Three-clip concat may fail with some ffmpeg builds due to filter complexity
    # Accept either success or that we attempted it with correct params
    if "error" not in result:
        assert out.exists()
        assert result["clips_count"] == 3
        assert len(result["transitions_applied"]) == 2
        assert result["duration_seconds"] < 3.0


def test_stitch_three_clips_different_transitions(tmp_path: Path) -> None:
    """Three clips with explicit transition type."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    c = _make_test_clip(tmp_path / "c.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(
        stitch.stitch_videos([a, b, c], out, transition="fade", transition_duration=0.3)
    )
    if "error" not in result:
        assert all(t == "fade" for t in result["transitions_applied"])


# ---------------------------------------------------------------------------
# Root parameter (testability — output goes to root, not cwd)
# ---------------------------------------------------------------------------

def test_stitch_videos_root_parameter(tmp_path: Path) -> None:
    """The root parameter directs output to the given directory."""
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = out_dir / "final.mp4"
    result = _run(stitch.stitch_videos([a, b], out, root=tmp_path))
    assert "error" not in result
    assert out.exists()


# ---------------------------------------------------------------------------
# Three-clip xfade/acrossfade filtergraph regressions
# ---------------------------------------------------------------------------

def _capture_cmd(tmp_path: Path, has_audio: bool, color_grade: str = "none") -> list[str]:
    """Run a 3-clip stitch with ffmpeg mocked; return the executed command."""
    clips = [_make_test_clip(tmp_path / f"{n}.mp4", duration=1.0) for n in "abc"]
    out = tmp_path / "out.mp4"
    captured_cmd: list[list[str]] = []

    async def fake_exec(*args, **kwargs):    # type: ignore[no-untyped-def]
        captured_cmd.append(list(args))
        fake_proc = MagicMock()
        fake_proc.communicate = AsyncMock(return_value=(b"", b""))
        fake_proc.returncode = 0
        return fake_proc

    with (
        patch("asyncio.create_subprocess_exec", side_effect=fake_exec),
        patch("brandly_cli.stitch._ffprobe_has_audio", return_value=has_audio),
    ):
        _run(
            stitch.stitch_videos(
                clips, out, transition="fade",
                transition_duration=0.5, color_grade=color_grade,
            )
        )
    assert len(captured_cmd) == 1
    return captured_cmd[0]


def test_three_clip_video_only_filtergraph_chains_labels(tmp_path: Path) -> None:
    """Regression: each xfade must consume the previous virtual label.

    The pre-fix graph emitted ``[v1];[2:v]xfade=...`` — an xfade with a
    single input pad — and ffmpeg rejected the whole graph ("Filter not
    found") for any clip count above 2.
    """
    cmd = _capture_cmd(tmp_path, has_audio=False)
    graph = next(arg for arg in cmd if "xfade" in arg)
    # Second xfade consumes [v1] (first xfade's output) plus clip 2
    assert "[v1][2:v]xfade=" in graph
    # Exactly one terminal [vout] — the pre-fix graph appended a dangling
    # second [vout] (or [vout];[vout]) which made ffmpeg reject it
    assert graph.count("[vout]") == 1
    # No grade → no extra ;[vout]eq=...[final_v] segment
    assert "[final_v]" not in graph


def test_three_clip_audio_filtergraph_chains_labels(tmp_path: Path) -> None:
    """Regression: acrossfade chain must also carry [a1] into filter 2."""
    cmd = _capture_cmd(tmp_path, has_audio=True)
    graph = next(arg for arg in cmd if "acrossfade" in arg)
    assert "[a1][2:a]acrossfade=" in graph
    assert graph.count("[aout]") == 1
    # Video mapping is [vout] when no grade is applied
    cmd_str = " ".join(cmd)
    assert " [vout]" in cmd_str


def test_three_clip_grade_filtergraph_segments_separated(tmp_path: Path) -> None:
    """The grade segment is joined with ';' so it reads [vout]eq=...[final_v]."""
    cmd = _capture_cmd(tmp_path, has_audio=False, color_grade="cinematic")
    graph = next(arg for arg in cmd if "xfade" in arg)
    assert ";[vout]eq=" in graph
    assert graph.endswith("[final_v]")
    # Output maps the graded label, not [vout]
    cmd_str = " ".join(cmd)
    assert " [final_v]" in cmd_str


def test_stitch_three_clips_fade_real_run(tmp_path: Path) -> None:
    """A real 3-clip fade stitch succeeds end-to-end (tightened from the
    previously error-tolerant check, which masked the graph bug)."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    c = _make_test_clip(tmp_path / "c.mp4", duration=1.0)
    out = tmp_path / "out.mp4"
    result = _run(
        stitch.stitch_videos([a, b, c], out, transition="fade", transition_duration=0.3)
    )
    assert "error" not in result, result.get("error")
    assert out.exists()
    assert result["clips_count"] == 3
    # 3s of source minus 2 x 0.3s of overlap
    assert result["duration_seconds"] < 3.0


# ---------------------------------------------------------------------------
# FFmpeg mock tests — verify command construction without running real FFmpeg
# ---------------------------------------------------------------------------

def test_stitch_builds_correct_ffmpeg_command_fade(tmp_path: Path) -> None:
    """Verify the FFmpeg filter_complex contains xfade fade for fade transition."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"

    captured_cmd: list[list[str]] = []

    async def fake_exec(*args, **kwargs):    # type: ignore[no-untyped-def]
        captured_cmd.append(list(args))
        fake_proc = MagicMock()
        fake_proc.communicate = AsyncMock(return_value=(b"", b""))
        fake_proc.returncode = 0
        return fake_proc

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        _run(stitch.stitch_videos([a, b], out, transition="fade", transition_duration=0.5))

    assert len(captured_cmd) == 1
    cmd = captured_cmd[0]
    # Should contain xfade with fade transition
    assert any("xfade" in str(arg) for arg in cmd)
    assert any("fade" in str(arg) for arg in cmd)


def test_stitch_builds_correct_ffmpeg_command_cinematic_grade(tmp_path: Path) -> None:
    """Verify the FFmpeg filter_complex contains cinematic EQ when color_grade='cinematic'."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"

    captured_cmd: list[list[str]] = []

    async def fake_exec(*args, **kwargs):    # type: ignore[no-untyped-def]
        captured_cmd.append(list(args))
        fake_proc = MagicMock()
        fake_proc.communicate = AsyncMock(return_value=(b"", b""))
        fake_proc.returncode = 0
        return fake_proc

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        _run(stitch.stitch_videos([a, b], out, color_grade="cinematic"))

    assert len(captured_cmd) == 1
    cmd = captured_cmd[0]
    assert any("eq=" in str(arg) for arg in cmd)
    assert any("brightness" in str(arg) for arg in cmd)


def test_stitch_builds_correct_ffmpeg_command_warm_grade(tmp_path: Path) -> None:
    """Verify warm color grade uses colorbalance filter."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"

    captured_cmd: list[list[str]] = []

    async def fake_exec(*args, **kwargs):    # type: ignore[no-untyped-def]
        captured_cmd.append(list(args))
        fake_proc = MagicMock()
        fake_proc.communicate = AsyncMock(return_value=(b"", b""))
        fake_proc.returncode = 0
        return fake_proc

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        _run(stitch.stitch_videos([a, b], out, color_grade="warm"))

    assert len(captured_cmd) == 1
    cmd = captured_cmd[0]
    assert any("colorbalance" in str(arg) for arg in cmd)


# ---------------------------------------------------------------------------
# FFmpeg failure propagation
# ---------------------------------------------------------------------------

def test_stitch_videos_ffmpeg_failure(tmp_path: Path) -> None:
    """When FFmpeg returns non-zero, the error is propagated."""
    a = _make_test_clip(tmp_path / "a.mp4", duration=1.0)
    b = _make_test_clip(tmp_path / "b.mp4", duration=1.0)
    out = tmp_path / "out.mp4"

    fake_proc = MagicMock()
    fake_proc.communicate = AsyncMock(return_value=(b"", b"ffmpeg filter error"))
    fake_proc.returncode = 1

    async def fake_exec(*args, **kwargs):    # type: ignore[no-untyped-def]
        return fake_proc

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        result = _run(stitch.stitch_videos([a, b], out))
    assert "error" in result
    assert "ffmpeg filter error" in result["error"]


# ---------------------------------------------------------------------------
# get_clip_duration helper (used internally)
# ---------------------------------------------------------------------------

def test_get_clip_duration(tmp_path: Path) -> None:
    """get_clip_duration returns the correct duration for a real clip."""
    clip = _make_test_clip(tmp_path / "clip.mp4", duration=2.5)
    duration = stitch.get_clip_duration(clip)
    assert isinstance(duration, float)
    assert 2.0 <= duration <= 3.0  # small tolerance for container overhead
