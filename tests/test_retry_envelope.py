"""Goal 7 PR G: retry-instruction envelopes and bounded phase retries.

When ``Director.run_pipeline`` encounters a phase failure (a failing gate or
worker error payload):
1. It records an attempt on the phase (``attempts: int`` in ``project.phases[<phase>]``).
2. It returns a structured ``retry_instruction`` envelope with failing gates,
   verdict details, files to fix, and the exact re-run command.
3. If attempts exceed MAX_PHASE_ATTEMPTS (3), ``retry_instruction["escalate"]`` is True,
   advising escalation via ``brandly approve <id> <phase>``.
4. ``brandly plan --json`` surfaces ``attempts`` and ``retry_instruction`` for failing phases.
5. Approving or completing a phase resets or preserves attempts appropriately.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner, Result

from brandly_cli.cli import cli
from brandly_cli.cmd.production import (
    MAX_PHASE_ATTEMPTS,
    Director,
    DirectorConfig,
    phase_handoffs,
)
from brandly_cli.project_manager import ProjectManager
from brandly_cli.types import PhaseResult, ProjectData

PID = "testretry"


def _make_project(tmp_path: Path, pid: str = PID) -> str:
    pm = ProjectManager(tmp_path)
    asyncio.run(
        pm.update(
            pid,
            {
                "id": pid,
                "name": "Retry Test",
                "slug": pid,
                "status": "pending",
                "current_phase": "concept",
                "style": "cinematic",
                "shot_count": 5,
                "budget": 500,
                "spent": 0,
            },
        )
    )
    return pid


def _invoke(root: Path, args: list[str], **kwargs: Any) -> Result:
    return CliRunner().invoke(cli, ["--root", str(root), *args], **kwargs)


def _patch_worker(
    monkeypatch: pytest.MonkeyPatch,
    failing: dict[str, Any] | None = None,
) -> None:
    async def fake(self: Director, phase: str, proj: ProjectData) -> dict[str, Any]:
        if failing and phase in failing:
            outcome = failing[phase]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return {"phase": phase, "ok": True}

    monkeypatch.setattr(Director, "_run_phase_real", fake)


def test_phase_result_has_attempts_field() -> None:
    pr = PhaseResult()
    assert pr.attempts == 0
    pr_custom = PhaseResult(attempts=2)
    assert pr_custom.attempts == 2


def test_run_pipeline_failure_returns_retry_instruction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    _patch_worker(
        monkeypatch,
        failing={"concept": {"error": "concept phase needs revision"}},
    )

    director = Director(DirectorConfig(tmp_path))
    res = asyncio.run(director.run_pipeline(pid))

    assert "error" in res
    assert res["failed_phase"] == "concept"
    assert "retry_instruction" in res

    instr = res["retry_instruction"]
    assert instr["project_id"] == pid
    assert instr["phase"] == "concept"
    assert instr["error"] == "concept phase needs revision"
    assert instr["attempts"] == 1
    assert instr["max_attempts"] == MAX_PHASE_ATTEMPTS
    assert instr["escalate"] is False
    assert "brandly run" in instr["next_command"]
    assert "brandly approve" in instr["escalate_command"]


def test_retry_counter_increments_and_escalates_on_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    _patch_worker(
        monkeypatch,
        failing={"concept": {"error": "concept phase needs revision"}},
    )
    director = Director(DirectorConfig(tmp_path))

    # Attempt 1
    res1 = asyncio.run(director.run_pipeline(pid))
    assert res1["retry_instruction"]["attempts"] == 1
    assert res1["retry_instruction"]["escalate"] is False

    # Attempt 2
    res2 = asyncio.run(director.run_pipeline(pid))
    assert res2["retry_instruction"]["attempts"] == 2
    assert res2["retry_instruction"]["escalate"] is False

    # Attempt 3 (hits max attempts)
    res3 = asyncio.run(director.run_pipeline(pid))
    assert res3["retry_instruction"]["attempts"] == 3
    assert res3["retry_instruction"]["escalate"] is True
    assert f"brandly approve {pid} concept" in res3["retry_instruction"]["escalate_command"]

    # Verify state in ProjectData
    proj = asyncio.run(ProjectManager(tmp_path).read(pid))
    assert proj is not None
    assert proj.phases["concept"].attempts == 3
    assert proj.phases["concept"].status == "failed"


def test_plan_json_surfaces_attempts_and_retry_instruction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    _patch_worker(
        monkeypatch,
        failing={"concept": {"error": "concept gate rejected prompt"}},
    )
    director = Director(DirectorConfig(tmp_path))
    asyncio.run(director.run_pipeline(pid))

    handoffs_doc = phase_handoffs(tmp_path, pid)
    concept_handoff = next(h for h in handoffs_doc["handoffs"] if h["id"] == "concept")

    assert concept_handoff["attempts"] == 1
    assert concept_handoff["retry_instruction"] is not None
    assert concept_handoff["retry_instruction"]["attempts"] == 1
    assert concept_handoff["retry_instruction"]["error"] == "concept gate rejected prompt"


def test_run_cli_emits_retry_guidance_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    _patch_worker(
        monkeypatch,
        failing={"concept": {"error": "concept phase syntax error"}},
    )

    result = _invoke(tmp_path, ["run", pid, "--execute", "--yes"])

    assert result.exit_code == 1
    assert "Phase 'concept' failed" in result.output
    assert "Retry attempt: 1/3" in result.output


def test_success_after_retry_resumes_and_preserves_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    _patch_worker(
        monkeypatch,
        failing={"concept": {"error": "concept phase needs revision"}},
    )
    director = Director(DirectorConfig(tmp_path))

    # First run fails: attempts = 1, phase failed, pipeline stuck at concept.
    res1 = asyncio.run(director.run_pipeline(pid))
    assert res1["retry_instruction"]["attempts"] == 1

    # The worker is fixed (re-dispatch succeeds): the phase completes, the
    # retry counter is preserved as an audit trail, and the pipeline advances.
    _patch_worker(monkeypatch, failing=None)
    res2 = asyncio.run(director.run_pipeline(pid, until="concept"))

    assert "error" not in res2, res2
    proj = asyncio.run(ProjectManager(tmp_path).read(pid))
    assert proj is not None
    assert proj.phases["concept"].status == "completed"
    assert proj.phases["concept"].attempts == 1  # preserved, not reset
    assert proj.current_phase == "script"


def test_state_only_run_preserves_retry_counter(tmp_path: Path) -> None:
    pid = _make_project(tmp_path)
    asyncio.run(
        ProjectManager(tmp_path).update(
            pid,
            {
                "status": "failed",
                "current_phase": "concept",
                "phases": {
                    "concept": {
                        "status": "failed",
                        "error": "concept phase needs revision",
                        "attempts": 2,
                    },
                },
            },
        )
    )

    result = _invoke(tmp_path, ["run", pid])

    assert result.exit_code == 0, result.output
    proj = asyncio.run(ProjectManager(tmp_path).read(pid))
    assert proj is not None
    # The state-only path must not erase the persisted retry counter —
    # otherwise a mixed workflow could bypass the 3-attempt cap.
    assert proj.phases["concept"].attempts == 2
