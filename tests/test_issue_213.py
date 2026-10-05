r"""Issue #213: ``project.json.budget`` is a silent mirror of ``cost.json``.

The value that actually gates spend is ``cost.json.budget_credits``. Editing
``project.json.budget`` appears to work, is confirmed by ``brandly list``, and
is then silently reverted by the next spending command which re-syncs the
mirror from ``cost.json`` — no error, no warning. The display must read
``cost.json`` (the authoritative cap) and warn on divergence instead of
showing a briefly-wrong raised cap.

Run under ``.venv\\Scripts\\python`` (editable install points at ``src/``).
"""

from __future__ import annotations

import json
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


def _write_project(project_dir: Path, pid: str, budget: int = 200) -> None:
    proj_file = project_dir / pid / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    proj_file.write_text(
        json.dumps({"id": pid, "name": "T", "budget": budget, "spent": 10})
    )


def _write_cost(
    project_dir: Path, pid: str, budget: int = 200, spent: int = 10
) -> None:
    cost_file = project_dir / pid / "cost.json"
    cost_file.parent.mkdir(parents=True, exist_ok=True)
    cost_file.write_text(
        json.dumps({"budget_credits": budget, "credits_spent": spent})
    )


class TestBudgetAuthoritative:
    def test_list_shows_cost_json_cap_and_warns_on_divergence(
        self, runner: CliRunner, project_dir: Path
    ) -> None:
        # The user raised project.json.budget to 1600; cost.json still says
        # 200. The mirror (1600) looks applied and is then silently reverted —
        # the display must show the authoritative cap (200) and warn.
        pid = generate_project_id()
        _write_project(project_dir, pid, budget=1600)
        _write_cost(project_dir, pid, budget=200, spent=10)
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0, result.output
        assert (
            "⚠" in result.output
        ), "the project.json.budget vs cost.json divergence must be warned"
        assert (
            "200" in result.output
        ), "the authoritative cost.json cap must be what the display shows"

    def test_status_shows_cost_json_cap_and_warns_on_divergence(
        self, runner: CliRunner, project_dir: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid, budget=1600)
        _write_cost(project_dir, pid, budget=200, spent=10)
        result = runner.invoke(cli, ["status", pid])
        assert result.exit_code == 0, result.output
        assert (
            "⚠" in result.output
        ), "the divergence must be warned in the project summary"
        assert (
            "200 credits" in result.output
        ), "the Budget row must show the authoritative cost.json cap"

    def test_no_warning_when_caps_agree(
        self, runner: CliRunner, project_dir: Path
    ) -> None:
        # Guard: no warning when the mirror and the cap agree.
        pid = generate_project_id()
        _write_project(project_dir, pid, budget=200)
        _write_cost(project_dir, pid, budget=200, spent=10)
        result = runner.invoke(cli, ["status", pid])
        assert result.exit_code == 0, result.output
        assert "⚠" not in result.output
