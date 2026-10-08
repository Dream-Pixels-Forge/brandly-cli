r"""Tests for G7: Duration Truth — measure every returned clip.

Tests that the shot runner measures actual clip durations, records
requested vs measured, and never reports a short clip as OK.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from brandly_cli import shot_runner


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


def _shots(ids: list[str], folder: str = "scenes", duration: int = 6) -> list[shot_runner.Shot]:
    return [
        shot_runner.Shot(
            id=sid, act="", style="cinematic", folder=folder,
            prompt=f"p {sid}", duration=duration,
            scene=1, index_in_scene=i + 1,
        )
        for i, sid in enumerate(ids)
    ]


class TestG7DurationTruth:
    """G7: Duration Truth — measure every returned clip."""

    def test_short_clip_is_marked_short_not_ok(self, tmp_path: Path) -> None:
        """A clip that measures shorter than tolerance is marked SHORT, not OK."""
        scenes = tmp_path / "videos" / "scenes"
        scenes.mkdir(parents=True, exist_ok=True)

        def generate_one(shot):
            clip_name = shot_runner.clip_filename(shot.scene, shot.index_in_scene)
            clip_path = scenes / clip_name
            clip_path.write_bytes(b"fake clip data")
            return True, 0, ""

        shots = _shots(["shot01"], duration=6)
        shots[0].requested_s = 6

        config = _make_config(tmp_path, shots, generate_one)

        with patch("brandly_cli.shot_runner._probe_video_duration", return_value=4.5):
            shot_runner.run_shots(config)

        assert shots[0].duration_status == "short"
        assert shots[0].measured_s == 4.5
        assert shots[0].delta_s == -1.5
        assert shots[0].requested_s == 6

    def test_clip_within_tolerance_is_ok(self, tmp_path: Path) -> None:
        """A clip within tolerance (e.g., 5.5s for 6s request) is marked OK."""
        scenes = tmp_path / "videos" / "scenes"
        scenes.mkdir(parents=True, exist_ok=True)

        def generate_one(shot):
            clip_name = shot_runner.clip_filename(shot.scene, shot.index_in_scene)
            clip_path = scenes / clip_name
            clip_path.write_bytes(b"fake clip data")
            return True, 0, ""

        shots = _shots(["shot01"], duration=6)
        shots[0].requested_s = 6

        config = _make_config(tmp_path, shots, generate_one)

        with patch("brandly_cli.shot_runner._probe_video_duration", return_value=5.5):
            shot_runner.run_shots(config)

        assert shots[0].duration_status == "ok"
        assert shots[0].measured_s == 5.5
        assert shots[0].delta_s == -0.5
        assert shots[0].requested_s == 6

    def test_clip_longer_than_requested_is_ok(self, tmp_path: Path) -> None:
        """A clip longer than requested (e.g., 7s for 6s) is still OK (within tolerance)."""
        scenes = tmp_path / "videos" / "scenes"
        scenes.mkdir(parents=True, exist_ok=True)

        def generate_one(shot):
            clip_name = shot_runner.clip_filename(shot.scene, shot.index_in_scene)
            clip_path = scenes / clip_name
            clip_path.write_bytes(b"fake clip data")
            return True, 0, ""

        shots = _shots(["shot01"], duration=6)
        shots[0].requested_s = 6

        config = _make_config(tmp_path, shots, generate_one)

        with patch("brandly_cli.shot_runner._probe_video_duration", return_value=7.0):
            shot_runner.run_shots(config)

        assert shots[0].duration_status == "ok"
        assert shots[0].measured_s == 7.0
        assert shots[0].delta_s == 1.0

    def test_clip_way_longer_is_short_status(self, tmp_path: Path) -> None:
        """A clip significantly longer (e.g., 10s for 6s) is marked SHORT (over-long)."""
        scenes = tmp_path / "videos" / "scenes"
        scenes.mkdir(parents=True, exist_ok=True)

        def generate_one(shot):
            clip_name = shot_runner.clip_filename(shot.scene, shot.index_in_scene)
            clip_path = scenes / clip_name
            clip_path.write_bytes(b"fake clip data")
            return True, 0, ""

        shots = _shots(["shot01"], duration=6)
        shots[0].requested_s = 6

        config = _make_config(tmp_path, shots, generate_one)

        with patch("brandly_cli.shot_runner._probe_video_duration", return_value=10.0):
            shot_runner.run_shots(config)

        assert shots[0].duration_status == "short"
        assert shots[0].measured_s == 10.0
        assert shots[0].delta_s == 4.0


class TestG7ToleranceHelpers:
    """Test the G7 tolerance calculation helpers."""

    def test_duration_tolerance(self):
        from brandly_cli.shot_runner import duration_tolerance

        assert duration_tolerance(5) == 1.0
        assert duration_tolerance(8) == 1.0
        assert duration_tolerance(10) == 1.0
        assert duration_tolerance(20) == 2.0
        assert duration_tolerance(0) == 1.0

    def test_is_within_tolerance(self):
        from brandly_cli.shot_runner import is_within_tolerance

        assert is_within_tolerance(6, 5.5) is True
        assert is_within_tolerance(6, 6.5) is True
        assert is_within_tolerance(6, 5.0) is True
        assert is_within_tolerance(6, 7.0) is True
        assert is_within_tolerance(6, 4.9) is False
        assert is_within_tolerance(6, 7.1) is False

        assert is_within_tolerance(10, 9.5) is True
        assert is_within_tolerance(10, 8.9) is False

    def test_duration_status(self):
        from brandly_cli.shot_runner import duration_status

        assert duration_status(6, 5.5) == "ok"
        assert duration_status(6, 7.0) == "ok"
        assert duration_status(6, 4.5) == "short"
        assert duration_status(6, None) == "ok"


class TestG7Timeline:
    """Test the get_timeline function with measured durations."""

    def test_get_timeline_includes_measured(self, tmp_path: Path):
        from brandly_cli import layout
        from brandly_cli.planning import production_plan_path
        from brandly_cli.shot_runner import clip_filename, get_timeline

        project_id = "test123"
        layout.resolve_project_dir(tmp_path, project_id).mkdir(parents=True, exist_ok=True)

        plan_dir = layout.docs_dir(layout.resolve_project_dir(tmp_path, project_id), "plan")
        plan_dir.mkdir(parents=True, exist_ok=True)
        shots_data = [
            {"id": "shot01", "duration": 6, "scene": 1, "index_in_scene": 1},
            {"id": "shot02", "duration": 8, "scene": 1, "index_in_scene": 2},
        ]
        plan_path = production_plan_path(project_id, root=tmp_path)
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text('{"shots": ' + str(shots_data).replace("'", '"') + '}')

        from brandly_cli.shot_runner import PROGRESS_FILENAME, ProgressLog
        progress_log = ProgressLog(
            layout.docs_dir(layout.resolve_project_dir(tmp_path, project_id), "tmp")
            / PROGRESS_FILENAME
        )
        progress_log.path.parent.mkdir(parents=True, exist_ok=True)
        progress_log.record("shot01", "OK", 0)
        progress_log.record("shot02", "OK", 0)

        videos_root = layout.resolve_media_root(tmp_path, project_id, "videos") / "scenes"
        videos_root.mkdir(parents=True, exist_ok=True)
        (videos_root / clip_filename(1, 1)).write_bytes(b"clip1")
        (videos_root / clip_filename(1, 2)).write_bytes(b"clip2")

        with patch("brandly_cli.shot_runner._probe_video_duration", side_effect=[5.5, 7.0]):
            timeline = get_timeline(project_id, root=tmp_path)

        assert len(timeline) == 2
        assert timeline[0]["shot_id"] == "shot01"
        assert timeline[0]["requested_s"] == 6
        assert timeline[0]["measured_s"] == 5.5
        assert timeline[0]["delta_s"] == -0.5
        assert timeline[0]["duration_status"] == "ok"

        assert timeline[1]["shot_id"] == "shot02"
        assert timeline[1]["requested_s"] == 8
        assert timeline[1]["measured_s"] == 7.0
        assert timeline[1]["delta_s"] == -1.0
        assert timeline[1]["duration_status"] == "ok"

    def test_get_timeline_pending_shots(self, tmp_path: Path):
        from brandly_cli import layout
        from brandly_cli.planning import production_plan_path
        from brandly_cli.shot_runner import get_timeline

        project_id = "test456"
        layout.resolve_project_dir(tmp_path, project_id).mkdir(parents=True, exist_ok=True)

        plan_dir = layout.docs_dir(layout.resolve_project_dir(tmp_path, project_id), "plan")
        plan_dir.mkdir(parents=True, exist_ok=True)
        shots_data = [
            {"id": "shot01", "duration": 6, "scene": 1, "index_in_scene": 1},
            {"id": "shot02", "duration": 8, "scene": 1, "index_in_scene": 2},
        ]
        plan_path = production_plan_path(project_id, root=tmp_path)
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text('{"shots": ' + str(shots_data).replace("'", '"') + '}')

        timeline = get_timeline(project_id, root=tmp_path)

        assert len(timeline) == 2
        assert timeline[0]["duration_status"] == "pending"
        assert timeline[0]["measured_s"] is None
        assert timeline[1]["duration_status"] == "pending"
        assert timeline[1]["measured_s"] is None
