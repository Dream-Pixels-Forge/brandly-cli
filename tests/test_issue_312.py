"""Issue #312: the script phase assigns scene numbers from the screenplay.

The script phase hardcoded ``"scene": 1`` for every shot, so a 3-act
screenplay collapsed into one scene — ``brandly assemble`` applies its
between-scene transition BETWEEN scenes only, so the transition never fired.

Ruling: the script phase reads ``docs/screenplay/screenplay.md`` (optional
input), extracts the act/scene structure (markdown ``ACT``/``Scene`` headings
or ``INT.``/``EXT.`` screenplay headings) and distributes the shots
contiguously across the acts as scenes (remainder spread to earlier acts).
No screenplay / no act structure → single scene 1 (backward compatible).
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

PID = "scene-proj"


def _make_project(root: Path, **overrides: Any) -> None:
    pm = ProjectManager(root)
    data: dict[str, Any] = {
        "id": PID, "name": "Scene Project",
        "description": "A barista's morning ritual", "shot_count": 6,
    }
    data.update(overrides)
    asyncio.run(pm.create(ProjectData(**data)))


def _seed_current(root: Path, phase: str) -> None:
    pm = ProjectManager(root)
    prior = {p: {"status": "completed"} for p in PHASE_ORDER[: PHASE_ORDER.index(phase)]}
    asyncio.run(pm.update(PID, {"current_phase": phase, "phases": prior}))


def _write(root: Path, rel: str, text: str) -> None:
    path = root / ".brandly" / PID / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_script(root: Path) -> dict[str, Any]:
    director = Director(DirectorConfig(root))
    return asyncio.run(director.run_phase(PID, "script"))


CONCEPT = "# Concept\n\nA warm artisan coffee bar.\n"

THREE_ACT_SCREENPLAY = """# Screenplay

## ACT I — The Commute
Maya cycles through the waking city, beans in her satchel.

## ACT II — The Studio Flow
The espresso ritual: grind, tamp, pull, pour — one unbroken sequence.

## ACT III — Rooftop Sunset
She serves the last cup above the skyline as the sun drops.
"""


class TestSceneNumbersFromScreenplay:
    def test_three_acts_yield_three_scenes(self, tmp_path: Path) -> None:
        _make_project(tmp_path, shot_count=6)
        _seed_current(tmp_path, "script")
        _write(tmp_path, "docs/general/concept.md", CONCEPT)
        _write(tmp_path, "docs/screenplay/screenplay.md", THREE_ACT_SCREENPLAY)

        result = _run_script(tmp_path)
        assert "error" not in result, result
        shots = json.loads(
            (tmp_path / ".brandly" / PID / "shots.json").read_text(encoding="utf-8")
        )
        scenes = [s["scene"] for s in shots]
        assert scenes == [1, 1, 1, 2, 2, 3] or scenes == [1, 1, 2, 2, 3, 3], (
            f"6 shots across 3 acts must distribute contiguously: {scenes}"
        )
        # Shot numbers restart within each scene (clip naming
        # Scene-XX-Shot-<scene>-<shot> depends on it).
        s2 = [s for s in shots if s["scene"] == 2]
        assert [s["shot"] for s in s2] == list(range(1, len(s2) + 1))

    def test_remainder_spreads_to_earlier_acts(self, tmp_path: Path) -> None:
        _make_project(tmp_path, shot_count=10)
        _seed_current(tmp_path, "script")
        _write(tmp_path, "docs/general/concept.md", CONCEPT)
        _write(tmp_path, "docs/screenplay/screenplay.md", THREE_ACT_SCREENPLAY)

        result = _run_script(tmp_path)
        assert "error" not in result, result
        shots = json.loads(
            (tmp_path / ".brandly" / PID / "shots.json").read_text(encoding="utf-8")
        )
        scenes = [s["scene"] for s in shots]
        assert scenes == [1, 1, 1, 1, 2, 2, 2, 3, 3, 3], (
            f"10 shots / 3 acts must be 4+3+3: {scenes}"
        )

    def test_int_ext_headings_also_count(self, tmp_path: Path) -> None:
        screenplay = """# Screenplay

INT. SUBWAY CAR - MORNING
Maya squeezads aboard.

EXT. ROOFTOP - SUNSET
Maya serves the last cup.
"""
        _make_project(tmp_path, shot_count=4)
        _seed_current(tmp_path, "script")
        _write(tmp_path, "docs/general/concept.md", CONCEPT)
        _write(tmp_path, "docs/screenplay/screenplay.md", screenplay)

        result = _run_script(tmp_path)
        assert "error" not in result, result
        shots = json.loads(
            (tmp_path / ".brandly" / PID / "shots.json").read_text(encoding="utf-8")
        )
        scenes = {s["scene"] for s in shots}
        assert scenes == {1, 2}, f"two INT/EXT headings must yield 2 scenes: {scenes}"

    def test_no_screenplay_keeps_single_scene(self, tmp_path: Path) -> None:
        """Backward compatible: without a screenplay every shot is scene 1."""
        _make_project(tmp_path, shot_count=4)
        _seed_current(tmp_path, "script")
        _write(tmp_path, "docs/general/concept.md", CONCEPT)

        result = _run_script(tmp_path)
        assert "error" not in result, result
        shots = json.loads(
            (tmp_path / ".brandly" / PID / "shots.json").read_text(encoding="utf-8")
        )
        assert all(s["scene"] == 1 for s in shots), (
            f"no screenplay must keep single-scene output: "
            f"{[s['scene'] for s in shots]}"
        )

    def test_screenplay_without_structure_keeps_single_scene(self, tmp_path: Path) -> None:
        _make_project(tmp_path, shot_count=4)
        _seed_current(tmp_path, "script")
        _write(tmp_path, "docs/general/concept.md", CONCEPT)
        _write(tmp_path, "docs/screenplay/screenplay.md", "# Screenplay\n\nA quiet tale.\n")

        result = _run_script(tmp_path)
        assert "error" not in result, result
        shots = json.loads(
            (tmp_path / ".brandly" / PID / "shots.json").read_text(encoding="utf-8")
        )
        assert all(s["scene"] == 1 for s in shots)
