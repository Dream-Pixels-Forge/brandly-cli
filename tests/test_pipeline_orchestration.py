"""Goal 2 (audit F3/F4): real director orchestration via ``brandly run --execute``.

The ``run`` command historically only flipped state ("Next: approve") while
``Director.run_phase``/``run_pipeline`` sat unreachable, and several phase
workers returned fabricated success payloads. These tests pin the new
contract:

* ``brandly run <id> --execute [--until <phase>] [--yes]`` drives
  ``Director.run_pipeline`` for real, resumable from ``project.phases``.
* A phase worker that returns an ``error`` payload — or raises — fails
  closed: the phase is marked ``failed``, ``current_phase`` does NOT
  advance, and the pipeline stops with a non-zero exit code.
* Fabricated stub workers (``concept``/``asset``/``re_edit``/``publish``)
  report "not implemented" instead of pretending to succeed.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner, Result

from brandly_cli.cli import cli
from brandly_cli.cmd.production import Director, DirectorConfig
from brandly_cli.constants import PHASE_ORDER
from brandly_cli.project_manager import ProjectManager
from brandly_cli.types import PhaseResult, ProjectData

PID = "g2proj"


def _make_project(root: Path) -> str:
    asyncio.run(ProjectManager(root).create(ProjectData(id=PID, name="G2 Test Project")))
    return PID


def _read(root: Path, pid: str = PID) -> ProjectData:
    proj = asyncio.run(ProjectManager(root).read(pid))
    assert proj is not None
    return proj


def _invoke(root: Path, args: list[str], **kwargs: Any) -> Result:
    return CliRunner().invoke(cli, ["--root", str(root), *args], **kwargs)


def _patch_worker(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[str],
    failing: dict[str, Any] | None = None,
) -> None:
    """Replace the phase worker with a recorder; no provider is touched."""

    async def fake(self: Director, phase: str, proj: ProjectData) -> dict[str, Any]:
        calls.append(phase)
        if failing and phase in failing:
            outcome = failing[phase]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return {"phase": phase, "ok": True}

    monkeypatch.setattr(Director, "_run_phase_real", fake)


# ---------------------------------------------------------------------------
# --execute drives the real pipeline
# ---------------------------------------------------------------------------


def test_run_execute_completes_all_phases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    calls: list[str] = []
    _patch_worker(monkeypatch, calls)

    result = _invoke(tmp_path, ["run", pid, "--execute", "--yes"])

    assert result.exit_code == 0, result.output
    assert calls == PHASE_ORDER
    proj = _read(tmp_path)
    assert proj.current_phase == "done"
    assert proj.status == "completed"
    for phase in PHASE_ORDER:
        assert proj.phases[phase].status == "completed", phase


def test_run_execute_until_stops_after_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    calls: list[str] = []
    _patch_worker(monkeypatch, calls)

    result = _invoke(tmp_path, ["run", pid, "--execute", "--yes", "--until", "script"])

    assert result.exit_code == 0, result.output
    assert calls == ["init", "trends", "concept", "script"]
    proj = _read(tmp_path)
    assert proj.current_phase == "asset"
    assert proj.phases["script"].status == "completed"
    assert "asset" not in proj.phases


def test_run_execute_resumes_from_current_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    asyncio.run(
        ProjectManager(tmp_path).update(
            pid,
            {
                "status": "running",
                "current_phase": "concept",
                "phases": {
                    "init": PhaseResult(status="completed"),
                    "trends": PhaseResult(status="completed"),
                },
            },
        )
    )
    calls: list[str] = []
    _patch_worker(monkeypatch, calls)

    result = _invoke(tmp_path, ["run", pid, "--execute", "--yes"])

    assert result.exit_code == 0, result.output
    assert calls == PHASE_ORDER[PHASE_ORDER.index("concept"):]


# ---------------------------------------------------------------------------
# Fail-closed semantics
# ---------------------------------------------------------------------------


def test_run_execute_error_payload_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    calls: list[str] = []
    _patch_worker(
        monkeypatch, calls, failing={"concept": {"error": "concept phase not implemented"}}
    )

    result = _invoke(tmp_path, ["run", pid, "--execute", "--yes"])

    assert result.exit_code == 1, result.output
    assert calls == ["init", "trends", "concept"]
    proj = _read(tmp_path)
    assert proj.phases["concept"].status == "failed"
    assert "not implemented" in (proj.phases["concept"].error or "")
    assert proj.current_phase == "concept"
    assert proj.status == "failed"


def test_run_execute_worker_exception_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    calls: list[str] = []
    _patch_worker(monkeypatch, calls, failing={"asset": RuntimeError("provider down")})

    result = _invoke(tmp_path, ["run", pid, "--execute", "--yes"])

    assert result.exit_code == 1, result.output
    proj = _read(tmp_path)
    assert proj.phases["asset"].status == "failed"
    assert "provider down" in (proj.phases["asset"].error or "")
    assert proj.current_phase == "asset"
    assert proj.status == "failed"
    # Phases after the failure never ran.
    assert "audio" not in proj.phases


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def test_run_without_execute_keeps_state_only_behaviour(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    calls: list[str] = []
    _patch_worker(monkeypatch, calls)

    result = _invoke(tmp_path, ["run", pid])

    assert result.exit_code == 0, result.output
    assert "Next: approve" in result.output
    assert calls == []


def test_run_execute_aborts_without_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    calls: list[str] = []
    _patch_worker(monkeypatch, calls)

    result = _invoke(tmp_path, ["run", pid, "--execute"], input="n\n")

    assert result.exit_code == 1
    assert calls == []
    proj = _read(tmp_path)
    assert proj.current_phase == "init"
    assert proj.status == "pending"


def test_run_help_lists_execute_flags() -> None:
    result = CliRunner().invoke(cli, ["run", "--help"])
    assert result.exit_code == 0
    for flag in ("--execute", "--until", "--yes"):
        assert flag in result.output


# ---------------------------------------------------------------------------
# Fabricated stubs report "not implemented" (audit F4)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("phase", ["concept", "asset", "re_edit", "publish"])
def test_stub_phases_report_not_implemented(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    pid = _make_project(tmp_path)
    generate_calls: list[str] = []

    async def fake_generate(*args: Any, **kwargs: Any) -> dict[str, Any]:
        generate_calls.append(phase)
        return {}

    # A stub worker must never kick off a private generation loop.
    monkeypatch.setattr(Director, "generate_video", fake_generate)
    monkeypatch.setattr(Director, "generate_music", fake_generate)

    director = Director(DirectorConfig(tmp_path))
    proj = _read(tmp_path, pid)
    result = asyncio.run(director._run_phase_real(phase, proj))

    assert "error" in result, f"{phase} returned fabricated success: {result}"
    assert "not implemented" in result["error"]
    assert generate_calls == []

