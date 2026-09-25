"""Goal 7 PR F: subagent dispatch contracts (prompt layer).

* The Director system prompt (``director.py``) gains a static "Subagent
  Dispatch" section: the 5-item worker contract schema, the
  parallel-cognition / serialized-execution rules, and the gate-screening
  loop — pointing at ``brandly plan --json`` as the authoritative per-phase
  contract (the prompt module stays import-free by design; the table itself
  is rendered from ``PHASE_HANDOFF_SPECS`` by the ``director`` command).
* ``brandly director`` prints a compact dispatch table (Phase | Contract |
  Verify) after the orchestrator plan.
* ``brandly init``'s ``AGENTS.md`` gains a short subagent note pointing at
  ``brandly plan --json`` as the dispatch source of truth.

String assertions only — pure prompt content, no behaviour risk.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli.cli import cli
from brandly_cli.cmd.production import PHASE_HANDOFF_SPECS
from brandly_cli.constants import PHASE_ORDER
from brandly_cli.director import get_director_prompt
from brandly_cli.project_manager import ProjectManager
from brandly_cli.types import ProjectData

PID = "dispatch-proj"

REAL_PHASES = [p for p in PHASE_ORDER if p not in ("init", "done")]


@pytest.fixture
def runner(tmp_path: Path) -> CliRunner:
    """Click test runner pointed at a temp directory (ROOT env, like test_cli)."""
    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _make_project(root: Path) -> ProjectManager:
    pm = ProjectManager(root)
    asyncio.run(pm.create(ProjectData(id=PID, name="Dispatch Project")))
    return pm


class TestDirectorPromptDispatchSection:
    """The system prompt teaches orchestrator-worker dispatch."""

    def test_prompt_has_a_subagent_dispatch_section(self) -> None:
        prompt = get_director_prompt()

        assert "Subagent Dispatch" in prompt

    def test_prompt_names_the_five_item_worker_contract(self) -> None:
        prompt = get_director_prompt().lower()

        for item in ("scope", "inputs", "outputs", "boundaries", "verification"):
            assert item in prompt, f"contract item missing: {item}"

    def test_prompt_points_at_plan_json_as_the_contract_source(self) -> None:
        prompt = get_director_prompt()

        assert "brandly plan" in prompt
        assert "--json" in prompt

    def test_prompt_separates_parallel_cognition_from_serial_execution(self) -> None:
        prompt = get_director_prompt().lower()

        assert "parallel" in prompt
        assert "serial" in prompt or "single" in prompt
        assert "gate" in prompt


class TestDirectorCommandDispatchTable:
    """``brandly director`` renders the per-phase dispatch contracts."""

    def test_director_prints_the_dispatch_table(self, runner: CliRunner, tmp_path: Path) -> None:
        _make_project(tmp_path)

        result = runner.invoke(cli, ["director", PID])

        assert result.exit_code == 0, result.output
        assert "dispatch" in result.output.lower()
        for phase in REAL_PHASES:
            assert phase in result.output
        assert "gate" in result.output.lower()

    def test_dispatch_table_rows_match_the_handoff_specs(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _make_project(tmp_path)

        result = runner.invoke(cli, ["director", PID])

        assert result.exit_code == 0, result.output
        for phase, spec in PHASE_HANDOFF_SPECS.items():
            if phase == "done":
                continue
            gate_cmd = spec["gate"]["command"].split("<")[0].strip()
            gate_line = gate_cmd.replace("<project_id>", PID).replace("<id>", PID)
            assert gate_line.split()[0] in result.output, phase
            assert gate_cmd.split(" ", 1)[0] in result.output, phase

    def test_director_without_project_still_prints_dispatch(
        self, runner: CliRunner
    ) -> None:
        result = runner.invoke(cli, ["director"])

        assert result.exit_code == 0, result.output
        assert "dispatch" in result.output.lower()


class TestAgentsMdSubagentNote:
    """``AGENTS.md`` points subagents at the plan contract."""

    def test_agents_md_mentions_subagent_dispatch(self, tmp_path: Path) -> None:
        result = CliRunner().invoke(
            cli, ["--root", str(tmp_path), "init", "--name", "Acme", "--idea", "a widget"]
        )

        assert result.exit_code == 0, result.output
        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "subagent" in content.lower()
        assert "brandly plan" in content
