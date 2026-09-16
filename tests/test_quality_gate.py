"""Tests for the quality gate (quality_gate.py) and the `brandly gate` command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from brandly_cli import quality_gate
from brandly_cli.cli import cli


@pytest.fixture
def runner(tmp_path: Path) -> CliRunner:
    import os

    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _run(coro):
    import asyncio

    return asyncio.run(coro)


class TestGatePrechecks:
    def test_missing_element_fails(self, tmp_path: Path) -> None:
        result = _run(quality_gate.verify_element(tmp_path / "nope.png", use_ai=False))
        assert result.status == quality_gate.FAIL
        assert result.issues

    def test_blank_solid_image_fails_entropy(self, tmp_path: Path) -> None:
        from PIL import Image

        p = tmp_path / "blank.png"
        Image.new("RGB", (512, 288), (120, 120, 120)).save(p)
        result = _run(quality_gate.verify_element(p, use_ai=False))
        assert result.status == quality_gate.FAIL
        assert any("blank" in i.lower() or "failed generation" in i for i in result.issues)

    def test_good_image_with_content_passes(self, tmp_path: Path) -> None:
        from PIL import Image

        p = tmp_path / "sheet.png"
        im = Image.new("RGB", (512, 288), (150, 150, 150))
        px = im.load()
        for x in range(200, 312):
            for y in range(80, 208):
                px[x, y] = (30, 30, 35)  # a dark subject block in the center
        im.save(p)
        result = _run(quality_gate.verify_element(p, use_ai=False))
        assert result.status in (quality_gate.PASS, quality_gate.WARN)

    def test_corrupt_image_fails(self, tmp_path: Path) -> None:
        p = tmp_path / "corrupt.png"
        p.write_bytes(b"this is not a png")
        result = _run(quality_gate.verify_element(p, use_ai=False))
        assert result.status == quality_gate.FAIL


class TestGateAiVerdictMapping:
    def test_apply_verdict_fail_distortion(self) -> None:
        result = quality_gate.GateResult(element="x", kind="image")
        verdict = {
            "quality_score": 40,
            "slop": 8,
            "distortion": 7,
            "drift": 2,
            "matte_background": False,
            "issues": ["melted face"],
            "verdict": "fail",
            "notes": "bad",
        }
        quality_gate._apply_ai_verdict(
            result, verdict, expect_matt_background=True, has_reference=True
        )
        assert result.status == quality_gate.FAIL
        assert result.score == 40
        assert "melted face" in result.issues
        assert any("slop" in i for i in result.issues)
        assert any("distortion" in i for i in result.issues)

    def test_apply_verdict_pass(self) -> None:
        result = quality_gate.GateResult(element="x", kind="image")
        verdict = {
            "quality_score": 95,
            "slop": 0,
            "distortion": 0,
            "drift": 1,
            "matte_background": True,
            "issues": [],
            "verdict": "pass",
            "notes": "good",
        }
        quality_gate._apply_ai_verdict(
            result, verdict, expect_matt_background=True, has_reference=True
        )
        assert result.status == quality_gate.PASS
        assert result.score == 95
        assert not result.issues

    def test_apply_verdict_unparseable_warns(self) -> None:
        result = quality_gate.GateResult(element="x", kind="image")
        quality_gate._apply_ai_verdict(
            result, {}, expect_matt_background=False, has_reference=False
        )
        assert result.status == quality_gate.WARN


class TestGateCommand:
    def test_gate_invalid_project_id(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["gate", "bad id", "x.png"])
        assert result.exit_code == 1
        assert "Invalid project ID" in result.output

    def test_gate_no_element(self, runner: CliRunner, tmp_path: Path) -> None:
        # no project / no media yet
        result = runner.invoke(cli, ["gate", "my-project"], catch_exceptions=False)
        assert result.exit_code == 2

    def test_gate_element_path(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AGNES_API_KEY", "test-key")
        from PIL import Image

        media = tmp_path / "img.png"
        im = Image.new("RGB", (512, 288), (150, 150, 150))
        px = im.load()
        for x in range(200, 312):
            for y in range(80, 208):
                px[x, y] = (30, 30, 35)
        im.save(media)

        with patch(
            "brandly_cli.quality_gate._run_vision_check",
            AsyncMock(return_value={
                "quality_score": 92,
                "slop": 1,
                "distortion": 0,
                "drift": None,
                "matte_background": True,
                "issues": [],
                "verdict": "pass",
                "notes": "great",
            }),
        ):
            result = runner.invoke(
                cli,
                ["gate", "my-project", str(media), "-d", "a red widget"],
            )
        assert result.exit_code == 0, result.output
        assert "GATE PASS" in result.output


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
