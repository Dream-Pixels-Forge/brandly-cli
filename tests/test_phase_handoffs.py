"""Goal 7 PR E: per-phase handoff contracts for orchestrator/subagent dispatch.

``phase_handoffs`` (``cmd/production.py``) is the data-only dispatch source for
orchestrating agents: per phase it reports ``{id, status, inputs[], outputs[],
gate, next_command, est_cost}`` — everything derived from on-disk state
(``project.phases``, ``scenes.json``, ``shots.json``) plus the project's
style/shot_count. No new state, no writes.

``brandly plan <id> [--json]`` renders the table; ``--json`` emits one
machine-readable document (rich console suppressed, per the #73 convention).
The tool is registered in the ``agent_surface`` manifest as read-only.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from brandly_cli.cli import cli
from brandly_cli.cmd.production import director_plan, phase_handoffs
from brandly_cli.constants import PHASE_ORDER
from brandly_cli.project_manager import ProjectManager
from brandly_cli.types import ProjectData

PID = "handoffs-proj"

REAL_PHASES = [p for p in PHASE_ORDER if p not in ("init", "done")]


@pytest.fixture
def runner(tmp_path: Path) -> CliRunner:
    """Click test runner pointed at a temp directory (ROOT env, like test_cli)."""
    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _make_project(root: Path, pid: str = PID, **kwargs: Any) -> ProjectManager:
    pm = ProjectManager(root)
    asyncio.run(pm.create(ProjectData(id=pid, name="Handoffs Project", **kwargs)))
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


class TestPhaseHandoffs:
    """``phase_handoffs`` reports the per-phase dispatch contract."""

    def test_unknown_project_reports_generic_handoffs(self, tmp_path: Path) -> None:
        handoffs = phase_handoffs(tmp_path, "missing-project")

        assert handoffs["project_id"] == "missing-project"
        assert handoffs["next_command"] == "brandly init"
        assert [h["id"] for h in handoffs["handoffs"]] == PHASE_ORDER

    def test_each_handoff_carries_the_contract_fields(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        handoffs = phase_handoffs(tmp_path, PID)

        required = {"id", "status", "inputs", "outputs", "gate", "next_command", "est_cost", "error"}
        for h in handoffs["handoffs"]:
            assert set(h) == required, h["id"]
            assert isinstance(h["inputs"], list) and h["inputs"], h["id"]
            assert isinstance(h["outputs"], list) and h["outputs"], h["id"]
            assert isinstance(h["gate"], dict) and h["gate"]["command"], h["id"]
            assert isinstance(h["next_command"], str) and h["next_command"], h["id"]
            assert isinstance(h["est_cost"], int) and h["est_cost"] >= 0, h["id"]
            assert h["error"] is None or isinstance(h["error"], str), h["id"]

    def test_fresh_project_marks_first_real_phase_current(self, tmp_path: Path) -> None:
        _make_project(tmp_path)  # current_phase defaults to "init"

        handoffs = phase_handoffs(tmp_path, PID)

        statuses = {h["id"]: h["status"] for h in handoffs["handoffs"]}
        assert statuses["trends"] == "pending"
        assert handoffs["current"] == "trends"
        assert handoffs["next_command"] == f"brandly run {PID} --execute --yes"

    def test_statuses_track_project_phases(self, tmp_path: Path) -> None:
        pm = _make_project(tmp_path)
        _seed(pm, PID, completed=REAL_PHASES[:2], current_phase="script")

        handoffs = phase_handoffs(tmp_path, PID)

        statuses = {h["id"]: h["status"] for h in handoffs["handoffs"]}
        assert statuses["trends"] == "completed"
        assert statuses["concept"] == "completed"
        assert statuses["script"] == "pending"
        assert handoffs["current"] == "script"

    def test_failed_phase_carries_its_error_for_redispatch(self, tmp_path: Path) -> None:
        pm = _make_project(tmp_path)
        _seed(pm, PID, completed=REAL_PHASES[:3], failed=["asset"], current_phase="asset")

        handoffs = phase_handoffs(tmp_path, PID)
        asset = next(h for h in handoffs["handoffs"] if h["id"] == "asset")

        assert asset["status"] == "failed"
        assert asset["error"] == "test failure"
        assert handoffs["current"] == "asset"

    def test_done_project_has_no_next_command(self, tmp_path: Path) -> None:
        pm = _make_project(tmp_path)
        _seed(pm, PID, completed=list(REAL_PHASES), current_phase="done")

        handoffs = phase_handoffs(tmp_path, PID)

        assert handoffs["current"] is None
        assert handoffs["next_command"] is None

    def test_asset_handoff_names_the_scene_gate(self, tmp_path: Path) -> None:
        _make_project(tmp_path)

        handoffs = phase_handoffs(tmp_path, PID)
        asset = next(h for h in handoffs["handoffs"] if h["id"] == "asset")

        assert "scenes.json" in " ".join(asset["inputs"] + asset["outputs"])
        assert "gate" in asset["gate"]["command"]
        assert "all-scenes" in asset["gate"]["command"]

    def test_handoffs_agree_with_director_plan(self, tmp_path: Path) -> None:
        pm = _make_project(tmp_path)
        _seed(pm, PID, completed=REAL_PHASES[:4], current_phase="audio")

        handoffs = phase_handoffs(tmp_path, PID)
        plan = director_plan(tmp_path, PID)

        assert handoffs["current"] == plan["current"]
        assert handoffs["next_command"] == plan["next_command"]
        assert {h["id"]: h["status"] for h in handoffs["handoffs"]} == plan["phases_status"]

    def test_costs_derive_from_project_style_and_shots(self, tmp_path: Path) -> None:
        _make_project(tmp_path, pid="cheap", style="ugc", shot_count=3)
        _make_project(tmp_path, pid="pricey", style="explainer_video", shot_count=10)

        cheap = {h["id"]: h["est_cost"] for h in phase_handoffs(tmp_path, "cheap")["handoffs"]}
        pricey = {h["id"]: h["est_cost"] for h in phase_handoffs(tmp_path, "pricey")["handoffs"]}

        assert cheap["init"] == 0
        assert cheap["asset"] < pricey["asset"]
        assert cheap["concept"] < pricey["concept"]

    def test_handoffs_are_json_serializable(self, tmp_path: Path) -> None:
        _make_project(tmp_path)

        assert json.dumps(phase_handoffs(tmp_path, PID))


class TestPlanCommand:
    """``brandly plan`` renders the handoff table (human + --json)."""

    def test_plan_prints_the_handoff_table(self, runner: CliRunner, tmp_path: Path) -> None:
        _make_project(tmp_path)

        result = runner.invoke(cli, ["plan", PID])

        assert result.exit_code == 0, result.output
        for phase in REAL_PHASES:
            assert phase in result.output
        assert f"brandly run {PID} --execute --yes" in result.output

    def test_plan_json_is_machine_readable(self, runner: CliRunner, tmp_path: Path) -> None:
        _make_project(tmp_path)

        result = runner.invoke(cli, ["plan", PID, "--json"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["project_id"] == PID
        assert [h["id"] for h in payload["handoffs"]] == PHASE_ORDER

    def test_plan_rejects_bad_project_id(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["plan", "bad id!!"])

        assert result.exit_code == 1
        assert "Invalid project ID" in result.output


