"""Goal 2 PR D: ``brandly director`` prints the orchestrator plan.

``director_plan`` (``cmd/production.py``) is the single data source for the
orchestrator plan — pipeline phases, per-phase status, current step, and the
exact next command (``brandly run <id> --execute --yes``).  The
``brandly director`` command renders the prompt panel plus this plan; the
plan itself is data-only so agents can consume it without parsing rich
output.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from brandly_cli.cli import cli
from brandly_cli.cmd.production import director_plan
from brandly_cli.constants import PHASE_ORDER
from brandly_cli.project_manager import ProjectManager
from brandly_cli.types import ProjectData

PID = "plan-proj"

EXPECTED_PHASES = [
    "init",
    "trends",
    "concept",
    "script",
    "asset",
    "audio",
    "re_edit",
    "validate",
    "publish",
    "done",
]
REAL_PHASES = EXPECTED_PHASES[1:-1]


@pytest.fixture
def runner(tmp_path: Path) -> CliRunner:
    """Click test runner pointed at a temp directory (ROOT env, like test_cli)."""
    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _make_project(root: Path, pid: str = PID) -> ProjectManager:
    pm = ProjectManager(root)
    asyncio.run(pm.create(ProjectData(id=pid, name="Plan Project")))
    return pm


def _seed(
    pm: ProjectManager,
    pid: str,
    *,
    completed: list[str] | None = None,
    failed: list[str] | None = None,
    current_phase: str = "init",
) -> None:
    """Seed ``project.phases`` + ``current_phase`` the way ``run`` does."""
    phases: dict[str, Any] = {}
    for name in completed or []:
        phases[name] = {"status": "completed", "completed_at": "2026-01-01T00:00:00Z"}
    for name in failed or []:
        phases[name] = {"status": "failed", "error": "test failure"}
    asyncio.run(pm.update(pid, {"phases": phases, "current_phase": current_phase}))


class TestDirectorPlan:
    """``director_plan`` is the data-only source for the orchestrator plan."""

    def test_no_project_reports_generic_plan(self, tmp_path: Path) -> None:
        plan = director_plan(tmp_path, None)

        assert plan["project_id"] is None
        assert plan["phases"] == EXPECTED_PHASES
        assert plan["phases_status"] == dict.fromkeys(EXPECTED_PHASES, "pending")
        assert plan["completed"] == []
        assert plan["current"] is None
        assert plan["next_command"] == "brandly init"

    def test_unknown_project_falls_back_to_init(self, tmp_path: Path) -> None:
        _make_project(tmp_path)

        plan = director_plan(tmp_path, "missing-project")

        assert plan["current"] is None
        assert plan["next_command"] == "brandly init"

    def test_fresh_project_points_at_first_real_phase(self, tmp_path: Path) -> None:
        _make_project(tmp_path)  # current_phase defaults to "init"

        plan = director_plan(tmp_path, PID)

        # "init" is a bookkeeping marker; the first real step is "trends".
        assert plan["current"] == "trends"
        assert plan["next_command"] == f"brandly run {PID} --execute --yes"

    def test_partial_progress_reports_the_resume_point(self, tmp_path: Path) -> None:
        pm = _make_project(tmp_path)
        _seed(pm, PID, completed=REAL_PHASES[:2], current_phase="script")

        plan = director_plan(tmp_path, PID)

        assert plan["completed"] == REAL_PHASES[:2]
        assert plan["phases_status"]["script"] == "pending"
        assert plan["current"] == "script"
        assert plan["next_command"] == f"brandly run {PID} --execute --yes"

    def test_failed_phase_is_the_resume_point(self, tmp_path: Path) -> None:
        pm = _make_project(tmp_path)
        _seed(
            pm,
            PID,
            completed=REAL_PHASES[:3],
            failed=["asset"],
            current_phase="asset",
        )

        plan = director_plan(tmp_path, PID)

        assert plan["completed"] == REAL_PHASES[:3]
        assert plan["phases_status"]["asset"] == "failed"
        assert plan["current"] == "asset"  # a re-run retries the failed phase
        assert plan["next_command"] == f"brandly run {PID} --execute --yes"

    def test_all_phases_complete_ends_the_plan(self, tmp_path: Path) -> None:
        pm = _make_project(tmp_path)
        _seed(pm, PID, completed=list(REAL_PHASES), current_phase="done")

        plan = director_plan(tmp_path, PID)

        assert plan["completed"] == REAL_PHASES
        assert plan["current"] is None
        assert plan["next_command"] is None

    def test_plan_phases_track_the_pipeline_constant(self, tmp_path: Path) -> None:
        plan = director_plan(tmp_path, None)

        assert plan["phases"] == PHASE_ORDER


class TestDirectorCommand:
    """``brandly director`` prints the prompt panel + the orchestrator plan."""

    def test_director_prints_prompt_and_plan(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["director"])

        assert result.exit_code == 0, result.output
        assert "Director Mode" in result.output
        assert "Orchestrator plan" in result.output
        for phase in EXPECTED_PHASES:
            assert phase in result.output
        assert "brandly init" in result.output

    def test_director_project_plan_shows_resume_point(self, runner: CliRunner, tmp_path: Path) -> None:
        pm = _make_project(tmp_path)
        _seed(pm, PID, completed=REAL_PHASES[:2], current_phase="script")

        result = runner.invoke(cli, ["director", PID])

        assert result.exit_code == 0, result.output
        assert "Orchestrator plan" in result.output
        assert "script" in result.output  # current step
        assert f"brandly run {PID} --execute --yes" in result.output  # next command

    def test_director_unknown_project_notes_init(self, runner: CliRunner, tmp_path: Path) -> None:
        _make_project(tmp_path)

        result = runner.invoke(cli, ["director", "missing-project"])

        assert result.exit_code == 0, result.output
        assert "brandly init" in result.output
