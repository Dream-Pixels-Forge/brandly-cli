r"""Issues #214 + #192: no preflight cost estimate, and no rate-limit warning.

#214: ``init --budget`` defaults to 500 credits with no preflight check
against the estimated production cost, so a multi-shot project passes every
validation gate and then fails at the credit gate mid-run, after assets are
already paid for. ``produce --dry-run`` reports shots and duration but does
not price them.

#192 item 4: nothing reported actual daily quota usage - during provider
503/429 waves there was no way to tell quota exhaustion (the Agnes free tier
allows ~500 video-seconds/day) from service degradation.

Run under ``.venv\\Scripts\\python`` (editable install points at ``src/``).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli.cli import cli
from brandly_cli.utils import generate_project_id


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    return tmp_path / ".brandly"


@pytest.fixture
def runner(project_dir: Path, tmp_path: Path) -> CliRunner:
    import os

    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _write_project(project_dir: Path, pid: str, budget: int = 500) -> None:
    proj_file = project_dir / pid / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    proj_file.write_text(
        json.dumps({"id": pid, "name": "T", "budget": budget, "spent": 0})
    )


def _write_cost(project_dir: Path, pid: str, budget: int, spent: int) -> None:
    cost_file = project_dir / pid / "cost.json"
    cost_file.parent.mkdir(parents=True, exist_ok=True)
    cost_file.write_text(
        json.dumps(
            {
                "id": pid,
                "budget_credits": budget,
                "credits_spent": spent,
                "cost_log": [],
            }
        )
    )


def _ensure_plan(tmp_path: Path, pid: str) -> None:
    plan_dir = tmp_path / ".brandly" / pid / "docs" / "plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "production_plan.md").write_text(
        "| Plan | Asset | Shot ID | Model | Source | Status | Created | Updated |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )


def _shots_file(tmp_path: Path, count: int) -> Path:
    shots = [
        {"id": f"shot{i:02d}", "prompt": "a walk", "duration": 5}
        for i in range(1, count + 1)
    ]
    p = tmp_path / "shots.json"
    p.write_text(json.dumps(shots))
    return p


def _video_records(project_dir: Path, pid: str, total_seconds: int) -> None:
    """Write today's video generation records (the daily-quota read source)."""
    records_dir = project_dir / pid / "docs" / "tmp"
    records_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    per = 5
    written = 0
    for i in range(total_seconds // per):
        (records_dir / f"video_{i:03d}.json").write_text(
            json.dumps(
                {
                    "asset_type": "video",
                    "generated_at": stamp,
                    "metadata": {"duration": per},
                }
            )
        )
        written += per
    assert written == total_seconds - (total_seconds % per)


class TestPreflightCostAndQuota:
    def test_dry_run_prices_the_shots(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        # #214: the dry-run reported shots and duration but not their price.
        pid = generate_project_id()
        _write_project(project_dir, pid, budget=500)
        _write_cost(project_dir, pid, budget=500, spent=0)
        _ensure_plan(tmp_path, pid)
        shots = _shots_file(tmp_path, 3)
        result = runner.invoke(
            cli,
            ["produce", pid, "--shots", str(shots), "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        # Rich wraps console output; collapse whitespace before asserting.
        flat = " ".join(result.output.split())
        assert (
            "estimated 60 credits" in flat
        ), "the dry-run must price the shot list (3 x 20 credits)"
        assert "no API calls, no files written" in flat

    def test_dry_run_warns_when_projection_exceeds_remaining_budget(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid, budget=500)
        _write_cost(project_dir, pid, budget=500, spent=0)
        _ensure_plan(tmp_path, pid)
        shots = _shots_file(tmp_path, 30)
        result = runner.invoke(
            cli,
            ["produce", pid, "--shots", str(shots), "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        flat = " ".join(result.output.split())
        assert (
            "Projected video cost" in flat
        ), "a projection that cannot fit the budget must warn BEFORE spending"
        assert "600" in flat
        assert "Run 25 shots" in flat, "the warning must say what fits"

    def test_no_projection_warning_when_it_fits(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        # Guard: a shot list that fits the budget warns about nothing.
        pid = generate_project_id()
        _write_project(project_dir, pid, budget=500)
        _write_cost(project_dir, pid, budget=500, spent=0)
        _ensure_plan(tmp_path, pid)
        shots = _shots_file(tmp_path, 3)
        result = runner.invoke(
            cli,
            ["produce", pid, "--shots", str(shots), "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        assert "Projected video cost" not in result.output

    def test_quota_warning_when_daily_cap_nearly_reached(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        # #192 item 4: 420/500 video-seconds today (84%) must warn.
        pid = generate_project_id()
        _write_project(project_dir, pid, budget=500)
        _write_cost(project_dir, pid, budget=500, spent=0)
        _ensure_plan(tmp_path, pid)
        _video_records(project_dir, pid, 420)
        shots = _shots_file(tmp_path, 2)
        result = runner.invoke(
            cli,
            ["produce", pid, "--shots", str(shots), "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        assert (
            "Daily video quota" in result.output
        ), "approaching the daily cap must warn so quota exhaustion is distinguishable"
        assert "420/500" in result.output

    def test_no_quota_warning_below_threshold(
        self, runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        # Guard: a quiet day warns about nothing.
        pid = generate_project_id()
        _write_project(project_dir, pid, budget=500)
        _write_cost(project_dir, pid, budget=500, spent=0)
        _ensure_plan(tmp_path, pid)
        shots = _shots_file(tmp_path, 2)
        result = runner.invoke(
            cli,
            ["produce", pid, "--shots", str(shots), "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        assert "Daily video quota" not in result.output
