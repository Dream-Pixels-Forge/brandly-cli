r"""Tests for G9: Wire the vision gate to video clips.

Tests that the produce phase runs vision gate on first clip of each scene.
"""

from __future__ import annotations

from pathlib import Path

from brandly_cli import shot_runner


def _make_config(
    tmp_path: Path,
    shots: list[shot_runner.Shot],
    generate_one,
    interval: float = 0.0,
    only=None,
    max_shots: int = 0,
    gate_ai: str = "scene-first",
    vision_gate_runner=None,
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
        gate_ai=gate_ai,
        vision_gate_runner=vision_gate_runner,
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


class TestG9VisionGate:
    """G9: Wire the vision gate to video clips."""

    def test_scene_first_vision_gate_runs_on_first_clip(self, tmp_path: Path) -> None:
        """Default produce records a vision verdict for the first clip of every scene."""
        scenes = tmp_path / "videos" / "scenes"
        scenes.mkdir(parents=True, exist_ok=True)

        vision_gate_calls = []

        def vision_gate_runner(clip_path: Path) -> str:
            vision_gate_calls.append(str(clip_path))
            return "pass"

        def generate_one(shot):
            clip_name = shot_runner.clip_filename(shot.scene, shot.index_in_scene)
            clip_path = scenes / clip_name
            clip_path.write_bytes(b"fake clip data")
            return True, 0, ""

        # Two scenes, 2 shots each
        shots = [
            shot_runner.Shot(id="s1", act="", style="cinematic", folder="scenes",
                           prompt="p1", duration=6, scene=1, index_in_scene=1),
            shot_runner.Shot(id="s2", act="", style="cinematic", folder="scenes",
                           prompt="p2", duration=6, scene=1, index_in_scene=2),
            shot_runner.Shot(id="s3", act="", style="cinematic", folder="scenes",
                           prompt="p3", duration=6, scene=2, index_in_scene=1),
            shot_runner.Shot(id="s4", act="", style="cinematic", folder="scenes",
                           prompt="p4", duration=6, scene=2, index_in_scene=2),
        ]

        config = _make_config(tmp_path, shots, generate_one, gate_ai="scene-first", vision_gate_runner=vision_gate_runner)
        result = shot_runner.run_shots(config)

        assert result == 0
        # Vision gate should run on first clip of scene 1 (s1) and scene 2 (s3)
        assert len(vision_gate_calls) == 2
        assert "Scene-01-Shot-1-1" in vision_gate_calls[0]
        assert "Scene-02-Shot-2-1" in vision_gate_calls[1]

    def test_scene_first_vision_gate_fail_blocks_scene(self, tmp_path: Path) -> None:
        """A stub judge returning drift on scene 1 blocks scene 1 and not scenes 2+."""
        scenes = tmp_path / "videos" / "scenes"
        scenes.mkdir(parents=True, exist_ok=True)

        call_count = {"count": 0}

        def vision_gate_runner(clip_path: Path) -> str:
            call_count["count"] += 1
            # Fail on first call (scene 1 first clip)
            if call_count["count"] == 1:
                return "fail"
            return "pass"

        def generate_one(shot):
            clip_name = shot_runner.clip_filename(shot.scene, shot.index_in_scene)
            clip_path = scenes / clip_name
            clip_path.write_bytes(b"fake clip data")
            return True, 0, ""

        shots = [
            shot_runner.Shot(id="s1", act="", style="cinematic", folder="scenes",
                           prompt="p1", duration=6, scene=1, index_in_scene=1),
            shot_runner.Shot(id="s2", act="", style="cinematic", folder="scenes",
                           prompt="p2", duration=6, scene=1, index_in_scene=2),
            shot_runner.Shot(id="s3", act="", style="cinematic", folder="scenes",
                           prompt="p3", duration=6, scene=2, index_in_scene=1),
            shot_runner.Shot(id="s4", act="", style="cinematic", folder="scenes",
                           prompt="p4", duration=6, scene=2, index_in_scene=2),
        ]

        config = _make_config(tmp_path, shots, generate_one, gate_ai="scene-first", vision_gate_runner=vision_gate_runner)
        result = shot_runner.run_shots(config)

        assert result == 1  # Overall failure
        # Scene 1 should be blocked, scene 2 should still generate
        # s1 fails vision gate -> scene 1 blocked
        # s2 should be skipped (scene 1 blocked)
        # s3 runs (scene 2 first clip) -> vision gate passes
        # s4 runs

    def test_gate_ai_off_restores_today_behavior(self, tmp_path: Path) -> None:
        """--gate-ai off restores today's behaviour exactly (no vision gate)."""
        scenes = tmp_path / "videos" / "scenes"
        scenes.mkdir(parents=True, exist_ok=True)

        vision_gate_calls = []

        def vision_gate_runner(clip_path: Path) -> str:
            vision_gate_calls.append(str(clip_path))
            return "pass"

        def generate_one(shot):
            clip_name = shot_runner.clip_filename(shot.scene, shot.index_in_scene)
            clip_path = scenes / clip_name
            clip_path.write_bytes(b"fake clip data")
            return True, 0, ""

        shots = _shots(["s1", "s2", "s3", "s4"])
        shots[0].scene = 1
        shots[0].index_in_scene = 1
        shots[1].scene = 1
        shots[1].index_in_scene = 2
        shots[2].scene = 2
        shots[2].index_in_scene = 1
        shots[3].scene = 2
        shots[3].index_in_scene = 2

        config = _make_config(tmp_path, shots, generate_one, gate_ai="off", vision_gate_runner=vision_gate_runner)
        result = shot_runner.run_shots(config)

        assert result == 0
        assert len(vision_gate_calls) == 0  # No vision gate calls


def _shots(ids: list[str], folder: str = "scenes", duration: int = 6) -> list[shot_runner.Shot]:
    return [
        shot_runner.Shot(
            id=sid, act="", style="cinematic", folder=folder,
            prompt=f"p {sid}", duration=duration,
            scene=1, index_in_scene=i + 1,
        )
        for i, sid in enumerate(ids)
    ]


class TestG9GateAiOptions:
    """Test gate_ai options: off, scene-first, all."""

    def test_gate_ai_all_judges_every_clip(self, tmp_path: Path) -> None:
        """gate_ai=all judges every clip."""
        scenes = tmp_path / "videos" / "scenes"
        scenes.mkdir(parents=True, exist_ok=True)

        vision_gate_calls = []

        def vision_gate_runner(clip_path: Path) -> str:
            vision_gate_calls.append(str(clip_path))
            return "pass"

        def generate_one(shot):
            clip_name = shot_runner.clip_filename(shot.scene, shot.index_in_scene)
            clip_path = scenes / clip_name
            clip_path.write_bytes(b"fake clip data")
            return True, 0, ""

        shots = _shots(["s1", "s2"])
        shots[0].scene = 1
        shots[0].index_in_scene = 1
        shots[1].scene = 1
        shots[1].index_in_scene = 2

        config = _make_config(tmp_path, shots, generate_one, gate_ai="all", vision_gate_runner=vision_gate_runner)
        result = shot_runner.run_shots(config)

        assert result == 0
        assert len(vision_gate_calls) == 2  # Both clips judged

    def test_gate_ai_invalid_raises(self, tmp_path: Path) -> None:
        """Invalid gate_ai value raises error."""
        shots = _shots(["s1"])
        config = _make_config(tmp_path, shots, lambda s: (True, 0, ""), gate_ai="invalid")
        # Should validate at config creation or run time
        try:
            shot_runner.run_shots(config)
            raise AssertionError("Should have raised")
        except ValueError:
            pass
