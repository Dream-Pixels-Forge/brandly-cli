"""G7 PR 2 (issue #98, DEV-G7-003 confirmed): gate claim-lock + export logo
overlay — closes F9 gap 2 and flips `brand_kit` to supported.

Anti-drift rules under test:
* claims outside the kit's allowlist hard-fail the scene gate (deterministic,
  no heuristics);
* on-screen text fields without a registered value never block the gate;
* `export-platforms --brand` builds a deterministic ffmpeg overlay filter
  (corner / safe-zone / opacity from the kit) and fails closed when the kit
  or its logo is missing;
* the e2e dry-run path (monkeypatched ffmpeg) proves the full
  `brand verify` -> gate -> export flow.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli import brand_kit
from brandly_cli.brand_kit import BrandKit, OverlaySpec
from brandly_cli.cli import cli
from brandly_cli.cmd import gate as gate_cmd
from brandly_cli.export_platforms import (
    brand_overlay_position,
    build_export_cmd,
    export_for_platform,
)


def _kit(claims=("Save 30% today",)) -> BrandKit:
    return BrandKit(
        colors=("#123456",),
        claims=claims,
        style_lock="cinematic",
        logo="logo.png",
        overlay=OverlaySpec(),
    )


class TestClaimGate:
    def test_allowlisted_text_passes(self) -> None:
        assert brand_kit.brand_claim_issues(["Save 30% today"], _kit()) == []

    def test_offlist_text_fails(self) -> None:
        issues = brand_kit.brand_claim_issues(["Cheap deal!!"], _kit())
        assert issues == ["Cheap deal!!"]

    def test_blank_text_never_blocks(self) -> None:
        assert brand_kit.brand_claim_issues(["", "   "], _kit()) == []

    def test_apply_brand_claim_gate_fails_verdict(self) -> None:
        report = {"verdict": "pass"}
        gate_cmd.apply_brand_claim_gate(report, ["Discount 90% now"], _kit(), "test-proj")
        assert report["verdict"] == "fail"
        assert report["brand"]["violations"] == ["Discount 90% now"]

    def test_apply_brand_claim_gate_clean_report_untouched(self) -> None:
        report = {"verdict": "pass"}
        gate_cmd.apply_brand_claim_gate(report, [], _kit(), "test-proj")
        assert report["verdict"] == "pass"
        assert report["brand"]["violations"] == []


class TestExportBrandOverlay:
    def test_overlay_position_deterministic(self) -> None:
        width, height = 1080, 1920
        spec = OverlaySpec(corner="bottom-right", safe_zone=0.1, opacity=1.0)
        x, y = brand_overlay_position(width, height, spec)
        assert x == f"W-w-{int(0.1 * width)}"
        assert y == f"H-h-{int(0.1 * height)}"
        tl = brand_overlay_position(width, height, OverlaySpec(corner="top-left"))
        assert tl == (str(int(0.1 * width)), str(int(0.1 * height)))

    def test_build_cmd_with_brand_overlay(self) -> None:
        spec = OverlaySpec(corner="top-right", safe_zone=0.05, opacity=0.8)
        cmd = build_export_cmd(
            input_video=Path("in.mp4"),
            output_path=Path("out.mp4"),
            duration=30.0,
            filter_parts=["crop=1080:1920:0:0"],
            brand_logo=Path("logo.png"),
            brand_overlay=spec,
            target_dims=(1080, 1920),
        )
        joined = " ".join(cmd)
        assert str(Path("logo.png")) in joined
        assert "-filter_complex" in cmd
        assert "overlay=W-w-" in joined
        assert "colorchannelmixer=aa=0.8" in joined
        assert "[vout]" in joined

    def test_build_cmd_without_brand_keeps_plain_vf(self) -> None:
        cmd = build_export_cmd(
            input_video=Path("in.mp4"),
            output_path=Path("out.mp4"),
            duration=30.0,
            filter_parts=["crop=1:1:0:0"],
            brand_logo=None,
            brand_overlay=None,
            target_dims=None,
        )
        assert "-filter_complex" not in cmd
        assert "-vf" in cmd

    def test_export_missing_logo_fails_closed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import brandly_cli.export_platforms as ep

        monkeypatch.setattr(ep, "_ffmpeg_available", lambda: True)
        video = tmp_path / "in.mp4"
        video.write_bytes(b"\x00\x00")
        result = asyncio.run(
            export_for_platform(
                video,
                "tiktok",
                tmp_path / "out",
                fit="pad",
                brand_logo=str(tmp_path / "nope.png"),
                brand_overlay=OverlaySpec(),
            )
        )
        assert "error" in result and "logo" in result["error"].lower()

    def test_cli_export_brand_without_kit_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        proj = tmp_path / ".brandly" / "p"
        (proj / "videos").mkdir(parents=True)
        (proj / "videos" / "scene.mp4").write_bytes(b"\x00")
        (proj / "project.json").write_text('{"id": "p"}')
        result = CliRunner().invoke(
            cli,
            [
                "export-platforms",
                "p",
                "--platforms",
                "tiktok",
                "--brand",
                "--root",
                str(tmp_path),
            ],
        )
        assert result.exit_code != 0
        assert "brand" in result.output.lower()


class TestE2eDryRun:
    """G7 e2e proof: verify + gate claim-lock + export overlay, no network."""

    def test_full_flow_dry_run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        proj_dir = tmp_path / ".brandly" / "p"
        (proj_dir / "videos").mkdir(parents=True)
        (proj_dir / "videos" / "scene.mp4").write_bytes(b"\x00")
        (proj_dir / "project.json").write_text('{"id": "p"}')
        (proj_dir / "logo.png").write_bytes(b"\x89PNG-fake")
        kit = _kit()
        brand_kit.save_brand_kit(proj_dir, kit)
        assert brand_kit.verify_kit(kit, proj_dir) == []

        # gate layer: allowlisted claim keeps the verdict
        report = {"verdict": "pass"}
        gate_cmd.apply_brand_claim_gate(report, ["Save 30% today"], kit, "p")
        assert report["verdict"] == "pass"
        failing = {"verdict": "pass"}
        gate_cmd.apply_brand_claim_gate(failing, ["Discount 90% now"], kit, "p")
        assert failing["verdict"] == "fail"

        # export layer: command carries the overlay, no ffmpeg invocation
        import brandly_cli.export_platforms as ep

        captured: list[list[str]] = []

        async def fake_run(cmd: list[str]):
            captured.append(cmd)
            return (0, "")

        monkeypatch.setattr(ep, "_ffmpeg_available", lambda: True)
        monkeypatch.setattr(ep, "_run_ffmpeg", fake_run)
        monkeypatch.setattr(ep, "_get_duration", lambda p: 12.0)

        result = asyncio.run(
            export_for_platform(
                proj_dir / "videos" / "scene.mp4",
                "tiktok",
                proj_dir / "export",
                fit="pad",
                brand_logo=str(proj_dir / "logo.png"),
                brand_overlay=kit.overlay,
            )
        )
        assert "error" not in result, result
        joined = " ".join(captured[0])
        assert "logo.png" in joined and "overlay=" in joined
