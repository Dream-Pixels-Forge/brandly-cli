"""Issue #161: Agnes image --ratio rejects unsupported values at parse time.

Supported ratios (Agnes Image 2.5 Flash docs, 2026-09-29):
1:1, 3:4, 4:3, 16:9, 9:16, 2:3, 3:2, 21:9

ffmpeg-side crop ratios (stitch --ratio, export_platforms) are NOT Agnes
requests and stay unconstrained.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner

from brandly_cli.cli import cli


def _invoke(tmp_path: Path, args: list[str]) -> object:
    """Invoke the CLI with --root scoped to tmp so no repo files are touched."""
    return CliRunner().invoke(cli, ["--root", str(tmp_path), *args])


def test_image_ratio_rejects_unsupported_value(tmp_path: Path, monkeypatch) -> None:
    # Mock the transport so a (pre-fix) body execution can never hit the network.
    monkeypatch.setattr("brandly_cli.cmd.generation.generate_image", MagicMock())

    result = _invoke(tmp_path, ["image", "-p", "a cat", "--ratio", "4:5"])

    assert result.exit_code == 2
    assert "is not one of" in result.output


def test_reference_ratio_rejects_unsupported_value(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("brandly_cli.cmd.generation.generate_image", MagicMock())

    result = _invoke(
        tmp_path,
        [
            "reference",
            "proj-test",
            "--subject-type",
            "object",
            "--subject",
            "a ceramic mug",
            "--ratio",
            "4:5",
        ],
    )

    assert result.exit_code == 2
    assert "is not one of" in result.output


def test_image_help_lists_supported_ratios(tmp_path: Path) -> None:
    result = _invoke(tmp_path, ["image", "--help"])

    assert result.exit_code == 0
    for value in ("1:1", "3:4", "4:3", "16:9", "9:16", "2:3", "3:2", "21:9"):
        assert value in result.output
