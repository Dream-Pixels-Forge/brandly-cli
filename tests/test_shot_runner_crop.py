"""Regression tests: aspect-ratio crop axis + Windows rename retry (shot_runner).

RED-first tests for the stashed ``shot_runner`` fix (crop-windows-rename):

1. ``apply_aspect_ratio`` crops the WRONG axis on wide sources. A 1280x720
   (16:9 = 1.78) clip cropped to 2.39:1 is a WIDER target — the source is
   NARROWER than the target, so height must shrink (``crop=1280:H`` with
   H < 720). The old code cropped width instead (``crop=W:720`` with
   W > 1280 — overshooting the source) and computed a bogus height
   (``ratio * 0.5`` — pixels from a unitless ratio, always ~2px).
2. ``name_clips`` retries ``Path.replace`` on Windows ``PermissionError``
   (gate/player/AV briefly holding the fresh download) instead of failing
   on the first locked-file error.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from brandly_cli import shot_runner


def _run_ok(probe_dims: str):
    def fake_run(cmd, **kwargs):
        if cmd[0] == "ffprobe":
            return subprocess.CompletedProcess(cmd, 0, stdout=probe_dims, stderr="")
        out = Path(cmd[-1])
        out.write_bytes(b"cropped")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return fake_run


class TestCropAxis:
    def test_wide_source_to_wider_target_crops_height(self, tmp_path: Path) -> None:
        """1280x720 (1.78) -> 2.39:1 must shrink HEIGHT, keep full width."""
        clip = tmp_path / "test.mp4"
        clip.write_bytes(b"fake")
        captured: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured.append(cmd)
            return _run_ok("1280,720\n")(cmd, **kwargs)

        with patch("subprocess.run", side_effect=fake_run):
            assert shot_runner.apply_aspect_ratio(clip, "2.39:1") is True

        vf = next(c for c in captured if c[0] == "ffmpeg")
        crop = vf[vf.index("-vf") + 1].split("crop=")[1].split(",")[0]
        w_s, h_s = crop.split(":")[:2]
        assert int(w_s) <= 1280, f"crop width overshoots source: {crop}"
        assert int(h_s) < 720, f"height must shrink: {crop}"

    def test_wider_source_to_narrow_target_crops_width(self, tmp_path: Path) -> None:
        """2390x1000 (2.39) -> 16:9 must shrink WIDTH, keep full height."""
        clip = tmp_path / "test.mp4"
        clip.write_bytes(b"fake")
        captured: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured.append(cmd)
            return _run_ok("2390,1000\n")(cmd, **kwargs)

        with patch("subprocess.run", side_effect=fake_run):
            assert shot_runner.apply_aspect_ratio(clip, "16:9") is True

        vf = next(c for c in captured if c[0] == "ffmpeg")
        crop = vf[vf.index("-vf") + 1].split("crop=")[1].split(",")[0]
        w_s, h_s = crop.split(":")[:2]
        assert int(w_s) < 2390, f"width must shrink: {crop}"
        assert int(h_s) <= 1000, f"crop height overshoots source: {crop}"


class TestNameClipsWindowsRetry:
    def test_retries_replace_on_permission_error(self, tmp_path: Path) -> None:
        from brandly_cli.shot_runner import Shot

        shot = Shot(id="s1", act="act1", style="cine", folder="scenes",
                    prompt="p", duration=5, scene=1, index_in_scene=1)
        src = tmp_path / "raw_dl.mp4"
        src.write_bytes(b"clip")
        attempts = {"n": 0}
        real_replace = Path.replace

        def flaky_replace(self, target):
            if self == src and attempts["n"] < 2:
                attempts["n"] += 1
                raise PermissionError("file locked by AV")
            return real_replace(self, target)

        with patch.object(Path, "replace", flaky_replace):
            renamed = shot_runner.name_clips(shot, [src], say=None)
        assert attempts["n"] == 2, "must retry locked renames"
        assert renamed[0].is_file()
