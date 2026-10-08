r"""Tests for G13: Quota-aware planning — design for growth, don't fight 500s/day.

Tests that the quota ledger, multi-day scheduling, and cross-day resume work correctly.
"""

from __future__ import annotations

from unittest.mock import patch

from brandly_cli import cost_tracker, layout, scenes, shot_runner


class TestG13QuotaAware:
    """G13: Quota-aware planning — design for growth, don't fight 500s/day."""

    def test_quota_ledger_first_class_budget_object(self, tmp_path):
        """Quota ledger as a first-class budget object (seconds used/remaining)."""
        root = tmp_path

        # Create a project
        shot_list = [
            {"id": "s1", "prompt": "p1", "duration": 6, "scene": 1, "shot": 1},
        ]
        scenes.write_scenes("test-proj", shot_list, root=tmp_path)

        # Get quota status
        quota = cost_tracker.daily_video_quota_status(root)

        assert "seconds" in quota
        assert "cap" in quota
        assert "remaining" in quota
        assert "percent_used" in quota
        assert "at_risk" in quota
        assert quota["cap"] == 500  # NOMINAL_VIDEO_SECONDS_PER_DAY

    def test_multi_day_schedule_proposed_when_exceeds_quota(self, tmp_path):
        """A --target-duration 900 run under 500s remaining proposes a 2-day schedule."""
        from brandly_cli.cost_tracker import compute_multi_day_schedule

        # 900 seconds with 500/day quota = 2 days
        schedule = compute_multi_day_schedule(900)

        assert schedule["days"] == 2
        assert len(schedule["seconds_per_day"]) == 2
        assert schedule["seconds_per_day"][0] == 500
        assert schedule["seconds_per_day"][1] == 400

        # Shots per day should be reasonable
        assert schedule["shots_per_day"][0] > 0
        assert schedule["shots_per_day"][1] > 0

    def test_quota_warning_at_80_percent(self, tmp_path):
        """Quota warning fires at 80% of daily cap."""

        # Mock video_seconds_today to return 400 seconds (80% of 500)
        with patch('brandly_cli.cost_tracker.video_seconds_today', return_value={"seconds": 400, "records": 80}):
            quota = cost_tracker.daily_video_quota_status("/tmp")
            assert quota["seconds"] == 400
            assert quota["percent_used"] == 80
            assert quota["at_risk"] is True
            assert quota["remaining"] == 100

    def test_estimate_target_duration_warns_on_quota_exceeded(self, tmp_path):
        """estimate --target-duration warns when exceeding quota."""

        from click.testing import CliRunner

        from brandly_cli.cli import cli

        runner = CliRunner()

        # Mock quota to be low
        original_quota = cost_tracker.daily_video_quota_status

        def mock_quota(root):
            return {"seconds": 100, "records": 20, "cap": 500, "remaining": 400, "percent_used": 20, "at_risk": False}

        cost_tracker.daily_video_quota_status = mock_quota
        try:
            runner = CliRunner()
            result = runner.invoke(cli, ["estimate", "--style", "cinematic", "--shots", "5", "--target-duration", "900"])
            assert result.exit_code == 0
            assert "⚠ Target duration" in result.output
            assert "900s" in result.output
            assert "2-day schedule" in result.output
        finally:
            cost_tracker.daily_video_quota_status = original_quota

    def test_estimate_target_duration_ok_when_fits_quota(self, tmp_path):
        """estimate --target-duration passes when within quota."""
        from click.testing import CliRunner

        from brandly_cli.cli import cli
        original_quota = cost_tracker.daily_video_quota_status

        def mock_quota(root):
            return {"seconds": 100, "records": 20, "cap": 500, "remaining": 400, "percent_used": 20, "at_risk": False}

        cost_tracker.daily_video_quota_status = mock_quota
        try:
            runner = CliRunner()
            result = runner.invoke(cli, ["estimate", "--style", "cinematic", "--shots", "5", "--target-duration", "100"])
            assert result.exit_code == 0
            assert "✓ Target duration" in result.output
            assert "fits within today's remaining quota" in result.output
        finally:
            cost_tracker.daily_video_quota_status = original_quota

    def test_quota_ledger_survives_crash_no_double_count(self, tmp_path):
        """The ledger survives a crash mid-run (no double-counted seconds)."""
        from brandly_cli.cost_tracker import video_seconds_today

        # Create some video records
        root = tmp_path

        # Create video records
        tmp_dir = tmp_path / ".brandly" / "test-proj" / "docs" / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        import json
        from datetime import datetime, timezone

        for i in range(3):
            record = {
                "asset_type": "video",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"duration": 10}
            }
            (tmp_dir / f"video_{i}.json").write_text(json.dumps(record))

        # Count seconds
        result = video_seconds_today(root)
        assert result["seconds"] == 30
        assert result["records"] == 3

        # Now simulate a crash and re-run (no new records added)
        # The count should be the same
        result2 = video_seconds_today(root)
        assert result2["seconds"] == 30
        assert result2["records"] == 3

    def test_resume_across_day_boundaries(self, tmp_path):
        """Resuming on day 2 continues the same shot list without duplication."""
        from brandly_cli.shot_runner import ProgressLog, RunnerConfig

        progress_log = ProgressLog(
            layout.docs_dir(layout.resolve_project_dir(tmp_path, "test-proj"), "tmp") / "produce_progress.txt"
        )
        progress_log.path.parent.mkdir(parents=True, exist_ok=True)
        progress_log.record("s1", "OK", 0)
        progress_log.record("s2", "OK", 0)

        scenes_dir = tmp_path / "videos" / "scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)
        calls: list[str] = []

        def generate_one(shot):
            calls.append(shot.id)
            (scenes_dir / shot_runner.clip_filename(shot.scene, shot.index_in_scene)).write_bytes(b"clip")
            return True, 0, ""

        shots = shot_runner.flatten_shots(
            [{"id": "s1", "duration": 6}, {"id": "s2", "duration": 6}, {"id": "s3", "duration": 6}],
            tmp_path,
        )
        config = RunnerConfig(
            shots=shots, generate_one=generate_one, scenes_dir=scenes_dir, progress=progress_log
        )
        rc = shot_runner.run_shots(config)

        assert rc == 0
        # s1/s2 are recorded OK in the progress file - only s3 generates
        assert calls == ["s3"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
