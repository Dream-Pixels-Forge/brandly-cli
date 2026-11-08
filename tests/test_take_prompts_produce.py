r"""Contract tests — ``brandly produce`` fail-closed on prompt-pack drift.

RED-first for ``dev-notes/subgoals/v0-15-4-per-take-prompts.md`` §8.3.

The prompt pack is opt-in. When ``.brandly/<id>/prompts/`` is absent,
``produce`` behaves exactly as before. When it exists it is the prompt source
of truth: any drift refuses the run (exit 2) **before** a provider call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from click.testing import CliRunner

from brandly_cli import layout, take_prompts
from brandly_cli.cli import cli
from brandly_cli.utils import generate_project_id


def _shots() -> list[dict[str, Any]]:
    return [
        {"id": "s1-1", "scene": 1, "shot": 1, "prompt": "opening shot", "duration": 4},
        {"id": "s1-2", "scene": 1, "shot": 2, "prompt": "second beat", "duration": 4},
    ]


class _Harness:
    """A project with a shots file and a patched video backend."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path
        self.pid = generate_project_id()
        proj = layout.resolve_project_dir(tmp_path, self.pid)
        proj.mkdir(parents=True)
        (proj / "project.json").write_text(
            json.dumps({"id": self.pid, "name": "Test"}), encoding="utf-8"
        )
        self.shots_file = proj / "shots.json"
        self.shots_file.write_text(json.dumps(_shots()), encoding="utf-8")
        self.proj = proj
        self.calls: list[dict[str, Any]] = []

    def export_pack(self) -> Path:
        report = take_prompts.export(self.pid, _shots(), root=self.root)
        assert report["verdict"] == "pass"
        return layout.prompts_dir(self.root, self.pid)

    def run(self, *extra: str):
        def fake_generate(project_id: str, shot: dict[str, Any], **kw: Any) -> bool:
            self.calls.append({"shot": shot, **kw})
            return True

        with (
            patch("brandly_cli.cmd.generation._generate_shot", side_effect=fake_generate),
            patch("brandly_cli.shot_runner.time.sleep"),
        ):
            result = CliRunner().invoke(
                cli,
                [
                    "--root",
                    str(self.root),
                    "produce",
                    self.pid,
                    "--shots",
                    str(self.shots_file),
                    "--no-auto-refs",
                    "--allow-referenceless",
                    "--interval",
                    "0",
                    *extra,
                ],
            )
        return result


class TestNoPack:
    def test_without_pack_produce_runs_unchanged(self, tmp_path: Path) -> None:
        h = _Harness(tmp_path)
        result = h.run()
        assert result.exit_code == 0, result.output
        assert len(h.calls) == 2
        assert "prompt pack" not in result.output.lower()


class TestDriftRefuses:
    def _assert_refused(self, result, h: _Harness) -> None:
        assert result.exit_code == 2, result.output
        assert h.calls == [], "no provider call may be made on drift"
        assert any(key in result.output for key in ("1.1", "1.2", "1.9"))
        assert "brandly takes" in result.output

    def test_edited_file_refuses(self, tmp_path: Path) -> None:
        h = _Harness(tmp_path)
        pack = h.export_pack()
        (pack / "Scene 1" / "Scene 1.1.md").write_text("hand edit\n", encoding="utf-8")

        self._assert_refused(h.run(), h)

    def test_drifted_shot_list_refuses(self, tmp_path: Path) -> None:
        h = _Harness(tmp_path)
        h.export_pack()
        changed = _shots()
        changed[0]["prompt"] = "changed in json"
        h.shots_file.write_text(json.dumps(changed), encoding="utf-8")

        self._assert_refused(h.run(), h)

    def test_conflict_refuses(self, tmp_path: Path) -> None:
        h = _Harness(tmp_path)
        pack = h.export_pack()
        (pack / "Scene 1" / "Scene 1.1.md").write_text("file side\n", encoding="utf-8")
        changed = _shots()
        changed[0]["prompt"] = "json side"
        h.shots_file.write_text(json.dumps(changed), encoding="utf-8")

        self._assert_refused(h.run(), h)

    def test_missing_file_refuses(self, tmp_path: Path) -> None:
        h = _Harness(tmp_path)
        pack = h.export_pack()
        (pack / "Scene 1" / "Scene 1.2.md").unlink()

        self._assert_refused(h.run(), h)

    def test_orphan_file_refuses(self, tmp_path: Path) -> None:
        h = _Harness(tmp_path)
        pack = h.export_pack()
        (pack / "Scene 1" / "Scene 1.9.md").write_text("orphan\n", encoding="utf-8")

        self._assert_refused(h.run(), h)

    def test_dry_run_also_checks(self, tmp_path: Path) -> None:
        h = _Harness(tmp_path)
        pack = h.export_pack()
        (pack / "Scene 1" / "Scene 1.1.md").write_text("hand edit\n", encoding="utf-8")

        self._assert_refused(h.run("--dry-run"), h)


class TestInSync:
    def test_in_sync_uses_the_file_body(self, tmp_path: Path) -> None:
        h = _Harness(tmp_path)
        pack = h.export_pack()
        (pack / "Scene 1" / "Scene 1.1.md").write_text("edited take\n", encoding="utf-8")
        applied = take_prompts.apply(h.pid, _shots(), root=h.root)
        assert applied["verdict"] == "pass"

        result = h.run()
        assert result.exit_code == 0, result.output
        prompts = [call["shot"]["prompt"] for call in h.calls]
        assert prompts == ["edited take", "second beat"]


class TestEscapeHatch:
    def test_ignore_prompt_pack_proceeds_with_warning(self, tmp_path: Path) -> None:
        h = _Harness(tmp_path)
        pack = h.export_pack()
        (pack / "Scene 1" / "Scene 1.1.md").write_text("hand edit\n", encoding="utf-8")

        result = h.run("--ignore-prompt-pack")
        assert result.exit_code == 0, result.output
        assert len(h.calls) == 2
        assert "prompt pack ignored" in result.output.lower()


class TestUnscripted:
    def test_unscripted_does_not_block(self, tmp_path: Path) -> None:
        h = _Harness(tmp_path)
        shots = _shots()
        shots[1]["prompt"] = ""
        h.shots_file.write_text(json.dumps(shots), encoding="utf-8")
        assert take_prompts.export(h.pid, shots, root=h.root)["verdict"] == "pass"

        result = h.run()
        assert result.exit_code == 0, result.output
        assert len(h.calls) == 2
