"""CLI contract tests — ``brandly takes`` (v0.15.4 §8.2).

RED-first for the per-take prompt pack command group.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli import layout, scenes
from brandly_cli.cli import cli


def _flat_20() -> list[dict]:
    return [
        {
            "id": f"s{scene}-{take}",
            "scene": scene,
            "shot": take,
            "prompt": f"prompt {scene}.{take}",
            "duration": 5,
        }
        for scene in range(1, 6)
        for take in range(1, 5)
    ]


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    project_id = "prompt-pack"
    data = _flat_20()
    proj = layout.resolve_project_dir(tmp_path, project_id)
    proj.mkdir(parents=True)
    (proj / "shots.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    scenes.write_scenes(project_id, data, root=tmp_path)
    return tmp_path


def _invoke(root: Path, *args: str):
    return CliRunner().invoke(cli, ["--root", str(root), "takes", *args])


class TestRegistration:
    def test_takes_is_listed(self) -> None:
        result = CliRunner().invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "takes" in result.output

    def test_takes_help_lists_commands(self) -> None:
        result = CliRunner().invoke(cli, ["takes", "--help"])
        assert result.exit_code == 0
        for command in ("list", "export", "apply", "status"):
            assert command in result.output


class TestExportCommand:
    def test_export_creates_tree(self, project: Path) -> None:
        result = _invoke(project, "export", "prompt-pack")
        assert result.exit_code == 0, result.output

        pack = layout.prompts_dir(project, "prompt-pack")
        assert (pack / "Scene 1" / "Scene 1.1.md").is_file()
        assert (pack / "Scene 5" / "Scene 5.4.md").is_file()
        assert (pack / "prompt-manifest.json").is_file()
        assert "20" in result.output

    def test_export_idempotent(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        pack = layout.prompts_dir(project, "prompt-pack")
        before = {p: p.stat().st_mtime_ns for p in pack.rglob("*") if p.is_file()}

        result = _invoke(project, "export", "prompt-pack")
        after = {p: p.stat().st_mtime_ns for p in pack.rglob("*") if p.is_file()}
        assert result.exit_code == 0
        assert before == after
        assert "in-sync" in result.output

    def test_export_keeps_edited_file(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        target = layout.prompts_dir(project, "prompt-pack") / "Scene 1" / "Scene 1.1.md"
        target.write_text("hand written\n", encoding="utf-8")

        result = _invoke(project, "export", "prompt-pack")
        assert result.exit_code == 0
        assert target.read_text(encoding="utf-8") == "hand written\n"

    def test_export_force_overwrites(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        target = layout.prompts_dir(project, "prompt-pack") / "Scene 1" / "Scene 1.1.md"
        target.write_text("hand written\n", encoding="utf-8")

        result = _invoke(project, "export", "prompt-pack", "--force")
        assert result.exit_code == 0
        assert target.read_text(encoding="utf-8") == "prompt 1.1\n"

    def test_prune_without_force_is_refused(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        pack = layout.prompts_dir(project, "prompt-pack")
        orphan = pack / "Scene 5" / "Scene 5.9.md"
        orphan.write_text("orphan\n", encoding="utf-8")

        result = _invoke(project, "export", "prompt-pack", "--prune")
        assert result.exit_code == 2
        assert orphan.exists()

    def test_export_dry_run_writes_nothing(self, project: Path) -> None:
        result = _invoke(project, "export", "prompt-pack", "--dry-run")
        assert result.exit_code == 0
        assert "Scene 1.1.md" in result.output
        assert not layout.prompts_dir(project, "prompt-pack").exists()


class TestApplyCommand:
    def test_apply_updates_shots_json(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        pack = layout.prompts_dir(project, "prompt-pack")
        (pack / "Scene 2" / "Scene 2.3.md").write_text("edited\n", encoding="utf-8")

        result = _invoke(project, "apply", "prompt-pack")
        assert result.exit_code == 0, result.output

        on_disk = json.loads(
            (layout.resolve_project_dir(project, "prompt-pack") / "shots.json").read_text(
                encoding="utf-8"
            )
        )
        assert on_disk[6]["prompt"] == "edited"
        assert on_disk[0]["prompt"] == "prompt 1.1"

    def test_apply_conflict_exit_2(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        pack = layout.prompts_dir(project, "prompt-pack")
        (pack / "Scene 1" / "Scene 1.1.md").write_text("file\n", encoding="utf-8")
        shots = layout.resolve_project_dir(project, "prompt-pack") / "shots.json"
        data = json.loads(shots.read_text(encoding="utf-8"))
        data[0]["prompt"] = "json"
        shots.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = _invoke(project, "apply", "prompt-pack")
        assert result.exit_code == 2

    def test_apply_clear(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        result = _invoke(project, "apply", "prompt-pack", "--clear", "1.2")
        assert result.exit_code == 0, result.output
        assert not (
            layout.prompts_dir(project, "prompt-pack") / "Scene 1" / "Scene 1.2.md"
        ).exists()

        data = json.loads(
            (layout.resolve_project_dir(project, "prompt-pack") / "shots.json").read_text(
                encoding="utf-8"
            )
        )
        assert data[1]["prompt"] == ""

    def test_apply_dry_run_writes_nothing(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        pack = layout.prompts_dir(project, "prompt-pack")
        (pack / "Scene 1" / "Scene 1.2.md").write_text("edited\n", encoding="utf-8")
        shots = layout.resolve_project_dir(project, "prompt-pack") / "shots.json"
        before = shots.read_bytes()

        result = _invoke(project, "apply", "prompt-pack", "--dry-run")
        assert result.exit_code == 0
        assert shots.read_bytes() == before

    def test_apply_scene_scope(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        pack = layout.prompts_dir(project, "prompt-pack")
        (pack / "Scene 1" / "Scene 1.1.md").write_text("scene one\n", encoding="utf-8")
        (pack / "Scene 2" / "Scene 2.1.md").write_text("scene two\n", encoding="utf-8")

        result = _invoke(project, "apply", "prompt-pack", "--scene", "1")
        assert result.exit_code == 0, result.output

        data = json.loads(
            (layout.resolve_project_dir(project, "prompt-pack") / "shots.json").read_text(
                encoding="utf-8"
            )
        )
        assert data[0]["prompt"] == "scene one"
        assert data[4]["prompt"] == "prompt 2.1"

    def test_apply_take_scope(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        pack = layout.prompts_dir(project, "prompt-pack")
        (pack / "Scene 3" / "Scene 3.2.md").write_text("take two\n", encoding="utf-8")
        (pack / "Scene 3" / "Scene 3.3.md").write_text("take three\n", encoding="utf-8")

        result = _invoke(project, "apply", "prompt-pack", "--scene", "3", "--take", "2")
        assert result.exit_code == 0, result.output

        data = json.loads(
            (layout.resolve_project_dir(project, "prompt-pack") / "shots.json").read_text(
                encoding="utf-8"
            )
        )
        assert data[9]["prompt"] == "take two"
        assert data[8]["prompt"] == "prompt 3.1"
        assert data[10]["prompt"] == "prompt 3.3"

    def test_clear_rejects_scene_combination(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        result = _invoke(project, "apply", "prompt-pack", "--clear", "1.2", "--scene", "1")
        assert result.exit_code == 1


class TestStatusCommand:
    def test_status_pass_exit_0(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        result = _invoke(project, "status", "prompt-pack")
        assert result.exit_code == 0
        assert "pass" in result.output.lower()

    def test_status_edited_exit_1(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        pack = layout.prompts_dir(project, "prompt-pack")
        (pack / "Scene 1" / "Scene 1.1.md").write_text("edited\n", encoding="utf-8")
        result = _invoke(project, "status", "prompt-pack")
        assert result.exit_code == 1
        assert "1.1" in result.output

    def test_status_conflict_exit_2(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        pack = layout.prompts_dir(project, "prompt-pack")
        (pack / "Scene 1" / "Scene 1.1.md").write_text("file\n", encoding="utf-8")
        shots = layout.resolve_project_dir(project, "prompt-pack") / "shots.json"
        data = json.loads(shots.read_text(encoding="utf-8"))
        data[0]["prompt"] = "json"
        shots.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = _invoke(project, "status", "prompt-pack")
        assert result.exit_code == 2

    def test_status_json(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        result = _invoke(project, "status", "prompt-pack", "--json")
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["verdict"] == "pass"
        assert len(payload["takes"]) == 20

    def test_list_shows_takes(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        result = _invoke(project, "list", "prompt-pack")
        assert result.exit_code == 0
        assert "Scene 1.1" in result.output
        assert "Scene 5.4" in result.output

    def test_list_scene_filter(self, project: Path) -> None:
        _invoke(project, "export", "prompt-pack")
        result = _invoke(project, "list", "prompt-pack", "--scene", "3", "--json")
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert {entry["scene"] for entry in payload["takes"]} == {3}


class TestValidation:
    def test_invalid_project_id(self, tmp_path: Path) -> None:
        result = _invoke(tmp_path, "status", "bad id!")
        assert result.exit_code == 1

    def test_missing_shots_json(self, tmp_path: Path) -> None:
        (tmp_path / ".brandly" / "ghost").mkdir(parents=True)
        result = _invoke(tmp_path, "status", "ghost")
        assert result.exit_code == 1

    def test_scene_paths_with_spaces_are_not_shelled(self, project: Path) -> None:
        # The pack deliberately uses folders with spaces; every command must
        # address takes by number, never by interpolating a path into a shell.
        assert _invoke(project, "export", "prompt-pack").exit_code == 0
        result = _invoke(project, "list", "prompt-pack", "--json")
        assert result.exit_code == 0
        payload = json.loads(result.output)
        first = next(entry for entry in payload["takes"] if entry["key"] == "1.1")
        assert first["file"] == "Scene 1/Scene 1.1.md"
