"""Contract tests — v0.15.5 scene direction files (closes P1).

Behaviour under test:

* ``.brandly/<id>/prompts/Scene N/Scene N.md`` is an optional, authored
  direction file — never written by pack tools.
* ``load_scene_direction`` reads it (None when absent).
* The pack scan exempts ``Scene N/Scene N.md`` — not invalid, never an orphan.
* ``flatten_shots`` prepends the scene direction to every take of that scene
  (``direction + "\\n\\n" + take_prompt``); scenes without a file are unchanged.

RED-first per the repo convention; GREEN once the code is wired.
"""

from __future__ import annotations

from pathlib import Path

from brandly_cli import take_prompts
from brandly_cli.shot_runner import flatten_shots


def _shots() -> list[dict]:
    return [
        {"id": "s1-1", "scene": 1, "shot": 1, "prompt": "take 1.1", "duration": 5},
        {"id": "s1-2", "scene": 1, "shot": 2, "prompt": "take 1.2", "duration": 5},
        {"id": "s2-1", "scene": 2, "shot": 1, "prompt": "take 2.1", "duration": 5},
        {"id": "s3-1", "scene": 3, "shot": 1, "prompt": "take 3.1", "duration": 5},
    ]


# ---------------------------------------------------------------------------
# load_scene_direction
# ---------------------------------------------------------------------------


class TestLoadSceneDirection:
    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        pack = take_prompts.pack_dir(tmp_path, "p1")
        assert take_prompts.load_scene_direction(pack, 1) is None
        assert take_prompts.load_scene_direction(pack, 9) is None

    def test_present_file_returns_text(self, tmp_path: Path) -> None:
        pack = take_prompts.pack_dir(tmp_path, "p1")
        (pack / "Scene 1").mkdir(parents=True)
        (pack / "Scene 1" / "Scene 1.md").write_text(
            "Cinematic lighting, wide lens.\n", encoding="utf-8"
        )
        assert (
            take_prompts.load_scene_direction(pack, 1)
            == "Cinematic lighting, wide lens."
        )
        assert take_prompts.load_scene_direction(pack, 2) is None


# ---------------------------------------------------------------------------
# Pack scan exempts scene direction files
# ---------------------------------------------------------------------------


class TestScanFilesExemptsDirectionFiles:
    def _write(self, tmp_path: Path, project_id: str, rel: str, text: str) -> None:
        p = take_prompts.pack_dir(tmp_path, project_id) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def test_direction_file_not_invalid(self, tmp_path: Path) -> None:
        pack = take_prompts.pack_dir(tmp_path, "p1")
        self._write(tmp_path, "p1", "Scene 1/Scene 1.1.md", "prompt 1.1")
        self._write(tmp_path, "p1", "Scene 1/Scene 1.md", "scene direction\n")
        files, invalid = take_prompts._scan_files(pack)
        assert (1, 1) in files
        assert all(e["file"] != "Scene 1/Scene 1.md" for e in invalid)

    def test_direction_file_not_orphan(self, tmp_path: Path) -> None:
        pack = take_prompts.pack_dir(tmp_path, "p1")
        # Direction file for a scene with NO take — must not be an orphan.
        self._write(tmp_path, "p1", "Scene 9/Scene 9.md", "direction")
        _, invalid = take_prompts._scan_files(pack)
        assert all(e["file"] != "Scene 9/Scene 9.md" for e in invalid)


# ---------------------------------------------------------------------------
# status matrix unaffected by direction files
# ---------------------------------------------------------------------------


class TestStatusUnaffected:
    def test_direction_file_does_not_enter_matrix(self, tmp_path: Path) -> None:
        data = _shots()
        pack = take_prompts.pack_dir(tmp_path, "p1")
        (pack / "Scene 1").mkdir(parents=True)
        (pack / "Scene 1" / "Scene 1.md").write_text(
            "MOODY\n", encoding="utf-8"
        )
        # Valid manifest so the matrix reflects takes, not a manifest error.
        take_prompts._write_manifest(
            pack, "p1", {f"{s}.{t}": {} for s, t in ((1, 1), (1, 2), (2, 1), (3, 1))}
        )
        report = take_prompts.status("p1", data, root=tmp_path)
        # Direction file is metadata: not a take, not invalid, not an orphan.
        keys = {e["key"] for e in report["takes"]}
        assert keys == {"1.1", "1.2", "2.1", "3.1"}
        assert report["orphans"] == []
        # Direction file never appears as invalid (manifest missing is
        # orthogonal to the direction-file exemption).
        assert all(e["file"] != "Scene 1/Scene 1.md" for e in report["invalid"])
        assert all(e["state"] == "missing" for e in report["takes"])
        assert report["verdict"] == "warn"  # takes have prompts but no files yet


# ---------------------------------------------------------------------------
# flatten_shots prepends scene direction
# ---------------------------------------------------------------------------


class TestFlattenShotsDirection:
    def test_prepends_direction_for_scenes_with_file(self, tmp_path: Path) -> None:
        (take_prompts.pack_dir(tmp_path, "p1") / "Scene 1").mkdir(parents=True)
        (take_prompts.pack_dir(tmp_path, "p1") / "Scene 1" / "Scene 1.md").write_text(
            "SCENE ONE DIRECTION\n", encoding="utf-8"
        )
        shots = flatten_shots(
            _shots(),
            tmp_path / "images",
            character=None,
            scene_direction={1: "SCENE ONE DIRECTION"},
        )
        by_id = {s.id: s for s in shots}
        assert by_id["s1-1"].prompt == "SCENE ONE DIRECTION\n\ntake 1.1"
        assert by_id["s1-2"].prompt == "SCENE ONE DIRECTION\n\ntake 1.2"
        # Scenes without direction are unchanged.
        assert by_id["s2-1"].prompt == "take 2.1"
        assert by_id["s3-1"].prompt == "take 3.1"

    def test_no_direction_leaves_prompts_untouched(self) -> None:
        shots = flatten_shots(_shots(), Path("/tmp/images"), character=None)
        assert shots[0].prompt == "take 1.1"
        assert shots[1].prompt == "take 1.2"
        assert shots[2].prompt == "take 2.1"

    def test_empty_direction_is_noop(self) -> None:
        shots = flatten_shots(
            _shots(), Path("/tmp/images"), character=None, scene_direction={1: ""}
        )
        assert shots[0].prompt == "take 1.1"
