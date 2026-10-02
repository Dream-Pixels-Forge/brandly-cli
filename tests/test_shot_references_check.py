r"""Pre-flight reference check for the shot list.

Covers ``shot_runner.check_shot_references`` (does every shot resolve the
references it needs, aggregated in one pass instead of failing on the first
miss) and the ``brandly produce --check`` command surface.

Run under .venv\Scripts\python (editable install points at src/).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from PIL import Image

from brandly_cli import shot_runner
from brandly_cli.cli import cli
from brandly_cli.utils import generate_project_id

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    return tmp_path / ".brandly"


@pytest.fixture
def runner(project_dir: Path, tmp_path: Path) -> CliRunner:
    import os

    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _write_project(project_dir: Path, project_id: str) -> None:
    proj_file = project_dir / project_id / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    proj_file.write_text(json.dumps({"id": project_id, "name": "Test"}))


def _add_plate(project_dir: Path, pid: str, category: str, name: str) -> Path:
    p = project_dir.parent / "pre-production" / pid / category / name
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), (20, 20, 20)).save(p, "PNG")
    return p


def _write_shots_file(tmp_path: Path, data: Any, name: str = "shots.json") -> Path:
    f = tmp_path / name
    f.write_text(json.dumps(data))
    return f


def _images_dir(tmp_path: Path, pid: str) -> Path:
    return tmp_path / "pre-production" / pid


# ---------------------------------------------------------------------------
# shot_runner.check_shot_references (pure pre-flight)
# ---------------------------------------------------------------------------


class TestCheckShotReferences:
    def test_all_stems_resolve_reports_empty(self, project_dir: Path, tmp_path: Path) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_plate(project_dir, pid, "character", "char_a.opt.jpg")
        _add_plate(project_dir, pid, "location", "loc_x.png")
        data = {
            "acts": {
                "act1": {
                    "shots": [
                        {"id": "s1", "prompt": "p", "refs": ["char_a", "loc_x"]},
                    ]
                }
            }
        }
        assert shot_runner.check_shot_references(data, _images_dir(tmp_path, pid)) == []

    def test_single_missing_stem_reported_with_context(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_plate(project_dir, pid, "character", "char_a.opt.jpg")
        data = {
            "acts": {
                "act1": {
                    "name": "ACT I",
                    "shots": [
                        {"id": "s1", "prompt": "p", "refs": ["char_a", "ghost"]},
                    ]
                }
            }
        }
        missing = shot_runner.check_shot_references(data, _images_dir(tmp_path, pid))
        assert len(missing) == 1
        m = missing[0]
        assert m.entry == "ghost"
        assert m.shot_id == "s1"
        assert m.act == "ACT I"
        assert m.scene == 1
        assert "ghost" in m.reason

    def test_aggregates_every_missing_across_shots_and_acts(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_plate(project_dir, pid, "character", "char_a.opt.jpg")
        data = {
            "acts": {
                "act1": {
                    "shots": [
                        {"id": "s1", "prompt": "p", "refs": ["ghost_a", "ghost_b"]},
                        {"id": "s2", "prompt": "p", "refs": ["char_a", "ghost_c"]},
                    ]
                },
                "act2": {
                    "shots": [
                        {"id": "s3", "prompt": "p", "refs": ["ghost_d"]},
                    ]
                },
            }
        }
        missing = shot_runner.check_shot_references(data, _images_dir(tmp_path, pid))
        by_entry = {m.entry for m in missing}
        # Every miss is surfaced in one pass - none is hidden behind the first.
        assert by_entry == {"ghost_a", "ghost_b", "ghost_c", "ghost_d"}
        assert {m.shot_id for m in missing} == {"s1", "s2", "s3"}

    def test_explicit_path_and_url_entries_are_not_flagged(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        local = _add_plate(project_dir, pid, "prop", "prop_1.jpg")
        data = {
            "acts": {
                "act1": {
                    "shots": [
                        {"id": "s1", "prompt": "p",
                         "refs": [str(local), "https://cdn.example/x.png"]},
                    ]
                }
            }
        }
        assert shot_runner.check_shot_references(data, _images_dir(tmp_path, pid)) == []

    def test_flat_list_input_supported(self, project_dir: Path, tmp_path: Path) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        data = [
            {"name": "shot-1", "prompt": "p", "refs": ["nope"]},
            {"name": "shot-2", "prompt": "p"},
        ]
        missing = shot_runner.check_shot_references(data, _images_dir(tmp_path, pid))
        assert [m.entry for m in missing] == ["nope"]
        assert all(m.shot_id.startswith("shot-") for m in missing)

    def test_act_level_ref_falls_back_and_flags_the_shot(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        data = {
            "acts": {
                "act1": {
                    "refs": ["ghost_act"],
                    "shots": [
                        {"id": "s1", "prompt": "p"},
                        {"id": "s2", "prompt": "p"},
                    ],
                }
            }
        }
        missing = shot_runner.check_shot_references(data, _images_dir(tmp_path, pid))
        assert [(m.shot_id, m.entry) for m in missing] == [
            ("s1", "ghost_act"),
            ("s2", "ghost_act"),
        ]

    def test_explicit_empty_shot_refs_opt_out_of_act_refs(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        data = {
            "acts": {
                "act1": {
                    "refs": ["ghost_act"],
                    "shots": [
                        {"id": "s1", "prompt": "p", "refs": []},
                        {"id": "s2", "prompt": "p"},
                    ],
                }
            }
        }
        missing = shot_runner.check_shot_references(data, _images_dir(tmp_path, pid))
        assert [(m.shot_id, m.entry) for m in missing] == [("s2", "ghost_act")]


# ---------------------------------------------------------------------------
# CLI: brandly produce --check
# ---------------------------------------------------------------------------


class TestProduceCheckCli:
    def test_check_lists_every_missing_and_exits_1(
        self,
        runner: CliRunner,
        project_dir: Path,
        tmp_path: Path,
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_plate(project_dir, pid, "character", "char_a.opt.jpg")
        shots = _write_shots_file(
            tmp_path,
            {
                "acts": {
                    "act1": {
                        "shots": [
                            {"id": "s1", "prompt": "p", "refs": ["char_a", "ghost"]},
                        ]
                    }
                }
            },
        )
        result = runner.invoke(
            cli, ["produce", pid, "--shots", str(shots), "--check", "--interval", "0"]
        )
        assert result.exit_code == 1, result.output
        assert "ghost" in result.output
        assert "could not be resolved" in result.output
        # Pure validation: no scene manifest, no generation happened.
        scenes = project_dir / pid / "docs" / "plan" / "scenes.json"
        assert not scenes.exists()

    def test_check_clean_exits_0(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_plate(project_dir, pid, "character", "char_a.opt.jpg")
        shots = _write_shots_file(
            tmp_path,
            {"acts": {"act1": {"shots": [{"id": "s1", "prompt": "p", "refs": ["char_a"]}]}}},
        )
        result = runner.invoke(
            cli, ["produce", pid, "--shots", str(shots), "--check", "--interval", "0"]
        )
        assert result.exit_code == 0, result.output
        assert "resolve" in result.output

    def test_produce_without_check_fails_fast_aggregated(
        self,
        runner: CliRunner,
        project_dir: Path,
        tmp_path: Path,
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_plate(project_dir, pid, "character", "char_a.opt.jpg")
        shots = _write_shots_file(
            tmp_path,
            {
                "acts": {
                    "act1": {
                        "shots": [
                            {"id": "s1", "prompt": "p", "refs": ["ghost_a"]},
                            {"id": "s2", "prompt": "p", "refs": ["ghost_b"]},
                        ]
                    }
                }
            },
        )
        result = runner.invoke(
            cli, ["produce", pid, "--shots", str(shots), "--interval", "0"]
        )
        assert result.exit_code == 1, result.output
        # Both misses are listed up front (not just the first), no traceback.
        assert "ghost_a" in result.output
        assert "ghost_b" in result.output
        assert "Traceback" not in result.output
