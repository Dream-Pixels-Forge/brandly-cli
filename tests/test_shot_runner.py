r"""Tests for the ``brandly produce`` progress-file shot runner
(shot_runner module + CLI routing).

Run under .venv\Scripts\python (editable install points at src/).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from PIL import Image

from brandly_cli import shot_runner
from brandly_cli.cli import cli
from brandly_cli.utils import _read_production_plan_rows, generate_project_id, production_plan_path

# ---------------------------------------------------------------------------
# Fixtures / helpers
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
    p = project_dir / pid / "images" / category / name
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), (10, 10, 10)).save(p, "PNG")
    return p


def _write_shots_file(tmp_path: Path, data: Any, name: str = "shots.json") -> Path:
    f = tmp_path / name
    f.write_text(json.dumps(data))
    return f


# ---------------------------------------------------------------------------
# resolve_plate
# ---------------------------------------------------------------------------


class TestResolvePlate:
    def test_prefers_optimized_twin(self, project_dir: Path, tmp_path: Path) -> None:
        pid = generate_project_id()
        _add_plate(project_dir, pid, "character", "char_a.jpg")
        _add_plate(project_dir, pid, "character", "char_a.opt.jpg")
        path = shot_runner.resolve_plate("char_a", project_dir / pid / "images")
        assert path.name == "char_a.opt.jpg"

    def test_falls_back_to_plain_image(self, project_dir: Path, tmp_path: Path) -> None:
        pid = generate_project_id()
        _add_plate(project_dir, pid, "location", "loc_x.png")
        path = shot_runner.resolve_plate("loc_x", project_dir / pid / "images")
        assert path.name == "loc_x.png"

    def test_searches_all_categories(self, project_dir: Path, tmp_path: Path) -> None:
        pid = generate_project_id()
        _add_plate(project_dir, pid, "prop", "prop_1.jpg")
        path = shot_runner.resolve_plate("prop_1", project_dir / pid / "images")
        assert path.parent.name == "prop"

    def test_missing_plate_raises(self, project_dir: Path, tmp_path: Path) -> None:
        _add_plate(project_dir, "x", "character", "c.png")
        with pytest.raises(FileNotFoundError):
            shot_runner.resolve_plate("ghost", project_dir / "x" / "images")


# ---------------------------------------------------------------------------
# flatten_shots
# ---------------------------------------------------------------------------


class TestFlattenShots:
    def test_structured_act_prefix_style_folder_and_refs(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _add_plate(project_dir, pid, "character", "char_rebel.opt.jpg")
        _add_plate(project_dir, pid, "location", "loc_ink.opt.jpg")
        data = {
            "character": "natural afro, ink wash",
            "acts": {
                "act1": {
                    "name": "ACT I",
                    "prefix": "Ink world: ",
                    "style": "cinematic",
                    "folder": "scenes",
                    "shots": [
                        {"id": "shot01", "prompt": "wide", "duration": 6,
                         "refs": ["char_rebel", "loc_ink"]},
                    ],
                },
                "transition12": {
                    "name": "TRANS",
                    "style": "cinematic",
                    "folder": "transition",
                    "shots": [
                        {"id": "trans12", "prompt": "vortex", "duration": 4,
                         "refs": ["char_rebel"]},
                    ],
                },
            },
        }
        shots = shot_runner.flatten_shots(data, project_dir / pid / "images")
        assert [s.id for s in shots] == ["shot01", "trans12"]
        s1, t12 = shots
        assert s1.prompt == "Ink world: wide"
        assert s1.style == "cinematic"
        assert s1.folder == "scenes"
        assert s1.duration == 6
        assert all(Path(r).name == "char_rebel.opt.jpg" for r in s1.refs[:1])
        assert s1.character == "natural afro, ink wash"
        assert t12.folder == "transition"
        assert t12.character == "natural afro, ink wash"

    def test_shot_without_character_plate_stays_anchor_free(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _add_plate(project_dir, pid, "location", "loc_real.opt.jpg")
        data = {
            "character": "global anchor",
            "acts": {
                "act3": {
                    "shots": [
                        {"id": "shot32", "prompt": "title", "refs": ["loc_real"]},
                    ],
                },
            },
        }
        (shot,) = shot_runner.flatten_shots(data, project_dir / pid / "images")
        assert shot.character is None

    def test_per_shot_character_wins_over_global(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _add_plate(project_dir, pid, "character", "char_a.opt.jpg")
        data = {
            "character": "global",
            "acts": {
                "a": {
                    "shots": [
                        {"id": "s1", "prompt": "x", "refs": ["char_a"],
                         "character": "per-shot"},
                    ],
                },
            },
        }
        (shot,) = shot_runner.flatten_shots(data, project_dir / pid / "images")
        assert shot.character == "per-shot"

    def test_cli_character_argument_wins_over_global(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _add_plate(project_dir, pid, "character", "char_a.opt.jpg")
        data = {
            "character": "global",
            "acts": {
                "a": {"shots": [{"id": "s1", "prompt": "x", "refs": ["char_a"]}]},
            },
        }
        (shot,) = shot_runner.flatten_shots(
            data, project_dir / pid / "images", character="cli"
        )
        assert shot.character == "cli"

    def test_flat_schema_file_refs_pass_through(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        data = [
            {"name": "shot-1", "prompt": "establishing", "duration": 5,
             "references": "plates/a.png"},
        ]
        (shot,) = shot_runner.flatten_shots(data, project_dir / "p" / "images")
        assert shot.refs == ["plates/a.png"]
        assert shot.prompt == "establishing"
        assert shot.style == "cinematic"  # default

    def test_string_references_split_on_comma(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        data = [
            {"name": "shot-1", "prompt": "x", "references": "a.png, b.png"},
        ]
        (shot,) = shot_runner.flatten_shots(data, project_dir / "p" / "images")
        assert shot.refs == ["a.png", "b.png"]

    def test_missing_plate_fails_with_clear_error(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        data = {"acts": {"a": {"shots": [{"id": "s", "prompt": "x", "refs": ["ghost"]}]}}}
        with pytest.raises(FileNotFoundError, match="ghost"):
            shot_runner.flatten_shots(data, project_dir / "p" / "images")

    def test_scene_and_shot_numbering_follow_act_order(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        data = {
            "acts": {
                "act1": {
                    "shots": [
                        {"id": "shot01", "prompt": "a"},
                        {"id": "shot02", "prompt": "b"},
                        {"id": "shot03", "prompt": "c"},
                        {"id": "shot04", "prompt": "d"},
                    ],
                },
                "act2": {"shots": [{"id": "shot05", "prompt": "e"}]},
            },
        }
        shots = shot_runner.flatten_shots(data, project_dir / "p" / "images")
        assert [(s.scene, s.index_in_scene) for s in shots] == [
            (1, 1),
            (1, 2),
            (1, 3),
            (1, 4),
            (2, 1),
        ]
        assert [s.clip_name for s in shots] == [
            "Scene-01-Shot-1-1.mp4",
            "Scene-01-Shot-1-2.mp4",
            "Scene-01-Shot-1-3.mp4",
            "Scene-01-Shot-1-4.mp4",
            "Scene-02-Shot-2-1.mp4",
        ]

    def test_flat_list_defaults_to_scene_one(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        data = [
            {"name": "shot-1", "prompt": "a"},
            {"name": "shot-2", "prompt": "b"},
            {"name": "shot-3", "prompt": "c"},
        ]
        shots = shot_runner.flatten_shots(data, project_dir / "p" / "images")
        assert [(s.scene, s.index_in_scene) for s in shots] == [(1, 1), (1, 2), (1, 3)]

    def test_explicit_scene_overrides_act_order(
        self, project_dir: Path, tmp_path: Path
    ) -> None:
        data = {
            "acts": {
                "a": {"scene": 7, "shots": [{"id": "s1", "prompt": "x"}]},
                "b": {
                    "shots": [
                        {"id": "s2", "prompt": "y"},
                        {"id": "s3", "prompt": "z", "scene": 9},
                    ],
                },
            },
        }
        shots = shot_runner.flatten_shots(data, project_dir / "p" / "images")
        assert [(s.scene, s.index_in_scene) for s in shots] == [(7, 1), (2, 1), (9, 2)]


# ---------------------------------------------------------------------------
# Generated-clip naming convention
# ---------------------------------------------------------------------------


class TestClipNaming:
    def test_clip_filename_convention(self) -> None:
        assert shot_runner.clip_filename(1, 1) == "Scene-01-Shot-1-1.mp4"
        assert shot_runner.clip_filename(2, 3) == "Scene-02-Shot-2-3.mp4"
        assert shot_runner.clip_filename(12, 4) == "Scene-12-Shot-12-4.mp4"


# ---------------------------------------------------------------------------
# ProgressLog + run_shots
# ---------------------------------------------------------------------------


def _make_config(
    tmp_path: Path,
    shots: list[shot_runner.Shot],
    generate_one,
    interval: float = 0.0,
    only=None,
    max_shots: int = 0,
) -> shot_runner.RunnerConfig:
    scenes = tmp_path / "videos" / "scenes"
    scenes.mkdir(parents=True, exist_ok=True)
    progress = shot_runner.ProgressLog(tmp_path / "docs" / "tmp" / "produce_progress.txt")
    return shot_runner.RunnerConfig(
        shots=shots,
        generate_one=generate_one,
        scenes_dir=scenes,
        progress=progress,
        interval=interval,
        only=only,
        max_shots=max_shots,
    )


def _shots(ids: list[str], folder: str = "scenes") -> list[shot_runner.Shot]:
    return [
        shot_runner.Shot(
            id=sid, act="ACT", style="cinematic", folder=folder,
            prompt=f"p {sid}", duration=5,
        )
        for sid in ids
    ]


class TestProgressLog:
    def test_completed_ids_only_counts_ok(self, tmp_path: Path) -> None:
        log = shot_runner.ProgressLog(tmp_path / "progress.txt")
        log.path.write_text(
            "2026-09-21T00:00:00Z shot01 OK exit=0\n"
            "2026-09-21T00:05:00Z shot02 FAIL exit=1\n"
            "2026-09-21T00:09:00Z shot02 OK exit=1 (clip downloaded; post-gen step failed)\n"
        )
        assert log.completed_ids(["shot01", "shot02", "shot03"]) == {"shot01", "shot02"}

    def test_completed_ids_ignores_unknown_tokens(self, tmp_path: Path) -> None:
        log = shot_runner.ProgressLog(tmp_path / "progress.txt")
        log.path.write_text("2026-09-21T00:00:00Z shot01 OK exit=0\n")
        assert log.completed_ids(["shot01", "shot02"]) == {"shot01"}

    def test_missing_file_is_empty(self, tmp_path: Path) -> None:
        log = shot_runner.ProgressLog(tmp_path / "nope.txt")
        assert log.completed_ids(["shot01"]) == set()


class TestRunShots:
    def test_resume_skips_completed(self, tmp_path: Path) -> None:
        calls: list[str] = []

        def generate_one(shot):
            calls.append(shot.id)
            return True, 0, ""

        config = _make_config(tmp_path, _shots(["shot01", "shot02", "shot03"]), generate_one)
        config.progress.record("shot01", "OK", 0)
        assert shot_runner.run_shots(config) == 0
        assert calls == ["shot02", "shot03"]

    def test_stop_on_first_failure(self, tmp_path: Path) -> None:
        calls: list[str] = []

        def generate_one(shot):
            calls.append(shot.id)
            return shot.id != "shot02", 0 if shot.id != "shot02" else 1, ""

        config = _make_config(tmp_path, _shots(["shot01", "shot02", "shot03"]), generate_one)
        assert shot_runner.run_shots(config) == 1
        assert calls == ["shot01", "shot02"]  # shot03 never attempted
        text = config.progress.path.read_text()
        assert "shot02 FAIL" in text
        assert "shot01 OK" in text

    def test_postgen_failure_tolerated_when_clip_downloaded(self, tmp_path: Path) -> None:
        scenes = tmp_path / "videos" / "scenes"

        def generate_one(shot):
            (scenes / f"clip_{shot.id}.mp4").write_bytes(b"x")  # clip DID download
            return False, 1, ""  # ...but a post-gen step (gate) crashed

        config = _make_config(tmp_path, _shots(["shot01", "shot02"]), generate_one)
        assert shot_runner.run_shots(config) == 0
        text = config.progress.path.read_text()
        assert "shot01 OK" in text
        assert "post-gen step failed" in text
        assert "shot02 OK" in text

    def test_transition_clips_moved(self, tmp_path: Path) -> None:
        scenes = tmp_path / "videos" / "scenes"

        def generate_one(shot):
            (scenes / "clip_trans.mp4").write_bytes(b"x")
            return True, 0, ""

        config = _make_config(
            tmp_path, _shots(["trans12"], folder="transition"), generate_one
        )
        assert shot_runner.run_shots(config) == 0
        assert not (scenes / "clip_trans.mp4").exists()
        # Renamed to the Scene-XX-Shot-X-Y convention, then moved.
        assert (tmp_path / "videos" / "transition" / "Scene-01-Shot-1-1.mp4").is_file()

    def test_generated_clip_is_renamed_to_canonical_name(self, tmp_path: Path) -> None:
        scenes = tmp_path / "videos" / "scenes"
        scenes.mkdir(parents=True, exist_ok=True)
        existing_take = scenes / "Scene-01-Shot-1-2.mp4"
        existing_take.write_bytes(b"old")  # a previous take

        def generate_one(shot):
            (scenes / "videos_2026-09-21T00-00-00_establishing.mp4").write_bytes(b"new")
            return True, 0, ""

        shots = [
            shot_runner.Shot(
                id="shot02", act="ACT I", style="cinematic", folder="scenes",
                prompt="p", duration=5, scene=1, index_in_scene=2,
            ),
        ]
        config = _make_config(tmp_path, shots, generate_one)
        assert shot_runner.run_shots(config) == 0
        canonical = scenes / "Scene-01-Shot-1-2.mp4"
        assert canonical.read_bytes() == b"new"  # the redo replaces the old take
        assert not (scenes / "videos_2026-09-21T00-00-00_establishing.mp4").exists()

    def test_extra_clips_from_one_shot_get_a_numeric_suffix(
        self, tmp_path: Path
    ) -> None:
        scenes = tmp_path / "videos" / "scenes"

        def generate_one(shot):
            (scenes / "videos_a.mp4").write_bytes(b"a")
            (scenes / "videos_b.mp4").write_bytes(b"b")
            return True, 0, ""

        config = _make_config(tmp_path, _shots(["shot01"]), generate_one)
        assert shot_runner.run_shots(config) == 0
        assert (scenes / "Scene-01-Shot-1-1.mp4").is_file()
        assert (scenes / "Scene-01-Shot-1-1-2.mp4").is_file()

    def test_only_and_max_filters(self, tmp_path: Path) -> None:
        calls: list[str] = []

        def generate_one(shot):
            calls.append(shot.id)
            return True, 0, ""

        base = _shots(["shot01", "shot02", "shot03"])
        config = _make_config(tmp_path, base, generate_one, only={"shot03"})
        assert shot_runner.run_shots(config) == 0
        assert calls == ["shot03"]

        calls.clear()
        config = _make_config(tmp_path, base, generate_one, max_shots=2)
        assert shot_runner.run_shots(config) == 0
        assert calls == ["shot01", "shot02"]


# ---------------------------------------------------------------------------
# load_shots_file validation
# ---------------------------------------------------------------------------


class TestLoadShotsFile:
    def test_flat_and_structured_accepted(self, tmp_path: Path) -> None:
        assert shot_runner.load_shots_file(_write_shots_file(tmp_path, [{"name": "s"}]))
        assert shot_runner.load_shots_file(
            _write_shots_file(tmp_path, {"acts": {"a": {"shots": []}}})
        )

    def test_empty_flat_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            shot_runner.load_shots_file(_write_shots_file(tmp_path, []))

    def test_structured_without_acts_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            shot_runner.load_shots_file(_write_shots_file(tmp_path, {"foo": 1}))

    def test_scalar_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            shot_runner.load_shots_file(_write_shots_file(tmp_path, 42))


# ---------------------------------------------------------------------------
# CLI routing: produce --no-auto-refs / structured schema -> runner path
# ---------------------------------------------------------------------------


class TestProduceRunnerRouting:
    def _capture_generate(self, captured: dict[str, Any]):
        def fake_generate(project_id: str, shot: dict[str, Any], **kw: Any) -> bool:
            captured["shot"] = shot
            captured.update(kw)
            return True

        return fake_generate

    def test_no_auto_refs_routes_through_runner_with_progress_file(
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
            [
                {"name": "shot-1", "prompt": "establishing", "duration": 5,
                 "refs": ["char_a"]},
            ],
        )
        captured: dict[str, Any] = {}
        with (
            patch("brandly_cli.cli._generate_shot",
                  side_effect=self._capture_generate(captured)),
        ):
            result = runner.invoke(
                cli,
                ["produce", pid, "--shots", str(shots),
                 "--no-auto-refs", "--interval", "0"],
            )
        assert result.exit_code == 0, result.output
        assert captured["auto_refs_enabled"] is False
        # Runner path: progress file created (not the production-plan loop).
        progress = project_dir / pid / "docs" / "tmp" / "produce_progress.txt"
        assert progress.is_file()
        assert "shot-1 OK" in progress.read_text()
        # Reference payload = resolved .opt.jpg twin only.
        assert any(Path(r).name == "char_a.opt.jpg" for r in captured["shot"]["references"])

    def test_structured_schema_routes_through_runner(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _add_plate(project_dir, pid, "character", "char_a.opt.jpg")
        shots = _write_shots_file(
            tmp_path,
            {
                "character": "anchor",
                "acts": {
                    "act1": {
                        "prefix": "P ",
                        "style": "documentary",
                        "folder": "transition",
                        "shots": [{"id": "trans01", "prompt": "x", "duration": 4,
                                   "refs": ["char_a"]}],
                    },
                },
            },
        )
        captured: dict[str, Any] = {}
        with (
            patch("brandly_cli.cli._generate_shot",
                  side_effect=self._capture_generate(captured)),
            patch("brandly_cli.shot_runner.time.sleep"),
        ):
            result = runner.invoke(
                cli, ["produce", pid, "--shots", str(shots), "--interval", "0"]
            )
        assert result.exit_code == 0, result.output
        assert captured["shot"]["prompt"] == "P x"
        assert captured["shot"]["style"] == "documentary"
        assert captured["shot"]["character"] == "anchor"

    def test_structured_run_names_clips_scene_shot(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        shots = _write_shots_file(
            tmp_path,
            {
                "acts": {
                    "act1": {
                        "shots": [
                            {"id": "shot01", "prompt": "a", "duration": 5},
                            {"id": "shot02", "prompt": "b", "duration": 5},
                        ],
                    },
                },
            },
        )
        clips = project_dir / pid / "videos" / "scenes"

        def fake_generate(project_id: str, shot: dict[str, Any], **kw: Any) -> bool:
            clips.mkdir(parents=True, exist_ok=True)
            (clips / f"videos_{shot['name']}.mp4").write_bytes(b"x")
            return True

        with patch("brandly_cli.cli._generate_shot", side_effect=fake_generate):
            result = runner.invoke(
                cli, ["produce", pid, "--shots", str(shots), "--interval", "0"]
            )
        assert result.exit_code == 0, result.output
        assert sorted(p.name for p in clips.glob("*.mp4")) == [
            "Scene-01-Shot-1-1.mp4",
            "Scene-01-Shot-1-2.mp4",
        ]

    def test_flat_without_new_flags_stays_on_legacy_plan_loop(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        shots = _write_shots_file(
            tmp_path,
            [{"name": "shot-1", "prompt": "establishing", "duration": 5}],
        )
        with patch("brandly_cli.cli._generate_shot", return_value=True):
            result = runner.invoke(
                cli,
                ["produce", pid, "--shots", str(shots),
                 "--interval", "0"],
            )
        assert result.exit_code == 0, result.output
        # Legacy path registers the shot on the production plan.
        rows = _read_production_plan_rows(production_plan_path(pid, root=tmp_path))
        assert any(v["asset"].startswith("video-shot") for v in rows.values())
        # ...and NOT through the runner progress file.
        progress = project_dir / pid / "docs" / "tmp" / "produce_progress.txt"
        assert not progress.exists()
