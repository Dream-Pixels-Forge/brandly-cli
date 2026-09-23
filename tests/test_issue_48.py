"""Regression tests for issue #48: --aspect-ratio crop failure on Windows.

Root cause
----------
``apply_aspect_ratio`` builds a vf expression with a bare Python-float ratio
inside ffmpeg's ``trunc(...)`` filter, and runs ffmpeg with ``-c:a copy``
which the crosstool-NG/MSYS2 ffmpeg build rejects. The function swallows the
ffmpeg stderr and reports ``crop failed`` but the *shot* is still marked OK
(per issue #37's post-gen tolerance), so the user sees no actionable error
and the clip stays uncropped.

Fix
---
- Use integer pixel values (no bare float in the filter expression).
- Re-encode audio to AAC instead of ``-c:a copy`` (portable across builds).
- Add a ``strict`` mode: when the caller passes ``strict=True``, a crop
  failure returns ``False`` AND the caller is expected to mark the shot
  FAILED (not silently OK). The caller (cmd/generation.py) must thread
  this through so a failed crop surfaces.
- Capture and surface stderr on failure.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from brandly_cli import shot_runner


class TestApplyAspectRatioStrictMode:
    """A crop failure in strict mode must be clearly signalled."""

    def test_strict_mode_returns_false_on_failure(self, tmp_path: Path) -> None:
        clip = tmp_path / "test.mp4"
        clip.write_bytes(b"fake")

        # ffprobe succeeds (returns dims), ffmpeg fails.
        def fake_run(cmd, **kwargs):
            if cmd and cmd[0] == "ffprobe":
                return subprocess.CompletedProcess(
                    cmd, 0, stdout="1280,720\n", stderr=""
                )
            return subprocess.CompletedProcess(
                cmd, 1, stdout="", stderr="vf pipeline error: Invalid argument"
            )

        with patch("subprocess.run", side_effect=fake_run) as mock_run:
            result = shot_runner.apply_aspect_ratio(
                clip, "2.39:1", strict=True
            )
            assert result is False

        # ffmpeg was called with the new portable command (AAC, no -c:a copy)
        ffmpeg_calls = [
            c for c in mock_run.call_args_list
            if c[0][0] and c[0][0][0] == "ffmpeg"
        ]
        assert ffmpeg_calls, "ffmpeg was not invoked"
        call_args = ffmpeg_calls[0][0][0]
        assert "-c:a" in call_args
        assert "aac" in call_args
        assert "copy" not in call_args  # no more -c:a copy

    def test_strict_mode_surfaces_stderr_via_say(self, tmp_path: Path) -> None:
        clip = tmp_path / "test.mp4"
        clip.write_bytes(b"fake")

        messages: list[str] = []

        def fake_run(cmd, **kwargs):
            if cmd and cmd[0] == "ffprobe":
                return subprocess.CompletedProcess(cmd, 0, stdout="1280,720\n", stderr="")
            return subprocess.CompletedProcess(
                cmd, 1, stdout="", stderr="ffmpeg: vf crop=... Invalid argument"
            )

        with patch("subprocess.run", side_effect=fake_run):
            result = shot_runner.apply_aspect_ratio(
                clip, "2.39:1", say=messages.append, strict=True
            )
        assert result is False
        assert any("crop failed" in m for m in messages)
        assert any("Invalid argument" in m for m in messages)

    def test_non_strict_mode_keeps_backward_compat(self, tmp_path: Path) -> None:
        """When strict is not requested (default), a failure just returns
        False and says a warning — the caller decides what to do."""
        clip = tmp_path / "test.mp4"
        clip.write_bytes(b"fake")

        messages: list[str] = []

        def fake_run(cmd, **kwargs):
            if cmd and cmd[0] == "ffprobe":
                return subprocess.CompletedProcess(cmd, 0, stdout="1280,720\n", stderr="")
            return subprocess.CompletedProcess(
                cmd, 1, stdout="", stderr="something went wrong"
            )

        with patch("subprocess.run", side_effect=fake_run):
            result = shot_runner.apply_aspect_ratio(
                clip, "2.39:1", say=messages.append, strict=False
            )
        assert result is False
        assert any("crop failed" in m for m in messages)


class TestApplyAspectRatioCommandShape:
    """The ffmpeg command must use portable flags (no -c:a copy, integer
    crop values) so it works across ffmpeg builds."""

    def _probe_ok(self, w: int = 1280, h: int = 720):
        """A patch helper: ffprobe returns given dimensions, ffmpeg succeeds."""
        def fake_run(cmd, **kwargs):
            if cmd[0] == "ffprobe":
                return subprocess.CompletedProcess(
                    cmd, 0, stdout=f"{w},{h}\n", stderr=""
                )
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return fake_run

    def test_vfilter_uses_integer_crop_values(self, tmp_path: Path) -> None:
        """The crop filter must use a concrete integer, not a bare float
        expression that some ffmpeg builds reject."""
        clip = tmp_path / "test.mp4"
        clip.write_bytes(b"fake")

        captured: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            captured.append(cmd)
            if cmd[0] == "ffprobe":
                return subprocess.CompletedProcess(
                    cmd, 0, stdout="1280,720\n", stderr=""
                )
            # ffmpeg: pretend success by writing a stub
            out = Path(cmd[-1])
            out.write_bytes(b"cropped")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=fake_run):
            shot_runner.apply_aspect_ratio(clip, "2.39:1")

        # Find the ffmpeg call
        ffmpeg_calls = [c for c in captured if c and c[0] == "ffmpeg"]
        assert ffmpeg_calls, "ffmpeg was not invoked"
        vf = ffmpeg_calls[0][ffmpeg_calls[0].index("-vf") + 1]
        # The crop expression must contain integer pixel values, not a
        # bare float like "2.39" or "iw/2.39"
        assert "crop=" in vf
        # Extract the crop dimensions: crop=w:h:x:y
        crop_expr = vf.split("crop=")[1].split(",")[0]
        w_expr, h_expr = crop_expr.split(":")[:2]
        # w should be "iw" or an int; h should be an int (not a float expr)
        # The key: no bare decimal float like "2.39" should appear
        assert "2.39" not in h_expr, f"bare float ratio leaked into h: {h_expr}"

    def test_audio_reencoded_not_copied(self, tmp_path: Path) -> None:
        """-c:a must be 'aac' (portable), not 'copy' (build-dependent)."""
        clip = tmp_path / "test.mp4"
        clip.write_bytes(b"fake")

        def fake_run(cmd, **kwargs):
            if cmd[0] == "ffprobe":
                return subprocess.CompletedProcess(
                    cmd, 0, stdout="1280,720\n", stderr=""
                )
            out = Path(cmd[-1])
            out.write_bytes(b"cropped")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        captured: list[list[str]] = []
        with patch("subprocess.run", side_effect=lambda c, **k: (captured.append(c) or fake_run(c, **k))):
            shot_runner.apply_aspect_ratio(clip, "2.39:1")

        ffmpeg_calls = [c for c in captured if c and c[0] == "ffmpeg"]
        assert ffmpeg_calls
        cmd = ffmpeg_calls[0]
        ca = cmd[cmd.index("-c:a") + 1]
        assert ca == "aac", f"expected 'aac' but got '{ca}'"
