"""Issue #118: local video-quota accounting.

During a 6-hour 503/429 outage there was no way to tell quota exhaustion
from service degradation. The per-video generation records already exist
(docs/tmp/video_*.json with generated_at + metadata.duration); summing the
video-seconds generated per UTC day gives the actionable number:
"video-seconds today: X/500".
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from click.testing import CliRunner

from brandly_cli.cli import cli
from brandly_cli.cost_tracker import video_seconds_today


def _record(path: Path, seconds: int, when: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "asset_type": "video",
                "model": "agnes-video-2.5-flash",
                "generated_at": when.isoformat(),
                "metadata": {"duration": seconds, "video_id": "task_x"},
            }
        ),
        encoding="utf-8",
    )


def test_video_seconds_today_sums_utc_day(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    docs = tmp_path / ".brandly" / "proj-a" / "docs" / "tmp"
    _record(docs / "video_1.json", 6, now)
    _record(docs / "video_2.json", 5, now - timedelta(minutes=30))
    _record(docs / "video_3.json", 7, now - timedelta(days=1))  # yesterday
    result = video_seconds_today(tmp_path)
    assert result["seconds"] == 11
    assert result["records"] == 2


def test_video_seconds_today_empty_root(tmp_path: Path) -> None:
    result = video_seconds_today(tmp_path)
    assert result["seconds"] == 0
    assert result["records"] == 0


def test_video_seconds_today_skips_non_video_and_malformed(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    docs = tmp_path / ".brandly" / "proj-a" / "docs" / "tmp"
    _record(docs / "video_1.json", 6, now)
    img = docs / "video_2.json"
    img.parent.mkdir(parents=True, exist_ok=True)
    img.write_text(json.dumps({"asset_type": "image", "generated_at": now.isoformat()}), encoding="utf-8")
    bad = docs / "video_3.json"
    bad.write_text("{not json", encoding="utf-8")
    missing_meta = docs / "video_4.json"
    missing_meta.write_text(
        json.dumps({"asset_type": "video", "generated_at": now.isoformat()}), encoding="utf-8"
    )
    result = video_seconds_today(tmp_path)
    assert result["seconds"] == 6
    assert result["records"] == 1


def test_cost_command_shows_video_quota(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    docs = tmp_path / ".brandly" / "quota-proj" / "docs" / "tmp"
    _record(docs / "video_1.json", 12, now)
    # a cost.json so ct.get_summary finds the project
    cost_dir = tmp_path / ".brandly" / "quota-proj"
    cost_dir.mkdir(parents=True, exist_ok=True)
    (cost_dir / "cost.json").write_text(
        json.dumps(
            {"id": "quota-proj", "budget_credits": 500, "credits_spent": 0, "cost_log": []}
        ),
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["cost", "quota-proj"], env={"ROOT": str(tmp_path)})
    assert result.exit_code == 0, result.output
    assert "video-seconds today" in result.output
    assert "12" in result.output
    assert "500" in result.output
