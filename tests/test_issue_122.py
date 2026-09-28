"""Issue #122: produce/storyboard --dry-run.

Prints the flattened shot list (ids, scene, duration, resolved reference
paths, prompt preview, progress status) without spending credits, writing
plans, or touching the API. Plate resolution errors surface at dry-run time
with the same message the real run would raise.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli.cli import cli

PROJECT = "dryrun-proj"


def _setup(root: Path) -> Path:
    proj = root / ".brandly" / PROJECT
    (proj / "docs" / "plan").mkdir(parents=True)
    (proj / "docs" / "tmp").mkdir(parents=True)
    plate_dir = root / "pre-production" / PROJECT / "character"
    plate_dir.mkdir(parents=True)
    (plate_dir / "char_test.png").write_bytes(b"\x89PNG")
    shots = {
        "character": "Tester",
        "acts": {
            "scene1": {
                "scene": 1,
                "prefix": "INT. TEST",
                "style": "cinematic",
                "folder": "scenes",
                "shots": [
                    {
                        "id": "scene1-shot01",
                        "prompt": "A test shot",
                        "duration": 5,
                        "refs": ["char_test"],
                    },
                ],
            }
        },
    }
    path = root / "shots.json"
    path.write_text(json.dumps(shots), encoding="utf-8")
    return path


def _run(root: Path, *args: str):  # type: ignore[no-untyped-def]
    runner = CliRunner()
    return runner.invoke(cli, list(args), env={"ROOT": str(root)})


def test_produce_dry_run_prints_shots_no_writes(tmp_path: Path) -> None:
    shots_path = _setup(tmp_path)
    result = _run(
        tmp_path,
        "produce", PROJECT, "--shots", str(shots_path),
        "--no-auto-refs", "--dry-run",
    )
    assert result.exit_code == 0, result.output
    assert "scene1-shot01" in result.output
    assert "5s" in result.output or "5.0s" in result.output or "5 s" in result.output
    assert "char_test" in result.output
    assert "Dry run" in result.output or "dry run" in result.output.lower()
    # nothing was written: no scene manifest, no progress, no plans
    assert not (tmp_path / ".brandly" / PROJECT / "docs" / "plan" / "scenes.json").exists()
    assert not (tmp_path / ".brandly" / PROJECT / "docs" / "tmp" / "produce_progress.txt").exists()


def test_produce_dry_run_missing_plate_fails_closed(tmp_path: Path) -> None:
    shots_path = _setup(tmp_path)
    data = json.loads(shots_path.read_text(encoding="utf-8"))
    data["acts"]["scene1"]["shots"][0]["refs"] = ["char_missing"]
    shots_path.write_text(json.dumps(data), encoding="utf-8")
    result = _run(
        tmp_path,
        "produce", PROJECT, "--shots", str(shots_path),
        "--no-auto-refs", "--dry-run",
    )
    assert result.exit_code == 1
    assert "char_missing" in result.output


# #113's duplicate-id validation shipped, so this is a real assertion now:
# the dry run must surface the exact same error the real run would raise.
def test_produce_dry_run_duplicate_ids_error(tmp_path: Path) -> None:
    shots_path = _setup(tmp_path)
    data = json.loads(shots_path.read_text(encoding="utf-8"))
    data["acts"]["scene2"] = {
        "scene": 2,
        "shots": [{"id": "scene1-shot01", "prompt": "dupe", "duration": 4}],
    }
    shots_path.write_text(json.dumps(data), encoding="utf-8")
    result = _run(
        tmp_path,
        "produce", PROJECT, "--shots", str(shots_path),
        "--no-auto-refs", "--dry-run",
    )
    assert result.exit_code == 1
    assert "duplicate" in result.output.lower()


def test_storyboard_dry_run_prints_shots_no_writes(tmp_path: Path) -> None:
    shots_path = _setup(tmp_path)
    result = _run(
        tmp_path,
        "storyboard", PROJECT, "--shots", str(shots_path), "--dry-run",
    )
    assert result.exit_code == 0, result.output
    assert "scene1-shot01" in result.output
    assert "Dry run" in result.output or "dry run" in result.output.lower()
    assert not (tmp_path / ".brandly" / PROJECT / "docs" / "tmp" / "storyboard_progress.txt").exists()


def test_storyboard_dry_run_missing_plate_fails_closed(tmp_path: Path) -> None:
    shots_path = _setup(tmp_path)
    data = json.loads(shots_path.read_text(encoding="utf-8"))
    data["acts"]["scene1"]["shots"][0]["refs"] = ["char_missing"]
    shots_path.write_text(json.dumps(data), encoding="utf-8")
    result = _run(
        tmp_path,
        "storyboard", PROJECT, "--shots", str(shots_path), "--dry-run",
    )
    assert result.exit_code == 1
    assert "char_missing" in result.output
