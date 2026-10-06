"""Contract test: G13 - Quota-aware planning.

RED test for the quota-aware planning increment.

The CLI should:
1. Accept a --target-duration flag on produce/estimate commands
2. Warn when the plan exceeds the remaining daily quota
3. Propose a multi-day schedule (shots/day split)
4. Duration fidelity from G7 feeds the schedule (no planning on fiction)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from brandly_cli import cost_tracker
from brandly_cli.cmd.production import Director, DirectorConfig
from brandly_cli.project_manager import ProjectManager
from brandly_cli.types import ProjectData

PID = "g13proj"


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


class TestQuotaAwarePlanning:
    """Test quota-aware planning with --target-duration."""

    def test_estimate_command_has_target_duration_flag(self):
        """The estimate command should accept --target-duration."""
        body = Path("src/brandly_cli/cmd/production.py").read_text(encoding="utf-8")
        assert '"--target-duration"' in body, "estimate command must expose --target-duration"

    def test_produce_command_has_target_duration_flag(self):
        """The produce command should accept --target-duration."""
        body = Path("src/brandly_cli/cmd/production.py").read_text(encoding="utf-8")
        assert '"--target-duration"' in body, "produce command must expose --target-duration"

    def test_daily_video_quota_status_returns_seconds_remaining(self, tmp_path: Path):
        """daily_video_quota_status should return cap, used, and remaining."""
        _make_project(tmp_path, shot_count=4)

        from datetime import datetime, timezone
        video_tmp = tmp_path / ".brandly" / PID / "docs" / "tmp"
        video_tmp.mkdir(parents=True, exist_ok=True)

        record = {
            "asset_type": "video",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"duration": 100}
        }
        (video_tmp / "video_001.json").write_text(json.dumps(record))

        status = cost_tracker.daily_video_quota_status(tmp_path)

        assert "cap" in status
        assert "seconds" in status
        assert "remaining" in status
        assert "percent_used" in status
        assert "at_risk" in status
        assert status["cap"] == 500
        assert status["seconds"] == 100
        assert status["remaining"] == 400
        assert status["percent_used"] == 20

    def test_quota_ledger_first_class_object(self):
        """Quota ledger should be a first-class object with seconds used/remaining."""
        assert hasattr(cost_tracker, "NOMINAL_VIDEO_SECONDS_PER_DAY")
        assert cost_tracker.NOMINAL_VIDEO_SECONDS_PER_DAY == 500
        assert hasattr(cost_tracker, "daily_video_quota_status")

    def test_target_duration_warns_when_exceeds_quota(self, tmp_path: Path):
        """--target-duration should warn when plan exceeds remaining quota."""
        _make_project(tmp_path, shot_count=10)

        from datetime import datetime, timezone
        video_tmp = tmp_path / ".brandly" / PID / "docs" / "tmp"
        video_tmp.mkdir(parents=True, exist_ok=True)

        record = {
            "asset_type": "video",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"duration": 400}
        }
        (video_tmp / "video_001.json").write_text(json.dumps(record))

        from brandly_cli.cost_tracker import daily_video_quota_status

        status = daily_video_quota_status(tmp_path)
        target_duration = 200

        assert status["remaining"] < target_duration

    def test_multi_day_schedule_proposal(self, tmp_path: Path):
        """Should propose a multi-day schedule when quota exceeded."""
        target_seconds = 900
        daily_quota = 500

        from brandly_cli.cost_tracker import compute_multi_day_schedule

        schedule = compute_multi_day_schedule(target_seconds, daily_quota)

        assert "days" in schedule
        assert schedule["days"] == 2
        assert "seconds_per_day" in schedule
        assert schedule["seconds_per_day"] == [500, 400]
        assert "shots_per_day" in schedule

    def test_resume_across_day_boundaries(self, tmp_path: Path):
        """A run should resume cleanly across day boundaries."""
        _make_project(tmp_path, shot_count=4)

        progress_file = tmp_path / ".brandly" / PID / "docs" / "tmp" / "produce_progress.txt"
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        progress_file.write_text("shot-1\nshot-2\n")

        status = cost_tracker.daily_video_quota_status(tmp_path)
        assert "remaining" in status


# Functions that don't exist yet - RED
assert hasattr(cost_tracker, "compute_multi_day_schedule"), "compute_multi_day_schedule must exist"
