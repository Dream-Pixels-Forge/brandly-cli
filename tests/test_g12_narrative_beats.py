r"""Tests for G12: Narrative Beats — give the film a shape.

Tests that beat labels are required on shots, durations derive from beat roles,
and the script phase enforces beat completeness.

Also tests F5: Per-beat shot prompt variation (#248) - that shot prompts vary by beat role.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from brandly_cli import layout, scenes
from brandly_cli.video_prompts import build_single_shot_prompt


def _write_scenes_and_clips(tmp_path: Path, project_id: str):
    """Helper to write scenes and create dummy clips."""
    shot_list = [
        {"id": "s1", "prompt": "p1", "duration": 6, "scene": 1, "shot": 1, "beat": "setup"},
        {"id": "s2", "prompt": "p2", "duration": 6, "scene": 1, "shot": 2, "beat": "turn"},
        {"id": "s3", "prompt": "p3", "duration": 6, "scene": 2, "shot": 1, "beat": "consequence"},
        {"id": "s4", "prompt": "p4", "duration": 6, "scene": 2, "shot": 2, "beat": "resolve"},
    ]
    scenes.write_scenes(project_id, shot_list, root=tmp_path)

    videos_root = layout.resolve_media_root(tmp_path, project_id, "videos")
    (videos_root / "scenes").mkdir(parents=True, exist_ok=True)
    (videos_root / "scenes" / "Scene-01-Shot-1-1.mp4").write_bytes(b"clip1")
    (videos_root / "scenes" / "Scene-01-Shot-1-2.mp4").write_bytes(b"clip2")
    (videos_root / "scenes" / "Scene-02-Shot-2-1.mp4").write_bytes(b"clip3")
    (videos_root / "scenes" / clip_filename(2, 2)).write_bytes(b"clip4")


class TestG12NarrativeBeats:
    """G12: Narrative Beats — give the film a shape."""

    def test_beat_labels_required_on_shots(self, tmp_path: Path):
        """Shot lists with beat labels are accepted."""
        shot_list = [
            {"id": "s1", "prompt": "p1", "duration": 6, "scene": 1, "shot": 1, "beat": "setup"},
            {"id": "s2", "prompt": "p2", "duration": 6, "scene": 1, "shot": 2, "beat": "turn"},
        ]
        scenes.write_scenes("test-proj", shot_list, root=tmp_path)

        manifest = scenes.load_scenes("test-proj", root=tmp_path)
        assert manifest is not None
        assert manifest["scenes"][0]["shots"][0]["beat"] == "setup"
        assert manifest["scenes"][0]["shots"][1]["beat"] == "turn"

    def test_invalid_beat_label_rejected(self, tmp_path: Path):
        """Invalid beat labels are rejected."""
        shot_list = [
            {"id": "s1", "prompt": "p1", "duration": 6, "scene": 1, "shot": 1, "beat": "invalid_beat"},
        ]
        with pytest.raises(ValueError, match="Invalid beat"):
            scenes.write_scenes("test-proj", shot_list, root=tmp_path)

    def test_script_phase_rejects_missing_resolve_beat(self, tmp_path: Path):
        """Script phase rejects shot list missing required 'resolve' beat."""
        project_id = "test-proj"
        # Shot list missing 'resolve' beat
        shot_list = [
            {"id": "s1", "prompt": "p1", "duration": 6, "scene": 1, "shot": 1, "beat": "setup"},
            {"id": "s2", "prompt": "p2", "duration": 6, "scene": 1, "shot": 2, "beat": "turn"},
            {"id": "s3", "prompt": "p3", "duration": 6, "scene": 2, "shot": 1, "beat": "consequence"},
        ]
        scenes.write_scenes(project_id, shot_list, root=tmp_path)

        # The script phase should reject this
        # This will be implemented in the script command
        # Write the shots file
        import json

        from click.testing import CliRunner

        from brandly_cli.cli import cli
        shots_file = tmp_path / "shots.json"
        shots_file.write_text(json.dumps(shot_list))

        runner = CliRunner(env={"ROOT": str(tmp_path)})
        result = runner.invoke(cli, ["script", project_id, "--shots", str(shots_file)])
        assert result.exit_code != 0
        assert "resolve" in result.output.lower()

    def test_beat_role_determines_duration(self, tmp_path: Path):
        """Beat role determines duration; hand-edited duration is ignored."""
        shot_list = [
            {"id": "s1", "prompt": "p1", "duration": 10, "scene": 1, "shot": 1, "beat": "setup"},
            {"id": "s2", "prompt": "p2", "duration": 10, "scene": 1, "shot": 2, "beat": "turn"},
            {"id": "s3", "prompt": "p3", "duration": 10, "scene": 2, "shot": 1, "beat": "consequence"},
            {"id": "s4", "prompt": "p4", "duration": 10, "scene": 2, "shot": 2, "beat": "resolve"},
        ]
        scenes.write_scenes("test-proj", shot_list, root=tmp_path)

        manifest = scenes.load_scenes("test-proj", root=tmp_path)
        # The script phase should override durations based on beat roles
        # setup: 4-6s, turn: 5-7s, consequence: 5-7s, resolve: 4-6s
        for scene in manifest["scenes"]:
            for shot in scene["shots"]:
                beat = shot["beat"]
                if beat == "setup":
                    assert 4 <= shot["duration"] <= 6
                elif beat == "turn":
                    assert 5 <= shot["duration"] <= 7
                elif beat == "consequence":
                    assert 5 <= shot["duration"] <= 7
                elif beat == "resolve":
                    assert 4 <= shot["duration"] <= 6

    def test_backcompat_no_beat_labels(self, tmp_path: Path):
        """Existing projects without beat labels still load (back-compat)."""
        # Old format without beat labels
        shot_list = [
            {"id": "s1", "prompt": "p1", "duration": 6, "scene": 1, "shot": 1},
            {"id": "s2", "prompt": "p2", "duration": 6, "scene": 1, "shot": 2},
        ]
        scenes.write_scenes("test-proj", shot_list, root=tmp_path)

        manifest = scenes.load_scenes("test-proj", root=tmp_path)
        assert manifest is not None
        # Shots without beats still load (beat key absent — legacy schema
        # preserved; G12 adds beat/duration only when a beat is declared).

    def test_beat_duration_derived_not_overridden(self, tmp_path: Path):
        """Editing a duration alone does not override the beat-derived value."""
        shot_list = [
            {"id": "s1", "prompt": "p1", "duration": 15, "scene": 1, "shot": 1, "beat": "setup"},
        ]
        scenes.write_scenes("test-proj", shot_list, root=tmp_path)

        manifest = scenes.load_scenes("test-proj", root=tmp_path)
        # The stored duration should be the beat-derived one, not 15
        shot = manifest["scenes"][0]["shots"][0]
        assert shot["duration"] != 15
        assert 4 <= shot["duration"] <= 6

    def test_f5_per_beat_shot_prompt_variation(self):
        """F5: Shot prompts should vary by beat role while keeping global style consistent."""
        # Test with cinematic style (default)
        subject = "test product"
        action_base = "demonstrates key features"
        environment_base = "clean studio setting"
        style = "cinematic"

        # Generate prompts for each beat role
        prompts = {}
        for beat in ["setup", "turn", "consequence", "resolve"]:
            prompt = build_single_shot_prompt(
                subject=subject,
                action=action_base,
                environment=environment_base,
                style=style,
                beat_role=beat,
            )
            prompts[beat] = prompt

        # Check that all prompts are different
        prompt_values = list(prompts.values())
        assert len(set(prompt_values)) == 4, "All beat role prompts should be unique"

        # Check that each prompt contains beat-specific action and setting
        # Setup beat: should contain "introduces the subject" and "wide establishing shot"
        setup_prompt = prompts["setup"]
        assert "introduces the subject" in setup_prompt.lower()
        assert "wide establishing shot" in setup_prompt.lower()

        # Turn beat: should contain "encounters a challenge" and "medium shot"
        turn_prompt = prompts["turn"]
        assert "encounters a challenge" in turn_prompt.lower()
        assert "medium shot" in turn_prompt.lower()

        # Consequence beat: should contain "responds to the challenge" and "close-up"
        consequence_prompt = prompts["consequence"]
        assert "responds to the challenge" in consequence_prompt.lower()
        assert "close-up" in consequence_prompt.lower()

        # Resolve beat: should contain "overcomes the challenge" and "wide shot"
        resolve_prompt = prompts["resolve"]
        assert "overcomes the challenge" in resolve_prompt.lower()
        assert "wide shot" in resolve_prompt.lower()

        # Check that global style is consistent
        for prompt in prompt_values:
            assert style.lower() in prompt.lower()

        # Test with different style
        style = "commercial"
        prompts_commercial = {}
        for beat in ["setup", "turn", "consequence", "resolve"]:
            prompt = build_single_shot_prompt(
                subject=subject,
                action=action_base,
                environment=environment_base,
                style=style,
                beat_role=beat,
            )
            prompts_commercial[beat] = prompt

        # Check that all prompts are different
        prompt_values_commercial = list(prompts_commercial.values())
        assert len(set(prompt_values_commercial)) == 4, "All beat role prompts should be unique for commercial style"

        # Check that commercial style is present
        for prompt in prompt_values_commercial:
            assert style.lower() in prompt.lower()


def clip_filename(scene: int, index_in_scene: int, ext: str = ".mp4") -> str:
    return f"Scene-{scene:02d}-Shot-{scene}-{index_in_scene}.mp4"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
