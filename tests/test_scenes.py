"""Tests for the explicit scene model + scene completeness gate (Goal 3).

Audit F6 (scene identity was positional, two acts each owned their own
``scene 1..N``) and F7 (no gate ever checked that every shot of scene N exists,
is the current take, and passes QC).

Contract:
* ``scenes.json`` (``docs/plan/``) is written by ``brandly produce`` and is the
  source of truth for which shots make up each scene.
* Scene ids are project-unique (``S01``…) even when two acts both declare
  ``scene 1``; the manifest keeps the original ``act`` + ``scene`` number.
* ``brandly scenes status`` reports the matrix; ``brandly gate --scene/--all-scenes``
  FAILs naming the missing/stale/gate-failed shots.

Written test-first (RED) — see dev-notes/GOAL-AGENTIC-PIPELINE.md Goal 3.
"""

from __future__ import annotations

import json
from pathlib import Path

from brandly_cli import scenes


def _project(tmp: Path, pid: str = "film") -> Path:
    """Minimal project skeleton: .brandly/<pid>/ docs + v2 production/<pid>/videos/scenes."""
    root = tmp / ".brandly"
    (root / pid / "docs" / "plan").mkdir(parents=True, exist_ok=True)
    (tmp / "production" / pid / "videos" / "scenes").mkdir(parents=True, exist_ok=True)
    return root


FLAT = [
    {"id": "shot01", "prompt": "wide", "scene": 1, "shot": 1},
    {"id": "shot02", "prompt": "mid", "scene": 1, "shot": 2},
    {"id": "shot03", "prompt": "cu", "scene": 1, "shot": 3},
]


STRUCTURED_TWO_ACTS = {
    "character": "Mara",
    "acts": {
        "act1": {"name": "ACT I", "scene": 1, "shots": [{"id": "a1", "prompt": "p"}]},
        "act2": {"name": "ACT II", "scene": 1, "shots": [{"id": "b1", "prompt": "p"}]},
    },
}


# ---------------------------------------------------------------------------
# Manifest construction (F6)
# ---------------------------------------------------------------------------


class TestBuildManifest:
    def test_flat_list_becomes_one_scene_with_expected_clips(self, tmp_path: Path) -> None:
        _project(tmp_path)
        manifest = scenes.write_scenes("film", FLAT, root=tmp_path)

        assert manifest["version"] == 1
        assert manifest["project_id"] == "film"
        assert len(manifest["scenes"]) == 1
        scene = manifest["scenes"][0]
        assert scene["id"] == "S01"
        assert scene["scene"] == 1
        clips = [s["clip"] for s in scene["shots"]]
        # Flat produce names downloads Scene-XX-Shot-<scene>-<shot>.mp4 at save time.
        assert clips == [
            "Scene-01-Shot-1-1.mp4",
            "Scene-01-Shot-1-2.mp4",
            "Scene-01-Shot-1-3.mp4",
        ]

    def test_two_acts_with_scene_1_get_distinct_scene_ids(self, tmp_path: Path) -> None:
        _project(tmp_path)
        manifest = scenes.write_scenes("film", STRUCTURED_TWO_ACTS, root=tmp_path)

        ids = [s["id"] for s in manifest["scenes"]]
        assert len(ids) == len(set(ids)) == 2, "scene ids must be project-unique"
        # The original numbers are preserved so nothing is lost in translation.
        assert [s["scene"] for s in manifest["scenes"]] == [1, 1]
        assert [s["act"] for s in manifest["scenes"]] == ["ACT I", "ACT II"]

    def test_manifest_written_to_docs_plan_scenes_json(self, tmp_path: Path) -> None:
        _project(tmp_path)
        scenes.write_scenes("film", FLAT, root=tmp_path)
        path = scenes.scenes_path("film", root=tmp_path)
        expected = tmp_path / ".brandly" / "film" / "docs" / "plan" / "scenes.json"
        assert path == expected
        data = json.loads(expected.read_text(encoding="utf-8"))
        assert data["project_id"] == "film"
        assert data["scenes"][0]["shots"][0]["id"] == "shot01"

    def test_load_scenes_returns_none_when_absent(self, tmp_path: Path) -> None:
        _project(tmp_path)
        assert scenes.load_scenes("film", root=tmp_path) is None


# ---------------------------------------------------------------------------
# Status matrix (F7)
# ---------------------------------------------------------------------------


def _touch(root: Path, pid: str, *names: str) -> None:
    folder = root.parent / "production" / pid / "videos" / "scenes"
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        (folder / name).write_bytes(b"\x00fake-clip\x00")


class TestSceneStatus:
    def test_all_clips_present_passes(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        scenes.write_scenes("film", FLAT, root=tmp_path)
        _touch(
            root, "film", "Scene-01-Shot-1-1.mp4", "Scene-01-Shot-1-2.mp4", "Scene-01-Shot-1-3.mp4"
        )

        status = scenes.status("film", root=tmp_path)

        assert status["verdict"] == "pass"
        scene = status["scenes"][0]
        assert scene["expected"] == 3
        assert scene["present"] == 3
        assert scene["missing"] == []
        assert scene["stale"] == []

    def test_missing_shot_is_reported_by_id_and_clip(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        scenes.write_scenes("film", FLAT, root=tmp_path)
        _touch(root, "film", "Scene-01-Shot-1-1.mp4", "Scene-01-Shot-1-2.mp4")

        status = scenes.status("film", root=tmp_path)
        scene = status["scenes"][0]

        assert status["verdict"] == "fail"
        assert scene["present"] == 2
        assert [m["id"] for m in scene["missing"]] == ["shot03"]
        assert scene["missing"][0]["clip"] == "Scene-01-Shot-1-3.mp4"

    def test_superseded_take_is_reported_as_stale(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        scenes.write_scenes("film", FLAT, root=tmp_path)
        _touch(
            root,
            "film",
            "Scene-01-Shot-1-1.mp4",
            "Scene-01-Shot-1-1-act9.mp4",  # prior take from the old naming scheme
            "Scene-01-Shot-1-2.mp4",
            "Scene-01-Shot-1-3.mp4",
        )

        status = scenes.status("film", root=tmp_path)
        scene = status["scenes"][0]

        assert status["verdict"] == "fail"
        assert [s["id"] for s in scene["stale"]] == ["shot01"]
        assert "Scene-01-Shot-1-1-act9.mp4" in scene["stale"][0]["files"]

    def test_extra_take_with_numeric_suffix_is_not_stale(self, tmp_path: Path) -> None:
        """name_clips() writes stem-2.mp4 for extra takes of the same run."""
        root = _project(tmp_path)
        scenes.write_scenes("film", FLAT, root=tmp_path)
        _touch(
            root,
            "film",
            "Scene-01-Shot-1-1.mp4",
            "Scene-01-Shot-1-1-2.mp4",
            "Scene-01-Shot-1-2.mp4",
            "Scene-01-Shot-1-3.mp4",
        )

        status = scenes.status("film", root=tmp_path)
        assert status["verdict"] == "pass"

    def test_status_is_json_serializable(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        scenes.write_scenes("film", FLAT, root=tmp_path)
        _touch(root, "film", "Scene-01-Shot-1-1.mp4")
        json.dumps(scenes.status("film", root=tmp_path))  # must not raise


# ---------------------------------------------------------------------------
# CLI: brandly scenes status
# ---------------------------------------------------------------------------


class TestScenesStatusCommand:
    def test_json_mode_reports_the_matrix(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from brandly_cli.cli import cli

        root = _project(tmp_path)
        scenes.write_scenes("film", FLAT, root=tmp_path)
        _touch(root, "film", "Scene-01-Shot-1-1.mp4")

        result = CliRunner().invoke(
            cli, ["--root", str(tmp_path), "scenes", "status", "film", "--json"]
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["verdict"] == "fail"
        assert payload["scenes"][0]["missing"][0]["id"] == "shot02"

    def test_missing_manifest_exits_nonzero_with_guidance(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from brandly_cli.cli import cli

        _project(tmp_path)
        result = CliRunner().invoke(cli, ["--root", str(tmp_path), "scenes", "status", "film"])
        assert result.exit_code != 0
        assert "produce" in result.output  # tells the user how to create it


# ---------------------------------------------------------------------------
# CLI: brandly gate --scene / --all-scenes  (the missing gate from audit F7)
# ---------------------------------------------------------------------------


class TestGateScene:
    def _gate(self, tmp: Path, *args: str) -> object:
        from click.testing import CliRunner

        from brandly_cli.cli import cli

        return CliRunner().invoke(cli, ["--root", str(tmp), "gate", "film", *args])

    def test_scene_gate_passes_when_every_shot_is_present(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        scenes.write_scenes("film", FLAT, root=tmp_path)
        _touch(
            root, "film", "Scene-01-Shot-1-1.mp4", "Scene-01-Shot-1-2.mp4", "Scene-01-Shot-1-3.mp4"
        )

        result = self._gate(tmp_path, "--scene", "S01", "--no-quality")
        assert result.exit_code == 0, result.output

    def test_scene_gate_fails_and_names_the_missing_shot(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        scenes.write_scenes("film", FLAT, root=tmp_path)
        _touch(root, "film", "Scene-01-Shot-1-1.mp4", "Scene-01-Shot-1-2.mp4")

        result = self._gate(tmp_path, "--scene", "S01", "--no-quality")
        assert result.exit_code != 0, result.output
        assert "shot03" in result.output
        assert "Scene-01-Shot-1-3.mp4" in result.output

    def test_scene_gate_fails_on_stale_take(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        scenes.write_scenes("film", FLAT, root=tmp_path)
        _touch(
            root,
            "film",
            "Scene-01-Shot-1-1.mp4",
            "Scene-01-Shot-1-1-act9.mp4",
            "Scene-01-Shot-1-2.mp4",
            "Scene-01-Shot-1-3.mp4",
        )

        result = self._gate(tmp_path, "--scene", "S01", "--no-quality")
        assert result.exit_code != 0, result.output
        assert "Scene-01-Shot-1-1-act9.mp4" in result.output

    def test_all_scenes_checks_every_scene_and_names_the_laggard(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        two_scenes = [
            {"id": "a", "prompt": "p", "scene": 1, "shot": 1},
            {"id": "b", "prompt": "p", "scene": 2, "shot": 1},
        ]
        scenes.write_scenes("film", two_scenes, root=tmp_path)
        _touch(root, "film", "Scene-01-Shot-1-1.mp4")  # scene 2 never generated

        result = self._gate(tmp_path, "--all-scenes", "--no-quality")
        assert result.exit_code != 0, result.output
        assert "S01" in result.output and "S02" in result.output
        assert "b" in result.output  # names the missing shot id

    def test_unknown_scene_reference_errors(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        scenes.write_scenes("film", FLAT, root=tmp_path)
        _touch(root, "film", "Scene-01-Shot-1-1.mp4")

        result = self._gate(tmp_path, "--scene", "S99")
        assert result.exit_code != 0
        assert "S99" in result.output

    def test_quality_check_fails_on_undecodable_clip(self, tmp_path: Path) -> None:
        import shutil

        if not shutil.which("ffmpeg"):
            import pytest

            pytest.skip("ffmpeg not available")
        root = _project(tmp_path)
        scenes.write_scenes("film", FLAT, root=tmp_path)
        # present but not a decodable video -> deterministic QC pre-check must fail
        _touch(
            root, "film", "Scene-01-Shot-1-1.mp4", "Scene-01-Shot-1-2.mp4", "Scene-01-Shot-1-3.mp4"
        )

        result = self._gate(tmp_path, "--scene", "S01")
        assert result.exit_code != 0, result.output
        assert "quality" in result.output.lower() or "gate" in result.output.lower()

    def test_no_quality_flag_skips_qc(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        scenes.write_scenes("film", FLAT, root=tmp_path)
        _touch(
            root, "film", "Scene-01-Shot-1-1.mp4", "Scene-01-Shot-1-2.mp4", "Scene-01-Shot-1-3.mp4"
        )

        result = self._gate(tmp_path, "--scene", "S01", "--no-quality")
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Integration: brandly produce writes the manifest (single source of truth)
# ---------------------------------------------------------------------------


class TestProduceWritesScenesManifest:
    def test_produce_registers_all_scenes_before_generating(self, tmp_path: Path) -> None:
        import json as _json
        from unittest.mock import patch

        from click.testing import CliRunner

        from brandly_cli.cli import cli

        root = _project(tmp_path)
        (root / "film" / "project.json").write_text(
            _json.dumps(
                {
                    "id": "film",
                    "name": "Film",
                    "style": "cinematic",
                    "shot_count": 3,
                    "budget": 500,
                    "status": "running",
                }
            ),
            encoding="utf-8",
        )
        shots_file = tmp_path / "shots.json"
        shots_file.write_text(_json.dumps(FLAT), encoding="utf-8")

        # Generate nothing: this test proves the manifest wiring, not providers.
        with patch("brandly_cli.cmd.production._generate_shot", return_value=True):
            result = CliRunner().invoke(
                cli,
                [
                    "--root",
                    str(tmp_path),
                    "produce",
                    "film",
                    "--shots",
                    str(shots_file),
                    "--interval",
                    "0",
                ],
            )
        assert result.exit_code == 0, result.output

        manifest = scenes.load_scenes("film", root=tmp_path)
        assert manifest is not None, "produce must write scenes.json"
        clips = [s["clip"] for s in manifest["scenes"][0]["shots"]]
        assert len(clips) == 3

        # Nothing generated yet, so the completeness gate correctly FAILs:
        status = scenes.status("film", root=tmp_path)
        assert status["verdict"] == "fail"
        assert len(status["scenes"][0]["missing"]) == 3
