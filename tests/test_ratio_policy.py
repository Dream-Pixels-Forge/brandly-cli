"""G4: aspect-ratio cropping happens only in assembly/export (ratio policy).

Before G4 the production path (shot_runner) cropped every freshly generated
clip to ``--aspect-ratio`` while assembly/export owned the ratio poorly
(post-production only scaled/letterboxed) — two owners, one irreversible
decision taken at the most expensive point (audit F8). After G4:

* Production keeps source aspect — the shot loop no longer crops, and a
  legacy ``RunnerConfig.aspect_ratio`` attribute is ignored.
* ``stitch`` is the single assembly owner: ``ratio="2.39:1"`` +
  ``fit="crop"|"pad"`` with one shared filter implementation.
* ``export_platforms`` reuses the same filters: crop is the default for
  feed aspects, pad (letterbox) only when explicitly requested.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from brandly_cli import shot_runner, stitch
from brandly_cli.cli import cli
from brandly_cli.export_platforms import export_for_platform


def _run(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine to completion."""
    return asyncio.run(coro)


def _probe_dims(path: Path) -> tuple[int, int]:
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path),
        ],
        capture_output=True,
        timeout=30,
    )
    w, h = proc.stdout.decode(errors="replace").strip().split(",")
    return int(w), int(h)


def _make_test_clip(path: Path, duration: float = 1.0, width: int = 320, height: int = 240) -> Path:
    """Create a minimal H.264 testsrc2 clip (same helper as test_stitch)."""
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
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to create test clip: {result.stderr.decode(errors='replace')[:300]}"
        )
    return path


def _needs_ffmpeg() -> None:
    assert shutil.which("ffmpeg") and shutil.which("ffprobe"), "these tests require ffmpeg"


# ---------------------------------------------------------------------------
# Shared ratio filter builders (the one G4 implementation, in stitch)
# ---------------------------------------------------------------------------


class TestRatioFilterBuilders:
    """The exact filter expressions — shared by stitch and export-platforms."""

    def test_parse_ratio_forms(self) -> None:
        assert stitch.parse_ratio("2.39:1") == pytest.approx(2.39)
        assert stitch.parse_ratio("16:9") == pytest.approx(16 / 9)
        assert stitch.parse_ratio("2.39") == pytest.approx(2.39)

    def test_parse_ratio_rejects_garbage(self) -> None:
        with pytest.raises(ValueError):
            stitch.parse_ratio("not-a-ratio")
        with pytest.raises(ValueError):
            stitch.parse_ratio("0:1")

    def test_crop_filter_wide_source(self) -> None:
        # 320x240 (4:3) -> 1:1: crop width down to 240, height kept.
        assert stitch.ratio_crop_filter(320, 240, "1:1") == "crop=240:240"

    def test_crop_filter_narrow_source(self) -> None:
        # 1280x720 (16:9) -> 2.39:1: crop height down to even(1280/2.39)=534.
        assert stitch.ratio_crop_filter(1280, 720, "2.39:1") == "crop=1280:534"

    def test_crop_filter_noop_when_already_at_ratio(self) -> None:
        assert stitch.ratio_crop_filter(1280, 720, "16:9") == ""

    def test_pad_filter_wide_source(self) -> None:
        # 320x240 -> 1:1: pillarbox into 240x240 at source scale.
        assert stitch.ratio_pad_filter(320, 240, "1:1") == (
            "scale=240:240:force_original_aspect_ratio=decrease,"
            "pad=240:240:(ow-iw)/2:(oh-ih)/2"
        )

    def test_pad_filter_noop_when_already_at_ratio(self) -> None:
        assert stitch.ratio_pad_filter(1280, 720, "16:9") == ""


# ---------------------------------------------------------------------------
# stitch: single assembly-time ratio owner
# ---------------------------------------------------------------------------


class TestStitchRatioOwnership:
    def test_stitch_ratio_crop_probes_to_target(self, tmp_path: Path) -> None:
        _needs_ffmpeg()
        clip = _make_test_clip(tmp_path / "a.mp4")
        out = tmp_path / "out.mp4"
        result = _run(stitch.stitch_videos([clip], out, ratio="2.39:1", fit="crop"))
        assert "error" not in result, result
        w, h = _probe_dims(out)
        assert abs(w / h - 2.39) / 2.39 < 0.02

    def test_stitch_ratio_pad_probes_to_target(self, tmp_path: Path) -> None:
        _needs_ffmpeg()
        clip = _make_test_clip(tmp_path / "a.mp4")
        out = tmp_path / "out_pad.mp4"
        result = _run(stitch.stitch_videos([clip], out, ratio="2.39:1", fit="pad"))
        assert "error" not in result, result
        w, h = _probe_dims(out)
        assert abs(w / h - 2.39) / 2.39 < 0.02

    def test_stitch_without_ratio_keeps_source_dimensions(self, tmp_path: Path) -> None:
        _needs_ffmpeg()
        clip = _make_test_clip(tmp_path / "a.mp4")
        out = tmp_path / "out_plain.mp4"
        result = _run(stitch.stitch_videos([clip], out))
        assert "error" not in result, result
        assert _probe_dims(out) == (320, 240)

    def test_stitch_multi_clip_crop_applies_per_input(self, tmp_path: Path) -> None:
        _needs_ffmpeg()
        a = _make_test_clip(tmp_path / "a.mp4")
        b = _make_test_clip(tmp_path / "b.mp4")
        out = tmp_path / "out_multi.mp4"
        result = _run(stitch.stitch_videos([a, b], out, ratio="2.39:1"))
        assert "error" not in result, result
        w, h = _probe_dims(out)
        assert abs(w / h - 2.39) / 2.39 < 0.02

    def test_stitch_rejects_unknown_fit(self, tmp_path: Path) -> None:
        _needs_ffmpeg()
        clip = _make_test_clip(tmp_path / "a.mp4")
        result = _run(
            stitch.stitch_videos([clip], tmp_path / "o.mp4", ratio="2.39:1", fit="zoom")
        )
        assert "error" in result

    def test_stitch_rejects_bad_ratio(self, tmp_path: Path) -> None:
        _needs_ffmpeg()
        clip = _make_test_clip(tmp_path / "a.mp4")
        result = _run(stitch.stitch_videos([clip], tmp_path / "o.mp4", ratio="not-a-ratio"))
        assert "error" in result

    def test_stitch_cli_exposes_ratio_and_fit(self, tmp_path: Path) -> None:
        result = CliRunner(env={"ROOT": str(tmp_path)}).invoke(cli, ["stitch", "--help"])
        assert "--ratio" in result.output
        assert "--fit" in result.output


# ---------------------------------------------------------------------------
# export-platforms: reuses the same ratio implementation
# ---------------------------------------------------------------------------


class TestExportRatioPolicy:
    def test_export_default_crop_for_feed(self, tmp_path: Path) -> None:
        _needs_ffmpeg()
        video = _make_test_clip(tmp_path / "in.mp4")
        out_dir = tmp_path / "out"
        result = _run(export_for_platform(video, "tiktok", out_dir))
        assert "error" not in result, result
        w, h = _probe_dims(Path(result["output_path"]))
        # 320x240 -> 9:16 crop: width shrinks to 134 (even), height kept.
        assert h == 240
        assert w < 320
        assert abs(w / h - 9 / 16) / (9 / 16) < 0.02

    def test_export_explicit_pad_letterboxes_to_standard_dims(self, tmp_path: Path) -> None:
        _needs_ffmpeg()
        video = _make_test_clip(tmp_path / "in.mp4")
        out_dir = tmp_path / "out"
        result = _run(export_for_platform(video, "tiktok", out_dir, fit="pad"))
        assert "error" not in result, result
        assert _probe_dims(Path(result["output_path"])) == (1080, 1920)

    def test_stitch_then_export_no_double_crop(self, tmp_path: Path) -> None:
        _needs_ffmpeg()
        video = _make_test_clip(tmp_path / "in.mp4")
        master = tmp_path / "master.mp4"
        s = _run(stitch.stitch_videos([video], master, ratio="9:16"))
        assert "error" not in s, s
        w1, h1 = _probe_dims(master)
        e = _run(export_for_platform(master, "tiktok", tmp_path / "out"))
        assert "error" not in e, e
        # Already within 2% of the platform ratio -> the export crop is a
        # no-op; dimensions stay stable (no double-crop).
        assert _probe_dims(Path(e["output_path"])) == (w1, h1)


# ---------------------------------------------------------------------------
# production: keeps source aspect (no crop in the shot loop)
# ---------------------------------------------------------------------------


class TestProductionKeepsSource:
    def test_run_shots_ignores_legacy_aspect_ratio(self, tmp_path: Path) -> None:
        """Even with a legacy RunnerConfig.aspect_ratio set, the shot loop
        must never shell out to ffmpeg/ffprobe (G4: no production crop)."""
        _needs_ffmpeg()
        scenes = tmp_path / "videos" / "scenes"
        scenes.mkdir(parents=True, exist_ok=True)

        def generate_one(shot):
            (scenes / f"videos_{shot.id}.mp4").write_bytes(b"fake")
            return True, 0, ""

        shots = [
            shot_runner.Shot(
                id="shot01", act="", style="cinematic",
                folder="scenes", prompt="p", duration=5,
            )
        ]
        config = shot_runner.RunnerConfig(
            shots=shots,
            generate_one=generate_one,
            scenes_dir=scenes,
            progress=shot_runner.ProgressLog(tmp_path / "progress.txt"),
        )
        # Legacy API surface — ignored after G4 (pre-G4 this triggered a crop).
        config.aspect_ratio = "2.39:1"  # type: ignore[attr-defined]

        calls: list[list[str]] = []
        real_run = subprocess.run

        def fake_run(cmd, *args, **kwargs):
            if isinstance(cmd, (list, tuple)) and cmd and cmd[0] in ("ffmpeg", "ffprobe"):
                calls.append(list(cmd))
            return real_run(cmd, *args, **kwargs)

        with patch("subprocess.run", side_effect=fake_run):
            rc = shot_runner.run_shots(config)
        assert rc == 0
        assert not calls, f"production shelled out to ffmpeg/ffprobe: {calls}"

    def test_produce_aspect_ratio_prints_deprecation_notice(self, tmp_path: Path) -> None:
        """produce --aspect-ratio survives as a deprecated alias for one
        release: one-line migration notice, crop deferred to assembly."""
        runner = CliRunner(env={"ROOT": str(tmp_path)})
        # No shots file on purpose — the notice fires before any heavy work.
        result = runner.invoke(
            cli,
            ["produce", "test-proj", "--shots", "shots.json", "--aspect-ratio", "2.39:1"],
        )
        assert "deprecated" in result.output.lower()
        assert "stitch" in result.output


