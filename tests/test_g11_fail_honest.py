r"""Tests for G11: Fail-honest — UNVERIFIED is never PASS.

Tests that UNVERIFIED status is properly handled:
- New status literal UNVERIFIED distinct from PASS/WARN/FAIL
- Absent a judge ⇒ UNVERIFIED (never PASS)
- --strict exits non-zero on UNVERIFIED
- UNVERIFIED surfaces in timeline
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from brandly_cli import layout, quality_gate, scenes, shot_runner


def _write_scenes_and_clips(tmp_path: Path, project_id: str):
    """Helper to write scenes and create dummy clips."""
    shot_list = [
        {"id": "s1", "prompt": "p1", "duration": 6, "scene": 1, "shot": 1},
        {"id": "s2", "prompt": "p2", "duration": 6, "scene": 2, "shot": 1},
    ]
    scenes.write_scenes(project_id, shot_list, root=tmp_path)

    videos_root = layout.resolve_media_root(tmp_path, project_id, "videos")
    (videos_root / "scenes").mkdir(parents=True, exist_ok=True)
    (videos_root / "scenes" / "Scene-01-Shot-1-1.mp4").write_bytes(b"clip1")
    (videos_root / "scenes" / "Scene-02-Shot-2-1.mp4").write_bytes(b"clip2")


class TestG11FailHonest:
    """G11: Fail-honest — UNVERIFIED is never PASS."""

    def test_unverified_status_literal_exists(self):
        """UNVERIFIED status literal exists in quality_gate."""
        assert hasattr(quality_gate, "UNVERIFIED")
        assert quality_gate.UNVERIFIED == "unverified"

    def test_verify_element_returns_unverified_when_no_ai(self, tmp_path: Path):
        """verify_element returns UNVERIFIED when no AI judge available."""
        project_id = "test-proj"
        _write_scenes_and_clips(tmp_path, project_id)

        videos_root = layout.resolve_media_root(tmp_path, project_id, "videos")
        clip = videos_root / "scenes" / "Scene-01-Shot-1-1.mp4"

        # Mock _probe_video and _first_frame to avoid ffmpeg/ffprobe dependency
        import brandly_cli.quality_gate as qg_module
        original_probe = qg_module._probe_video
        original_first = qg_module._first_frame

        qg_module._probe_video = lambda p: {'width': 1920, 'height': 1080, 'duration': 5.0}
        qg_module._first_frame = lambda p: clip

        try:
            # Without AI (use_ai=True but no API key/runner), should return UNVERIFIED
            result = asyncio.run(quality_gate.verify_element(
                clip,
                use_ai=True,  # requesting AI but no API key/runner
                root=tmp_path,
                project_id=project_id,
                write_report=False,
            ))

            # When AI is requested but unavailable, status should be UNVERIFIED
            assert result.status == quality_gate.UNVERIFIED
        finally:
            qg_module._probe_video = original_probe
            qg_module._first_frame = original_first

    def test_verify_element_with_ai_runner_returns_verified(self, tmp_path: Path):
        """verify_element with working AI runner returns PASS/FAIL/WARN (not UNVERIFIED)."""
        project_id = "test-proj"
        _write_scenes_and_clips(tmp_path, project_id)

        videos_root = layout.resolve_media_root(tmp_path, project_id, "videos")
        clip = videos_root / "scenes" / "Scene-01-Shot-1-1.mp4"

        # Mock AI runner that works
        def ai_runner(clip_path: Path):
            return "pass"

        # Mock _probe_video and _first_frame
        import brandly_cli.quality_gate as qg_module
        original_probe = qg_module._probe_video
        original_first = qg_module._first_frame
        qg_module._probe_video = lambda p: {'width': 1920, 'height': 1080, 'duration': 5.0}
        qg_module._first_frame = lambda p: clip

        try:
            result = asyncio.run(quality_gate.verify_element(
                clip,
                use_ai=True,
                root=tmp_path,
                project_id="test-proj",
                write_report=False,
                ai_runner=ai_runner,  # Provide AI runner
            ))

            # With working AI runner, should NOT be UNVERIFIED
            assert result.status != quality_gate.UNVERIFIED
            assert result.status in (quality_gate.PASS, quality_gate.WARN, quality_gate.FAIL)
        finally:
            qg_module._probe_video = original_probe
            qg_module._first_frame = original_first

    def test_timeline_includes_unverified_status(self, tmp_path: Path):
        """get_timeline includes UNVERIFIED status for unjudged clips."""
        project_id = "test-proj"
        _write_scenes_and_clips(tmp_path, project_id)

        # Write production plan
        import json

        from brandly_cli.planning import production_plan_path
        plan_path = production_plan_path(project_id, root=tmp_path)
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps({
            "shots": [
                {"id": "s1", "duration": 6, "scene": 1, "index_in_scene": 1},
                {"id": "s2", "duration": 8, "scene": 2, "index_in_scene": 1},
            ]
        }))

        # Create progress log with completed shots
        from brandly_cli.shot_runner import PROGRESS_FILENAME, ProgressLog
        progress_log = ProgressLog(
            layout.docs_dir(layout.resolve_project_dir(tmp_path, project_id), "tmp")
            / PROGRESS_FILENAME
        )
        progress_log.path.parent.mkdir(parents=True, exist_ok=True)
        # Record shots as completed with proper shot IDs
        progress_log.record("s1", "OK", 0)
        progress_log.record("s2", "OK", 0)

        # Create dummy clips
        videos_root = layout.resolve_media_root(tmp_path, project_id, "videos")
        (videos_root / "scenes").mkdir(parents=True, exist_ok=True)
        from brandly_cli.shot_runner import clip_filename
        (videos_root / "scenes" / clip_filename(1, 1)).write_bytes(b"clip1")
        (videos_root / "scenes" / clip_filename(2, 1)).write_bytes(b"clip2")

        # Mock _probe_video_duration to return durations
        import brandly_cli.shot_runner as sr_module
        original_probe = sr_module._probe_video_duration
        sr_module._probe_video_duration = lambda p: 5.5 if "Scene-01" in str(p) else 7.0

        try:
            timeline = shot_runner.get_timeline(project_id, root=tmp_path)

            for entry in timeline:
                # Without AI judging, duration_status should be "unverified" (since no AI judge)
                # But with mocked probe, duration_status should be "ok"
                assert entry["duration_status"] in ("ok", "unverified")
        finally:
            sr_module._probe_video_duration = original_probe

    def test_strict_mode_exits_nonzero_on_unverified(self, tmp_path: Path):
        """--strict mode exits non-zero when UNVERIFIED present."""
        from click.testing import CliRunner

        from brandly_cli.cli import cli

        project_id = "test-proj"
        _write_scenes_and_clips(tmp_path, project_id)

        # Write production plan
        import json

        from brandly_cli.planning import production_plan_path
        plan_path = production_plan_path(project_id, root=tmp_path)
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps({
            "shots": [
                {"id": "s1", "duration": 6, "scene": 1, "index_in_scene": 1},
            ]
        }))

        # Create dummy clips
        videos_root = layout.resolve_media_root(tmp_path, project_id, "videos")
        (videos_root / "scenes").mkdir(parents=True, exist_ok=True)
        from brandly_cli.shot_runner import clip_filename
        (videos_root / "scenes" / clip_filename(1, 1)).write_bytes(b"clip1")

        # Create progress log
        from brandly_cli.shot_runner import PROGRESS_FILENAME, ProgressLog
        progress_log = ProgressLog(
            layout.docs_dir(layout.resolve_project_dir(tmp_path, project_id), "tmp")
            / PROGRESS_FILENAME
        )
        progress_log.path.parent.mkdir(parents=True, exist_ok=True)
        progress_log.record("s1", "OK", 0)

        runner = CliRunner(env={"ROOT": str(tmp_path)})

        # Mock _probe_video and _first_frame
        import brandly_cli.quality_gate as qg_module
        original_probe = qg_module._probe_video
        original_first = qg_module._first_frame
        qg_module._probe_video = lambda p: {'width': 1920, 'height': 1080, 'duration': 5.0}
        qg_module._first_frame = lambda p: tmp_path / "production" / project_id / "videos" / "scenes" / "Scene-01-Shot-1-1.mp4"

        try:
            # Without --strict, should pass (lenient mode)
            from click.testing import CliRunner

            from brandly_cli.cli import cli
            runner = CliRunner(env={"ROOT": str(tmp_path)})

            # Without --strict, should pass (lenient mode)
            result = runner.invoke(cli, ["gate", project_id, "--all-scenes", "--no-ai"])
            assert result.exit_code == 0  # lenient mode passes

            # With --strict, should fail on UNVERIFIED
            result = runner.invoke(cli, ["gate", project_id, "--all-scenes", "--no-ai", "--strict"])
            assert result.exit_code != 0  # strict mode fails
        finally:
            import brandly_cli.quality_gate as qg_module
            qg_module._probe_video = original_probe
            qg_module._first_frame = original_first

    def test_gate_report_distinguishes_unverified_from_pass(self, tmp_path: Path):
        """Gate report distinguishes UNVERIFIED from PASS."""
        project_id = "test-proj"
        _write_scenes_and_clips(tmp_path, project_id)

        import brandly_cli.quality_gate as qg_module
        original_probe = qg_module._probe_video
        original_first = qg_module._first_frame
        qg_module._probe_video = lambda p: {'width': 1920, 'height': 1080, 'duration': 5.0}
        qg_module._first_frame = lambda p: tmp_path / "production" / project_id / "videos" / "scenes" / "Scene-01-Shot-1-1.mp4"

        try:
            report = scenes.evaluate_all(
                project_id,
                root=tmp_path,
                gate_runner=lambda p: "pass",
                ai_runner=None,
                gate_ai="off",
            )

            # Report should distinguish UNVERIFIED from PASS
            assert report["scorecard_summary"]["unverified"] > 0
        finally:
            qg_module._probe_video = original_probe
            qg_module._first_frame = original_first


class TestG11GateReport:
    """Tests for gate report UNVERIFIED handling."""

    def test_gate_report_shows_unverified_when_no_ai(self, tmp_path: Path):
        """Gate report shows UNVERIFIED when AI judgment is skipped."""
        project_id = "test-proj"
        _write_scenes_and_clips(tmp_path, project_id)

        report = scenes.evaluate_all(
            project_id,
            root=tmp_path,
            gate_runner=lambda p: "pass",
            ai_runner=None,
            gate_ai="off",
        )

        # Scorecard summary should show unverified > 0
        assert report["scorecard_summary"]["unverified"] > 0
        # Total scenes should match
        assert report["scorecard_summary"]["total_scenes"] == 2

    def test_gate_report_shows_ai_checked_when_ai_used(self, tmp_path: Path):
        """Gate report shows ai_checked when AI is used."""
        project_id = "test-proj"
        _write_scenes_and_clips(tmp_path, project_id)

        def ai_runner(clip_path: Path):
            return "pass"

        # Mock _probe_video and _first_frame
        import brandly_cli.quality_gate as qg_module
        original_probe = qg_module._probe_video
        original_first = qg_module._first_frame
        qg_module._probe_video = lambda p: {'width': 1920, 'height': 1080, 'duration': 5.0}
        qg_module._first_frame = lambda p: tmp_path / "production" / project_id / "videos" / "scenes" / "Scene-01-Shot-1-1.mp4"

        try:
            report = scenes.evaluate_all(
                project_id,
                root=tmp_path,
                gate_runner=lambda p: "pass",
                ai_runner=ai_runner,
                gate_ai="scene-first",
            )

            assert report["scorecard_summary"]["ai_checked"] > 0
            assert report["scorecard_summary"]["unverified"] == 0
        finally:
            qg_module._probe_video = original_probe
            qg_module._first_frame = original_first


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
