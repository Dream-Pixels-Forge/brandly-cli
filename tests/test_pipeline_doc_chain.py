"""P3 (#258 #247 #259 #257): the trends.md -> concept.md -> shots.json chain becomes real.

RED-first contract tests for the pipeline document chain:
- #259: the trends phase writes non-empty ``docs/plan/trends.md`` and passes
  the project's style into ``research_trends`` (never hardcoded "commercial")
- #258: the concept phase (mocked agent runner) writes
  ``docs/plan/concept.md``; without a runner / without a brief it fails
  honestly (G11 — never fake-pass); ``approve <id> concept`` fails closed on
  a missing/empty concept.md
- #247: ``run --execute --until script`` progresses past concept with the
  mocked runner (no "not implemented yet")
- #257: the script phase reads ``docs/plan/concept.md`` (fail-closed with a
  resume hint when missing) and composes shot prompts from the brief/concept
  instead of the hardcoded demo strings
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

from click.testing import CliRunner

from brandly_cli.cli import cli
from brandly_cli.cmd.production import (
    PHASE_HANDOFF_SPECS,
    Director,
    DirectorConfig,
)
from brandly_cli.constants import PHASE_ORDER
from brandly_cli.project_manager import ProjectManager
from brandly_cli.types import ProjectData

PID = "chain-proj"
BRIEF = "A precision espresso machine for small cafes"


def _make_project(root: Path, **overrides: Any) -> None:
    pm = ProjectManager(root)
    data: dict[str, Any] = {"id": PID, "name": "Chain Project", "description": BRIEF}
    data.update(overrides)
    asyncio.run(pm.create(ProjectData(**data)))


def _seed_current(root: Path, phase: str) -> None:
    """Seed ``current_phase`` + mark the prior phases completed (like ``run``)."""
    pm = ProjectManager(root)
    prior = {p: {"status": "completed"} for p in PHASE_ORDER[: PHASE_ORDER.index(phase)]}
    asyncio.run(pm.update(PID, {"current_phase": phase, "phases": prior}))


def _director(root: Path, agent_runner=None) -> Director:  # type: ignore[no-untyped-def]
    return Director(DirectorConfig(root, agent_runner=agent_runner))


def _project_file(root: Path, name: str) -> Path:
    return root / ".brandly" / PID / name


class TestTrendsPhase259:
    """#259: the trends phase writes its document and uses the project category."""

    def test_trends_writes_doc_and_uses_project_style(self, tmp_path: Path) -> None:
        _make_project(tmp_path, style="fashion")
        _seed_current(tmp_path, "trends")
        director = _director(tmp_path)
        calls: list[str] = []

        async def fake_research(category: str, platforms=None):  # type: ignore[no-untyped-def]
            calls.append(category)
            return {
                "trending_formats": [{"name": "silent luxury", "virality": 9}],
                "recommended_format": "silent luxury",
            }

        with patch("brandly_cli.trends.research_trends", side_effect=fake_research):
            result = asyncio.run(director.run_phase(PID, "trends"))

        assert "error" not in result, result
        # The project's style is the research category — never hardcoded
        assert calls == ["fashion"], calls
        trends_md = _project_file(tmp_path, "docs/plan/trends.md")
        assert trends_md.is_file(), "trends phase did not write docs/plan/trends.md"
        assert trends_md.read_text(encoding="utf-8").strip()


class TestConceptPhase258:
    """#258: the concept phase derives from the brief — fail-honest without an agent."""

    def test_concept_writes_doc_with_mocked_runner(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        _seed_current(tmp_path, "concept")
        director = _director(
            tmp_path, agent_runner=lambda brief: f"# Concept\n\n{brief} — the world of the product"
        )

        result = asyncio.run(director.run_phase(PID, "concept"))

        assert "error" not in result, result
        concept_md = _project_file(tmp_path, "docs/plan/concept.md")
        assert concept_md.is_file(), "concept phase did not write docs/plan/concept.md"
        assert BRIEF in concept_md.read_text(encoding="utf-8")

    def test_concept_fails_honest_without_runner(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        _seed_current(tmp_path, "concept")
        director = _director(tmp_path)  # no agent runner wired

        result = asyncio.run(director.run_phase(PID, "concept"))

        # G11: without an agent the phase fails honestly — never fake-pass
        assert "error" in result, result

    def test_concept_fails_closed_on_missing_brief(self, tmp_path: Path) -> None:
        _make_project(tmp_path, description=None)
        _seed_current(tmp_path, "concept")
        director = _director(tmp_path, agent_runner=lambda brief: "# Concept")

        result = asyncio.run(director.run_phase(PID, "concept"))

        assert "error" in result, result
        assert "brief" in result["error"].lower()

    def test_approve_concept_fails_closed_on_missing_artifact(self, tmp_path: Path) -> None:
        """`brandly approve <id> concept` fails closed (exit != 0) when
        docs/plan/concept.md is missing."""
        _make_project(tmp_path)
        _seed_current(tmp_path, "concept")
        env = os.environ.copy()
        env["ROOT"] = str(tmp_path)
        runner = CliRunner(env=env)

        result = runner.invoke(cli, ["approve", PID, "concept"])

        assert result.exit_code != 0
        assert "concept" in result.output.lower()

    def test_approve_concept_fails_closed_on_empty_artifact(self, tmp_path: Path) -> None:
        """`approve <id> concept` also fails closed when concept.md is EMPTY."""
        _make_project(tmp_path)
        _seed_current(tmp_path, "concept")
        concept_md = _project_file(tmp_path, "docs/plan/concept.md")
        concept_md.parent.mkdir(parents=True, exist_ok=True)
        concept_md.write_text("   \n", encoding="utf-8")
        env = os.environ.copy()
        env["ROOT"] = str(tmp_path)
        runner = CliRunner(env=env)

        result = runner.invoke(cli, ["approve", PID, "concept"])

        assert result.exit_code != 0


class TestRunUntilScript247:
    """#247: `run --execute --until script` progresses past concept."""

    def test_run_until_script_progresses_past_concept(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        _seed_current(tmp_path, "trends")
        director = _director(
            tmp_path, agent_runner=lambda brief: f"# Concept\n\n{brief} — world"
        )

        async def fake_research(category: str, platforms=None):  # type: ignore[no-untyped-def]
            return {"trending_formats": [{"name": "f1", "virality": 9}]}

        with patch("brandly_cli.trends.research_trends", side_effect=fake_research):
            result = asyncio.run(director.run_pipeline(PID, until="script"))

        assert "error" not in result, result
        assert result["phases_run"] == ["trends", "concept", "script"]
        assert all(
            "not implemented yet" not in json.dumps(r) for r in result["results"]
        ), result["results"]


class TestScriptPhase257:
    """#257: the script phase reads the concept and composes from it."""

    def test_script_composes_from_concept_not_hardcoded(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        _seed_current(tmp_path, "concept")
        director = _director(
            tmp_path, agent_runner=lambda brief: "# Concept\n\nMinimalist espresso bar at dawn"
        )

        seeded = asyncio.run(director.run_phase(PID, "concept"))
        assert "error" not in seeded, seeded

        result = asyncio.run(director.run_phase(PID, "script"))

        assert "error" not in result, result
        shots_path = _project_file(tmp_path, "shots.json")
        shots = json.loads(shots_path.read_text(encoding="utf-8"))
        prompts = " ".join(s["prompt"] for s in shots).lower()
        # The hardcoded demo strings are gone
        assert "demonstrates key features" not in prompts
        assert "clean studio setting" not in prompts
        # The concept and the brief drive the prompts
        assert "minimalist espresso bar at dawn" in prompts
        assert BRIEF.lower() in prompts

    def test_script_fails_closed_on_missing_concept(self, tmp_path: Path) -> None:
        """The script phase fail-closes with a resume hint when concept.md is
        missing (mirrors the asset phase's shots.json pattern)."""
        _make_project(tmp_path)
        _seed_current(tmp_path, "script")
        director = _director(tmp_path, agent_runner=lambda brief: "# Concept")

        result = asyncio.run(director.run_phase(PID, "script"))

        assert "error" in result, result
        assert "concept" in result["error"].lower()


class TestHandoffSpecs:
    """PHASE_HANDOFF_SPECS text matches the delivered behavior (#261 rule)."""

    def test_specs_match_delivered_behavior(self) -> None:
        # trends: writes the doc (real output)
        assert "docs/plan/trends.md" in PHASE_HANDOFF_SPECS["trends"]["outputs"]
        # concept: derives from the brief via an agent runner; moodboard optional
        assert "docs/plan/concept.md" in PHASE_HANDOFF_SPECS["concept"]["outputs"]
        assert any(
            "optional" in o.lower() for o in PHASE_HANDOFF_SPECS["concept"]["outputs"]
        ), PHASE_HANDOFF_SPECS["concept"]["outputs"]
        assert any(
            "brief" in i.lower() for i in PHASE_HANDOFF_SPECS["concept"]["inputs"]
        ), PHASE_HANDOFF_SPECS["concept"]["inputs"]
        # script: reads concept.md + the brief (not the moodboard)
        assert any(
            "concept.md" in i for i in PHASE_HANDOFF_SPECS["script"]["inputs"]
        ), PHASE_HANDOFF_SPECS["script"]["inputs"]
        assert any(
            "brief" in i.lower() for i in PHASE_HANDOFF_SPECS["script"]["inputs"]
        ), PHASE_HANDOFF_SPECS["script"]["inputs"]


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
