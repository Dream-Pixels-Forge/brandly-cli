"""Issue #311: no markdown table-header leak in script-phase shot prompts.

The script phase derives the shot-prompt environment from the FIRST
non-heading line of ``concept.md``. When concept.md opens with a markdown
table (``| Setting | Time | Visual | Audio |``), that header row leaked
verbatim into every shot prompt as ``Setting: | Time | Visual | Audio |``.

Ruling: concept-line extraction skips markdown table rows (``|…``) and
table separator rows — the first real prose line becomes the environment.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from brandly_cli.cmd.production import Director, DirectorConfig
from brandly_cli.constants import PHASE_ORDER
from brandly_cli.project_manager import ProjectManager
from brandly_cli.types import ProjectData

PID = "leak-proj"


def _make_project(root: Path, **overrides: Any) -> None:
    pm = ProjectManager(root)
    data: dict[str, Any] = {
        "id": PID, "name": "Leak Project",
        "description": "A sleek wireless earbud", "shot_count": 4,
    }
    data.update(overrides)
    asyncio.run(pm.create(ProjectData(**data)))


def _seed_current(root: Path, phase: str) -> None:
    pm = ProjectManager(root)
    prior = {p: {"status": "completed"} for p in PHASE_ORDER[: PHASE_ORDER.index(phase)]}
    asyncio.run(pm.update(PID, {"current_phase": phase, "phases": prior}))


def _write_concept(root: Path, text: str) -> None:
    path = root / ".brandly" / PID / "docs" / "general" / "concept.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_script(root: Path) -> dict[str, Any]:
    director = Director(DirectorConfig(root))
    return asyncio.run(director.run_phase(PID, "script"))


class TestNoTableHeaderLeak:
    def test_table_header_is_skipped_for_environment(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        _seed_current(tmp_path, "script")
        _write_concept(
            tmp_path,
            "# Concept\n\n"
            "| Setting | Time | Visual | Audio |\n"
            "|---------|------|---------|-------|\n"
            "| Studio  | Dawn | Warm    | Quiet |\n\n"
            "A sunlit minimal studio at first light.\n",
        )

        result = _run_script(tmp_path)
        assert "error" not in result, result

        shots = json.loads(
            (tmp_path / ".brandly" / PID / "shots.json").read_text(encoding="utf-8")
        )
        assert shots
        for shot in shots:
            assert "Setting: |" not in shot["prompt"], (
                f"markdown table header leaked into the shot prompt: "
                f"{shot['prompt'][:200]}"
            )
        # The first real prose line is the environment.
        assert "sunlit minimal studio" in shots[0]["prompt"]

    def test_plain_concept_still_used(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        _seed_current(tmp_path, "script")
        _write_concept(tmp_path, "# Concept\n\nA rain-soaked neon alley.\n")

        result = _run_script(tmp_path)
        assert "error" not in result, result
        shots = json.loads(
            (tmp_path / ".brandly" / PID / "shots.json").read_text(encoding="utf-8")
        )
        assert "rain-soaked neon alley" in shots[0]["prompt"]
