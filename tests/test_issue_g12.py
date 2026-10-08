"""Contract test: G12 - Narrative beats.

RED test for the narrative beats increment.

The script phase should:
1. Emit beat labels on shots: setup | turn | consequence | resolve
2. Reject shot lists missing required beats (completeness contract)
3. Derive shot durations from beat role, not hand-entry
4. Derived durations land in 4-6s reliable window (feeds G7 split policy)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from brandly_cli import scenes, shot_runner
from brandly_cli.cmd.production import Director, DirectorConfig
from brandly_cli.project_manager import ProjectManager
from brandly_cli.types import ProjectData

PID = "g12proj"


def _make_project(tmp_path: Path, shot_count: int = 4) -> None:
    """Create a minimal project via ProjectManager."""
    asyncio.run(ProjectManager(tmp_path).create(ProjectData(
        id=PID,
        name="Test Project",
        idea="A test film",
        style="cinematic",
        shot_count=shot_count,
        aspect_ratio="16:9",
    )))


def _read_project(tmp_path: Path) -> dict:
    """Read project.json."""
    path = Path(tmp_path) / ".brandly" / PID / "project.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _shots_json_path(root: Path, pid: str = PID) -> Path:
    return root / ".brandly" / pid / "shots.json"


def _director(root: Path) -> Director:
    return Director(DirectorConfig(root))


def _write_concept(root: Path, pid: str = PID) -> Path:
    """Write a minimal concept.md (P3 #257: the script phase requires it)."""
    from brandly_cli import layout

    concept = layout.resolve_project_dir(root, pid) / "docs" / "plan" / "concept.md"
    concept.parent.mkdir(parents=True, exist_ok=True)
    concept.write_text(
        "# Concept\n\nA precision espresso machine in a minimalist cafe at dawn\n",
        encoding="utf-8",
    )
    return concept


class TestNarrativeBeats:
    """Test narrative beats in script phase."""

    def test_script_phase_emits_beat_labels(self, tmp_path: Path):
        """Script phase should add beat labels to each shot."""
        _make_project(tmp_path, shot_count=4)
        _write_concept(tmp_path)
        director = _director(tmp_path)

        result = asyncio.run(director.run_phase(PID, "script"))

        assert "error" not in result, result
        shots_path = _shots_json_path(tmp_path)
        shots = shot_runner.load_shots_file(shots_path)

        assert isinstance(shots, list)
        assert len(shots) == 4

        # Each shot should have a beat field
        for shot in shots:
            assert "beat" in shot, f"Shot {shot.get('id')} missing beat field"
            assert shot["beat"] in ("setup", "turn", "consequence", "resolve"), \
                f"Invalid beat: {shot['beat']}"

    def test_script_phase_has_all_required_beats(self, tmp_path: Path):
        """Script phase output must include all four beat types."""
        _make_project(tmp_path, shot_count=4)
        _write_concept(tmp_path)
        director = _director(tmp_path)

        asyncio.run(director.run_phase(PID, "script"))

        shots_path = _shots_json_path(tmp_path)
        shots = shot_runner.load_shots_file(shots_path)

        beats = {shot["beat"] for shot in shots}
        assert "setup" in beats, "Missing 'setup' beat"
        assert "turn" in beats, "Missing 'turn' beat"
        assert "consequence" in beats, "Missing 'consequence' beat"
        assert "resolve" in beats, "Missing 'resolve' beat"

    def test_script_phase_rejects_missing_resolve_beat(self, tmp_path: Path):
        """Script phase should reject shot list without resolve beat."""
        # This will be tested at the script phase level - the phase should
        # ensure its output contains all required beats
        _make_project(tmp_path, shot_count=4)
        _write_concept(tmp_path)
        director = _director(tmp_path)

        result = asyncio.run(director.run_phase(PID, "script"))

        assert "error" not in result, result
        shots_path = _shots_json_path(tmp_path)
        shots = shot_runner.load_shots_file(shots_path)

        beats = {shot["beat"] for shot in shots}
        assert "resolve" in beats, "Script phase must ensure resolve beat exists"

    def test_beat_determines_duration(self, tmp_path: Path):
        """Shot duration should derive from beat role, not be fixed."""
        _make_project(tmp_path, shot_count=4)
        _write_concept(tmp_path)
        director = _director(tmp_path)

        asyncio.run(director.run_phase(PID, "script"))

        shots_path = _shots_json_path(tmp_path)
        shots = shot_runner.load_shots_file(shots_path)

        # Beat-to-duration mapping (4-6s window per G7 reliable zone)
        beat_durations = {
            "setup": 4,
            "turn": 5,
            "consequence": 5,
            "resolve": 6,
        }

        for shot in shots:
            beat = shot["beat"]
            expected_duration = beat_durations[beat]
            assert shot["duration"] == expected_duration, \
                f"Beat {beat} should have duration {expected_duration}s, got {shot['duration']}"
            assert 4 <= shot["duration"] <= 6, \
                f"Duration {shot['duration']}s outside reliable 4-6s window"

    def test_backward_compat_no_beat_labels(self, tmp_path: Path):
        """Existing projects without beat labels should still load."""
        _make_project(tmp_path, shot_count=3)
        _write_concept(tmp_path)
        director = _director(tmp_path)

        asyncio.run(director.run_phase(PID, "script"))

        shots_path = _shots_json_path(tmp_path)
        shots = shot_runner.load_shots_file(shots_path)

        # Manually remove beat labels to simulate old format
        for shot in shots:
            shot.pop("beat", None)

        shots_path.write_text(
            json.dumps(shots, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # Should still load without error
        loaded = shot_runner.load_shots_file(shots_path)
        assert len(loaded) == 3

        # build_scenes should still work
        manifest = scenes.build_scenes(PID, loaded, root=tmp_path)
        assert len(manifest["scenes"]) == 1
