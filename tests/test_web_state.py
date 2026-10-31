"""Atomic save contract for TimelineState.

``TimelineState.save()`` must never leave a half-written ``timeline.json`` or
``shots.json`` on disk. A crash mid-write previously left drifted JSON that
corrupted the project state. The fix: write to a temp file in the same
directory, then ``os.replace()`` (atomic on POSIX) into place.
"""

from __future__ import annotations

import json
from pathlib import Path

from brandly_cli.web.models import ClipUpdate
from brandly_cli.web.state import TimelineState

TIMELINE_FILENAME = "timeline.json"
SHOTS_FILENAME = "shots.json"


def _make_project(root: Path, project_id: str = "my-proj") -> Path:
    proj_dir = root / ".brandly" / project_id
    (proj_dir / "docs" / "tmp").mkdir(parents=True)
    (proj_dir / "project.json").write_text(
        json.dumps({"id": project_id, "name": "My Project"}), encoding="utf-8"
    )
    return root


def _timeline_path(root: Path, project_id: str) -> Path:
    proj_dir = root / ".brandly" / project_id
    from brandly_cli import layout

    return layout.docs_dir(proj_dir, "tmp") / TIMELINE_FILENAME


def _shots_path(root: Path, project_id: str) -> Path:
    proj_dir = root / ".brandly" / project_id
    return proj_dir / SHOTS_FILENAME


def _write_initial_timeline(root: Path, project_id: str) -> None:
    path = _timeline_path(root, project_id)
    path.write_text(
        json.dumps(
            {
                "project_id": project_id,
                "clips": [
                    {
                        "id": "c1",
                        "shot_id": "s1",
                        "clip_path": "videos/scenes/c1.mp4",
                        "prompt": "hello",
                        "duration": 5.0,
                        "status": "generated",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


class TestAtomicTimelineSave:
    def test_save_writes_complete_json(self, tmp_path: Path) -> None:
        """After save(), timeline.json is valid, complete JSON (never truncated)."""
        _make_project(tmp_path)
        _write_initial_timeline(tmp_path, "my-proj")

        state = TimelineState("my-proj", tmp_path)
        state.load()
        state.get_clip("c1")
        state.update_clip("c1", ClipUpdate(duration=7.0))
        state.save()

        text = _timeline_path(tmp_path, "my-proj").read_text(encoding="utf-8")
        data = json.loads(text)  # must parse cleanly — no truncation
        assert data["clips"][0]["duration"] == 7.0

    def test_no_temp_files_left_behind(self, tmp_path: Path) -> None:
        """save() must not leave .tmp or other temp files in docs/tmp/."""
        _make_project(tmp_path)
        _write_initial_timeline(tmp_path, "my-proj")

        state = TimelineState("my-proj", tmp_path)
        state.load()
        state.update_clip("c1", ClipUpdate(duration=7.0))
        state.save()

        tmp_dir = tmp_path / ".brandly" / "my-proj" / "docs" / "tmp"
        leftovers = [p for p in tmp_dir.iterdir() if p.name != TIMELINE_FILENAME]
        assert not leftovers, f"temp files left behind: {leftovers}"

    def test_shots_json_atomic(self, tmp_path: Path) -> None:
        """shots.json is written atomically too (no partial JSON)."""
        _make_project(tmp_path)
        _write_initial_timeline(tmp_path, "my-proj")

        state = TimelineState("my-proj", tmp_path)
        state.load()
        state.save()

        shots = _shots_path(tmp_path, "my-proj")
        assert shots.is_file()
        data = json.loads(shots.read_text(encoding="utf-8"))
        assert data[0]["name"] == "c1"

    def test_concurrent_saves_do_not_corrupt(self, tmp_path: Path) -> None:
        """Two sequential saves both leave valid JSON (simulates rapid edits)."""
        _make_project(tmp_path)
        _write_initial_timeline(tmp_path, "my-proj")

        state = TimelineState("my-proj", tmp_path)
        state.load()
        state.update_clip("c1", ClipUpdate(duration=7.0))
        state.save()
        state.update_clip("c1", ClipUpdate(duration=9.0))
        state.save()

        data = json.loads(_timeline_path(tmp_path, "my-proj").read_text(encoding="utf-8"))
        assert data["clips"][0]["duration"] == 9.0


class TestAtomicShotsSave:
    def test_shots_not_left_empty_on_failure_path(self, tmp_path: Path) -> None:
        """An empty timeline writes no shots file (not an empty/partial one)."""
        _make_project(tmp_path)
        _write_initial_timeline(tmp_path, "my-proj")

        state = TimelineState("my-proj", tmp_path)
        state.load()
        # Replace all clips with an empty list -> shots.json should not be created
        state.replace_clips([])
        state.save()

        shots = _shots_path(tmp_path, "my-proj")
        assert not shots.is_file(), "shots.json must not exist for empty timeline"
