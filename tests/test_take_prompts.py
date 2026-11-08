"""Contract tests — v0.15.4 per-take prompt files.

RED-first for ``dev-notes/subgoals/v0-15-4-per-take-prompts.md`` §8.1.

The prompt pack is a file projection of the shot list:

    .brandly/<id>/prompts/
        Scene 1/Scene 1.1.md   ← Take 1 of Scene 1
        ...

This module tests the pure model only: layout, naming, ordering, status
matrix and manifest. CLI and produce integration live in
``test_take_prompts_cli.py`` / ``test_take_prompts_produce.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from brandly_cli import layout, scenes

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _flat_20() -> list[dict]:
    """5 scenes × 4 takes — the example from the subgoal."""
    shots: list[dict] = []
    for scene in range(1, 6):
        for take in range(1, 5):
            shots.append(
                {
                    "id": f"s{scene}-{take}",
                    "scene": scene,
                    "shot": take,
                    "prompt": f"prompt {scene}.{take}",
                    "duration": 5,
                }
            )
    return shots


def _structured_20() -> dict:
    """Same 5/20 shape expressed as a structured ``{"acts": …}`` plan."""
    return {
        "character": "ref hero",
        "acts": {
            f"act{scene}": {
                "name": f"ACT {scene}",
                "scene": scene,
                "shots": [
                    {"id": f"a{scene}s{take}", "prompt": f"prompt {scene}.{take}"}
                    for take in range(1, 5)
                ],
            }
            for scene in range(1, 6)
        },
    }


def _write_shots(root: Path, project_id: str, data) -> Path:
    path = layout.resolve_project_dir(root, project_id) / "shots.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _project(tmp_path: Path, project_id: str = "prompt-pack", data=None) -> Path:
    data = data if data is not None else _flat_20()
    _write_shots(tmp_path, project_id, data)
    scenes.write_scenes(project_id, data, root=tmp_path)
    return layout.prompts_dir(tmp_path, project_id)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 8.1 Layout
# ---------------------------------------------------------------------------


class TestLayout:
    def test_prompts_dirname_and_helper(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        assert layout.PROMPTS_DIRNAME == "prompts"
        assert take_prompts.pack_dir(tmp_path, "proj") == (
            tmp_path / ".brandly" / "proj" / "prompts"
        )
        assert layout.prompts_dir(tmp_path, "proj") == (
            tmp_path / ".brandly" / "proj" / "prompts"
        )

    def test_project_tree_never_creates_prompts(self, tmp_path: Path) -> None:
        layout.ensure_project_tree(tmp_path, "proj")
        assert not layout.prompts_dir(tmp_path, "proj").exists()


# ---------------------------------------------------------------------------
# 8.1 Naming
# ---------------------------------------------------------------------------


class TestNaming:
    def test_format_is_canonical(self) -> None:
        from brandly_cli import take_prompts

        assert take_prompts.format_take_relpath(1, 1) == "Scene 1/Scene 1.1.md"
        assert take_prompts.format_take_relpath(12, 10) == "Scene 12/Scene 12.10.md"
        # Spec names (§8.1) are the same contract.
        assert take_prompts.format_take_path(1, 1) == "Scene 1/Scene 1.1.md"
        assert take_prompts.parse_take_path("Scene 1/Scene 1.1.md") == (1, 1)
        assert take_prompts.parse_take_path("notes.txt") is None

    def test_parse_round_trips(self) -> None:
        from brandly_cli import take_prompts

        for scene in range(1, 100):
            for take in range(1, 100):
                rel = take_prompts.format_take_relpath(scene, take)
                assert take_prompts.parse_take_relpath(rel) == (scene, take)

    @pytest.mark.parametrize(
        "rel",
        [
            "Scene 01/Scene 01.1.md",
            "scene 1/Scene 1.1.md",
            "Scene-1/Scene-1.1.md",
            "Scene 1/Scene 01.1.md",
            "Scene 1/Scene 1.01.md",
            "Scene 1/Scene 1.1.txt",
            "Scene 1/Scene 2.1.md",
            "Scene 1/nested/Scene 1.1.md",
            "Scene 0/Scene 0.1.md",
            "Scene 1/Scene 1.0.md",
            "prompt-manifest.json",
        ],
    )
    def test_non_canonical_paths_are_rejected(self, rel: str) -> None:
        from brandly_cli import take_prompts

        assert take_prompts.parse_take_relpath(rel) is None

    def test_numeric_sort_key(self) -> None:
        from brandly_cli import take_prompts

        keys = [(10, 1), (9, 10), (9, 9), (1, 2)]
        assert sorted(keys, key=take_prompts.take_sort_key) == [
            (1, 2),
            (9, 9),
            (9, 10),
            (10, 1),
        ]


# ---------------------------------------------------------------------------
# 8.1 Take walk
# ---------------------------------------------------------------------------


class TestTakeWalk:
    def test_flat_5_scenes_20_takes(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        takes = take_prompts.iter_takes(_flat_20())
        assert len(takes) == 20
        assert sorted((t.scene, t.take) for t in takes) == [
            (scene, take) for scene in range(1, 6) for take in range(1, 5)
        ]
        assert len({(t.scene, t.take) for t in takes}) == 20

    def test_structured_5_scenes_20_takes(self) -> None:
        from brandly_cli import take_prompts

        takes = take_prompts.iter_takes(_structured_20())
        assert len(takes) == 20
        assert [(t.scene, t.take) for t in takes[:4]] == [
            (1, 1),
            (1, 2),
            (1, 3),
            (1, 4),
        ]

    def test_flat_scene_without_shot_key_uses_position(self) -> None:
        from brandly_cli import take_prompts

        takes = take_prompts.iter_takes(
            [{"scene": 1, "prompt": "a"}, {"scene": 1, "prompt": "b"}]
        )
        assert [(t.scene, t.take) for t in takes] == [(1, 1), (1, 2)]

    def test_duplicate_scene_take_rejected(self) -> None:
        from brandly_cli import take_prompts

        with pytest.raises(take_prompts.TakePromptError, match="duplicate"):
            take_prompts.iter_takes(
                [
                    {"scene": 1, "shot": 1, "prompt": "a"},
                    {"scene": 1, "shot": 1, "prompt": "b"},
                ]
            )

    def test_scene_ordinal_is_project_unique(self) -> None:
        from brandly_cli import take_prompts

        data = {
            "acts": {
                "a1": {"scene": 1, "shots": [{"prompt": "a"}]},
                "a2": {"scene": 1, "shots": [{"prompt": "b"}]},
            }
        }
        takes = take_prompts.iter_takes(data)
        assert [(t.scene, t.take) for t in takes] == [(1, 1), (2, 1)]

    def test_structured_prompt_dict_is_unsupported(self) -> None:
        from brandly_cli import take_prompts

        takes = take_prompts.iter_takes(
            [{"scene": 1, "shot": 1, "prompt": {"subject": "hero"}}]
        )
        assert takes[0].prompt is None

    def test_missing_prompt_is_unscripted(self) -> None:
        from brandly_cli import take_prompts

        takes = take_prompts.iter_takes([{"scene": 1, "shot": 1}])
        assert takes[0].prompt == ""


# ---------------------------------------------------------------------------
# 8.1 Export tree + status matrix
# ---------------------------------------------------------------------------


class TestExportAndStatus:
    def test_export_creates_exact_5_scene_tree(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        report = take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        assert report["verdict"] == "pass"

        expected = {
            pack / f"Scene {scene}" / f"Scene {scene}.{take}.md"
            for scene in range(1, 6)
            for take in range(1, 5)
        }
        assert set(pack.rglob("*.md")) == expected
        assert (pack / "prompt-manifest.json").is_file()
        assert _read(pack / "Scene 1" / "Scene 1.1.md") == "prompt 1.1\n"

    def test_export_is_idempotent(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        first = {p: p.stat().st_mtime_ns for p in pack.rglob("*") if p.is_file()}
        report = take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        second = {p: p.stat().st_mtime_ns for p in pack.rglob("*") if p.is_file()}

        assert report["verdict"] == "pass"
        assert report["actions"] == []
        assert first == second

    def test_status_in_sync(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        report = take_prompts.status("prompt-pack", _flat_20(), root=tmp_path)
        assert report["verdict"] == "pass"
        assert report["counts"]["in-sync"] == 20
        assert report["pack_exists"] is True

    def test_status_without_pack(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        _project(tmp_path)
        report = take_prompts.status("prompt-pack", _flat_20(), root=tmp_path)
        assert report["pack_exists"] is False
        assert report["verdict"] == "pass"

    def test_edited_file(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        (pack / "Scene 1" / "Scene 1.1.md").write_text("new direction\n", encoding="utf-8")

        report = take_prompts.status("prompt-pack", _flat_20(), root=tmp_path)
        assert report["verdict"] == "warn"
        states = {e["key"]: e["state"] for e in report["takes"]}
        assert states["1.1"] == "edited"

    def test_drifted_shot_list(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        changed = _flat_20()
        changed[0]["prompt"] = "changed in shots.json"

        report = take_prompts.status("prompt-pack", changed, root=tmp_path)
        states = {e["key"]: e["state"] for e in report["takes"]}
        assert states["1.1"] == "drifted"

    def test_conflict(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        (pack / "Scene 1" / "Scene 1.1.md").write_text("file side\n", encoding="utf-8")
        changed = _flat_20()
        changed[0]["prompt"] = "json side"

        report = take_prompts.status("prompt-pack", changed, root=tmp_path)
        states = {e["key"]: e["state"] for e in report["takes"]}
        assert states["1.1"] == "conflict"
        assert report["verdict"] == "fail"

    def test_missing_file(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        (pack / "Scene 2" / "Scene 2.3.md").unlink()

        report = take_prompts.status("prompt-pack", _flat_20(), root=tmp_path)
        states = {e["key"]: e["state"] for e in report["takes"]}
        assert states["2.3"] == "missing"
        assert report["verdict"] == "warn"

    def test_unscripted_does_not_block(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        data = _flat_20()
        data[0]["prompt"] = ""
        _project(tmp_path, data=data)
        take_prompts.export("prompt-pack", data, root=tmp_path)

        report = take_prompts.status("prompt-pack", data, root=tmp_path)
        states = {e["key"]: e["state"] for e in report["takes"]}
        assert states["1.1"] == "unscripted"
        assert report["verdict"] == "pass"
        assert not (tmp_path / ".brandly/prompt-pack/prompts/Scene 1/Scene 1.1.md").exists()

    def test_unsupported_structured_prompt_does_not_block(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        data = [{"scene": 1, "shot": 1, "prompt": {"subject": "hero"}}]
        _project(tmp_path, data=data)
        report = take_prompts.status("prompt-pack", data, root=tmp_path)
        assert report["verdict"] == "pass"
        assert report["takes"][0]["state"] == "unsupported"

    def test_empty_file_is_invalid(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        (pack / "Scene 1" / "Scene 1.2.md").write_text("   \n\n", encoding="utf-8")

        report = take_prompts.status("prompt-pack", _flat_20(), root=tmp_path)
        states = {e["key"]: e["state"] for e in report["takes"]}
        assert states["1.2"] == "invalid"
        assert report["verdict"] == "fail"

    def test_unknown_root_entry_is_invalid(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        (pack / "notes.txt").write_text("stray", encoding="utf-8")

        report = take_prompts.status("prompt-pack", _flat_20(), root=tmp_path)
        assert report["verdict"] == "fail"
        assert any("notes.txt" in entry["file"] for entry in report["invalid"])

    def test_case_variant_scene_dir_is_invalid(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        (pack / "scene 1" / "Scene 1.1.md").parent.mkdir()
        (pack / "scene 1" / "Scene 1.1.md").write_text("x\n", encoding="utf-8")

        report = take_prompts.status("prompt-pack", _flat_20(), root=tmp_path)
        assert report["verdict"] == "fail"
        assert any("scene 1" in entry["file"] for entry in report["invalid"])

    def test_take_in_wrong_scene_folder_is_invalid(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        src = pack / "Scene 1" / "Scene 1.1.md"
        dst = pack / "Scene 2" / "Scene 1.1.md"
        dst.write_text(_read(src), encoding="utf-8")
        src.unlink()

        report = take_prompts.status("prompt-pack", _flat_20(), root=tmp_path)
        assert report["verdict"] == "fail"
        assert any("Scene 2/Scene 1.1.md" in entry["file"] for entry in report["invalid"])

    def test_orphan_file(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        (pack / "Scene 5" / "Scene 5.9.md").write_text("orphan\n", encoding="utf-8")

        report = take_prompts.status("prompt-pack", _flat_20(), root=tmp_path)
        assert report["verdict"] == "fail"
        assert any("Scene 5.9.md" in entry["file"] for entry in report["orphans"])

    def test_missing_manifest_is_invalid(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        (pack / "prompt-manifest.json").unlink()

        report = take_prompts.status("prompt-pack", _flat_20(), root=tmp_path)
        assert report["verdict"] == "fail"
        assert any("manifest" in entry["error"] for entry in report["invalid"])

    def test_unknown_manifest_version_is_invalid(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        manifest_path = pack / "prompt-manifest.json"
        manifest = json.loads(_read(manifest_path))
        manifest["version"] = 99
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        report = take_prompts.status("prompt-pack", _flat_20(), root=tmp_path)
        assert report["verdict"] == "fail"
        assert any("version" in entry["error"] for entry in report["invalid"])


# ---------------------------------------------------------------------------
# 8.1 Export/apply safety
# ---------------------------------------------------------------------------


class TestExportSafety:
    def test_export_does_not_overwrite_edited_without_force(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        target = pack / "Scene 1" / "Scene 1.1.md"
        target.write_text("hand written\n", encoding="utf-8")

        report = take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        assert _read(target) == "hand written\n"
        assert report["verdict"] == "warn"

    def test_export_force_overwrites_and_reports(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        target = pack / "Scene 1" / "Scene 1.1.md"
        target.write_text("hand written\n", encoding="utf-8")

        report = take_prompts.export(
            "prompt-pack", _flat_20(), root=tmp_path, force=True
        )
        assert _read(target) == "prompt 1.1\n"
        assert any("Scene 1.1.md" in a["path"] for a in report["actions"])

    def test_export_prune_requires_force(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        orphan = pack / "Scene 5" / "Scene 5.9.md"
        orphan.write_text("orphan\n", encoding="utf-8")

        report = take_prompts.export("prompt-pack", _flat_20(), root=tmp_path, prune=True)
        assert orphan.exists()
        assert report["verdict"] == "fail"

        report = take_prompts.export(
            "prompt-pack", _flat_20(), root=tmp_path, prune=True, force=True
        )
        assert not orphan.exists()
        assert report["verdict"] == "pass"

    def test_export_refuses_on_invalid_entries(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        (pack / "Scene 1" / "Scene 1.99.md").write_text("wrong take\n", encoding="utf-8")

        report = take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        assert report["verdict"] == "fail"
        assert report["actions"] == []

    def test_export_duplicate_scene_take_writes_nothing(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        data = [
            {"scene": 1, "shot": 1, "prompt": "a"},
            {"scene": 1, "shot": 1, "prompt": "b"},
        ]
        _project(tmp_path, data=data)
        report = take_prompts.export("prompt-pack", data, root=tmp_path)
        assert report["verdict"] == "fail"
        assert not (tmp_path / ".brandly/prompt-pack/prompts").exists()

    def test_dry_run_writes_nothing(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        _project(tmp_path)
        report = take_prompts.export(
            "prompt-pack", _flat_20(), root=tmp_path, dry_run=True
        )
        assert report["actions"]
        assert not (tmp_path / ".brandly/prompt-pack/prompts").exists()


class TestApply:
    def test_apply_updates_only_the_edited_shot(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        (pack / "Scene 1" / "Scene 1.2.md").write_text("edited take\n", encoding="utf-8")

        data = _flat_20()
        report = take_prompts.apply("prompt-pack", data, root=tmp_path)
        assert report["verdict"] == "pass"
        assert data[1]["prompt"] == "edited take"
        assert data[0]["prompt"] == "prompt 1.1"

        on_disk = json.loads(
            _read(tmp_path / ".brandly/prompt-pack/shots.json")
        )
        assert on_disk[1]["prompt"] == "edited take"

    def test_apply_refuses_conflict_without_force(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        (pack / "Scene 1" / "Scene 1.1.md").write_text("file side\n", encoding="utf-8")
        data = _flat_20()
        data[0]["prompt"] = "json side"

        report = take_prompts.apply("prompt-pack", data, root=tmp_path)
        assert report["verdict"] == "fail"
        assert data[0]["prompt"] == "json side"

    def test_apply_force_resolves_conflict(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        (pack / "Scene 1" / "Scene 1.1.md").write_text("file side\n", encoding="utf-8")
        data = _flat_20()
        data[0]["prompt"] = "json side"

        report = take_prompts.apply("prompt-pack", data, root=tmp_path, force=True)
        assert report["verdict"] == "pass"
        assert data[0]["prompt"] == "file side"

    def test_apply_clear_removes_file_and_prompt(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        data = _flat_20()

        report = take_prompts.apply("prompt-pack", data, root=tmp_path, clear="1.2")
        assert report["verdict"] == "pass"
        assert data[1]["prompt"] == ""
        assert not (pack / "Scene 1" / "Scene 1.2.md").exists()

    def test_apply_dry_run_writes_nothing(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        take_prompts.export("prompt-pack", _flat_20(), root=tmp_path)
        (pack / "Scene 1" / "Scene 1.2.md").write_text("edited\n", encoding="utf-8")
        shots_path = tmp_path / ".brandly/prompt-pack/shots.json"
        before = shots_path.read_bytes()

        report = take_prompts.apply(
            "prompt-pack", _flat_20(), root=tmp_path, dry_run=True
        )
        assert report["actions"]
        assert shots_path.read_bytes() == before

    def test_apply_is_idempotent(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        _project(tmp_path)
        data = _flat_20()
        take_prompts.export("prompt-pack", data, root=tmp_path)
        take_prompts.apply("prompt-pack", data, root=tmp_path)

        report = take_prompts.apply("prompt-pack", data, root=tmp_path)
        assert report["verdict"] == "pass"
        assert report["actions"] == []


class TestApplyScope:
    """``--scene``/``--take`` narrow apply to one folder / one take index."""

    def test_scene_filter_touches_only_that_scene(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        data = _flat_20()
        take_prompts.export("prompt-pack", data, root=tmp_path)
        (pack / "Scene 1" / "Scene 1.1.md").write_text("scene one\n", encoding="utf-8")
        (pack / "Scene 2" / "Scene 2.1.md").write_text("scene two\n", encoding="utf-8")

        take_prompts.apply("prompt-pack", data, root=tmp_path, scene=1)

        assert data[0]["prompt"] == "scene one"   # 1.1 applied
        assert data[4]["prompt"] == "prompt 2.1"  # 2.1 untouched
        assert (pack / "Scene 2" / "Scene 2.1.md").read_text(encoding="utf-8") == "scene two\n"

    def test_take_filter_touches_only_that_take(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        data = _flat_20()
        take_prompts.export("prompt-pack", data, root=tmp_path)
        (pack / "Scene 1" / "Scene 1.2.md").write_text("take two\n", encoding="utf-8")
        (pack / "Scene 1" / "Scene 1.3.md").write_text("take three\n", encoding="utf-8")

        take_prompts.apply("prompt-pack", data, root=tmp_path, scene=1, take=2)

        assert data[1]["prompt"] == "take two"
        assert data[2]["prompt"] == "prompt 1.3"

    def test_scoped_apply_ignores_conflict_outside_scope(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        pack = _project(tmp_path)
        data = _flat_20()
        take_prompts.export("prompt-pack", data, root=tmp_path)
        # Conflict in 2.1 (both sides changed) but we only apply scene 1.
        (pack / "Scene 2" / "Scene 2.1.md").write_text("file side\n", encoding="utf-8")
        data[4]["prompt"] = "json side"
        (pack / "Scene 1" / "Scene 1.1.md").write_text("scene one\n", encoding="utf-8")

        report = take_prompts.apply("prompt-pack", data, root=tmp_path, scene=1)

        assert report.get("error") is None
        assert data[0]["prompt"] == "scene one"
        assert data[4]["prompt"] == "json side"

    def test_scope_with_no_match_is_a_warning_and_writes_nothing(self, tmp_path: Path) -> None:
        from brandly_cli import take_prompts

        _project(tmp_path)
        data = _flat_20()
        take_prompts.export("prompt-pack", data, root=tmp_path)
        before = (tmp_path / ".brandly/prompt-pack/shots.json").read_bytes()

        report = take_prompts.apply("prompt-pack", data, root=tmp_path, scene=99)

        assert report["verdict"] == "warn"
        assert report["actions"] == []
        assert (tmp_path / ".brandly/prompt-pack/shots.json").read_bytes() == before


# ---------------------------------------------------------------------------
# 8.4 Docs contract
# ---------------------------------------------------------------------------

_REPO = Path(__file__).resolve().parents[1]


class TestDocsContract:
    """The shipped docs must describe the feature they ship."""

    def test_layout_docstring_documents_prompts(self) -> None:
        text = (_REPO / "src/brandly_cli/layout.py").read_text(encoding="utf-8")
        assert "prompts/" in text
        assert "brandly takes export" in text

    def test_agent_surface_documents_prompts(self) -> None:
        text = (_REPO / "src/brandly_cli/agent_surface.py").read_text(encoding="utf-8")
        assert ".brandly/<id>/prompts/" in text

    def test_video_generation_skill_has_the_section(self) -> None:
        text = (_REPO / "skills/brandly-video-generation/SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "Per-take prompt pack" in text
        for needle in (
            "Scene 1/Scene 1.1.md",
            "brandly takes export",
            "brandly takes apply",
            "brandly takes status",
            "--ignore-prompt-pack",
            "prompt pack ignored",
        ):
            assert needle in text, f"missing {needle!r} in the skill doc"

    def test_init_skill_does_not_claim_auto_creation(self) -> None:
        text = (_REPO / "skills/brandly-init/SKILL.md").read_text(encoding="utf-8")
        assert "prompts/Scene N/Scene N.T.md" in text
        assert "never auto-created" in text


