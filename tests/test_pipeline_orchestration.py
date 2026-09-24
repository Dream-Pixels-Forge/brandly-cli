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
* Fabricated stub workers (``concept``/``re_edit``/``publish``)
  report "not implemented" instead of pretending to succeed.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner, Result

from brandly_cli import scenes, shot_runner
from brandly_cli.cli import cli
from brandly_cli.cmd import production
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


# asset became a real produce-runner phase in PR B (tests below); the
# remaining fabricated stubs must still report "not implemented".
@pytest.mark.parametrize("phase", ["concept", "re_edit", "publish"])
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
    # A stub worker must never kick off a private generation loop.
    assert generate_calls == []


# ---------------------------------------------------------------------------
# PR B: real script phase — writes shots.json with G3 scene-id inputs
# ---------------------------------------------------------------------------


def _director(root: Path) -> Director:
    return Director(DirectorConfig(root))


def _shots_json_path(root: Path, pid: str = PID) -> Path:
    return root / ".brandly" / pid / "shots.json"


def test_script_phase_writes_real_shots_json(tmp_path: Path) -> None:
    _make_project(tmp_path)
    director = _director(tmp_path)

    result = asyncio.run(director.run_phase(PID, "script"))

    assert "error" not in result, result
    shots_path = _shots_json_path(tmp_path)
    assert shots_path.is_file()
    shots = shot_runner.load_shots_file(shots_path)
    assert isinstance(shots, list)
    proj = _read(tmp_path)
    assert len(shots) == proj.shot_count
    for index, shot in enumerate(shots, start=1):
        assert str(shot.get("prompt", "")).strip()
        assert shot.get("style") == proj.style
        assert shot.get("scene") == 1
        assert shot.get("shot") == index


def test_script_phase_shots_json_yields_g3_scene_ids(tmp_path: Path) -> None:
    _make_project(tmp_path)
    director = _director(tmp_path)
    asyncio.run(director.run_phase(PID, "script"))

    shots = shot_runner.load_shots_file(_shots_json_path(tmp_path))
    manifest = scenes.build_scenes(PID, shots, root=tmp_path)

    assert [s["id"] for s in manifest["scenes"]] == ["S01"]
    scene = manifest["scenes"][0]
    assert [sh["clip"] for sh in scene["shots"]] == [
        shot_runner.clip_filename(1, i) for i in range(1, len(shots) + 1)
    ]
    assert scene["shots"][0]["clip"] == "Scene-01-Shot-1-1.mp4"



# ---------------------------------------------------------------------------
# PR B: real asset phase — drives the produce runner, never a private loop
# ---------------------------------------------------------------------------


def test_asset_phase_fails_closed_without_shots_json(tmp_path: Path) -> None:
    _make_project(tmp_path)
    director = _director(tmp_path)

    result = asyncio.run(director.run_phase(PID, "asset"))

    assert "error" in result
    assert "script" in result["error"]
    proj = _read(tmp_path)
    assert proj.phases["asset"].status == "failed"
    assert proj.current_phase == "init"  # frozen: a re-run retries this phase


def test_asset_phase_rejects_invalid_shots_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_project(tmp_path)
    _shots_json_path(tmp_path).write_text("{ not json", encoding="utf-8")

    def runner(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("produce runner must not run on an invalid shot list")

    monkeypatch.setattr(production, "_run_produce_runner", runner)
    director = _director(tmp_path)

    result = asyncio.run(director.run_phase(PID, "asset"))

    assert "error" in result
    assert "invalid shot list" in result["error"]


def test_asset_phase_invokes_produce_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_project(tmp_path)
    director = _director(tmp_path)
    asyncio.run(director.run_phase(PID, "script"))
    expected = shot_runner.load_shots_file(_shots_json_path(tmp_path))
    calls: list[dict[str, Any]] = []

    def fake_runner(
        ctx: Any, project_id: str, data: Any, root: Path, *args: Any, **kwargs: Any
    ) -> None:
        calls.append({"project_id": project_id, "data": data, "root": root})
        # G3: the scene manifest must exist BEFORE any generation runs.
        assert scenes.scenes_path(project_id, root=root).is_file()

    monkeypatch.setattr(production, "_run_produce_runner", fake_runner)

    result = asyncio.run(director.run_phase(PID, "asset"))

    assert "error" not in result, result
    assert len(calls) == 1
    call = calls[0]
    assert call["project_id"] == PID
    assert call["data"] == expected
    assert call["root"] == tmp_path
    manifest = scenes.load_scenes(PID, root=tmp_path)
    assert manifest is not None
    assert [s["id"] for s in manifest["scenes"]] == ["S01"]
    assert len(manifest["scenes"][0]["shots"]) == len(expected)
    proj = _read(tmp_path)
    assert proj.phases["asset"].status == "completed"


def test_asset_phase_fails_closed_when_runner_stops_then_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_project(tmp_path)
    director = _director(tmp_path)
    asyncio.run(director.run_phase(PID, "script"))
    state = {"calls": 0}

    def flaky_runner(*args: Any, **kwargs: Any) -> None:
        state["calls"] += 1
        if state["calls"] == 1:
            raise SystemExit(1)

    monkeypatch.setattr(production, "_run_produce_runner", flaky_runner)

    first = asyncio.run(director.run_phase(PID, "asset"))
    assert "error" in first
    assert "re-run" in first["error"]
    proj = _read(tmp_path)
    assert proj.phases["asset"].status == "failed"

    second = asyncio.run(director.run_phase(PID, "asset"))
    assert "error" not in second, second
    proj = _read(tmp_path)
    assert proj.phases["asset"].status == "completed"


def test_run_execute_runs_real_script_and_asset_phases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    # concept is still an honest "not implemented" phase in this PR, so the
    # run is resumed from script (the first real generation phase).
    asyncio.run(
        ProjectManager(tmp_path).update(
            pid,
            {
                "status": "running",
                "current_phase": "script",
                "phases": {
                    "init": PhaseResult(status="completed"),
                    "trends": PhaseResult(status="completed"),
                    "concept": PhaseResult(status="completed"),
                },
            },
        )
    )
    runner_calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        production,
        "_run_produce_runner",
        lambda *args, **kwargs: runner_calls.append((args, kwargs)),
    )

    result = _invoke(tmp_path, ["run", pid, "--execute", "--until", "asset", "--yes"])

    assert result.exit_code == 0, result.output
    proj = _read(tmp_path)
    assert proj.phases["script"].status == "completed"
    assert proj.phases["asset"].status == "completed"
    assert proj.current_phase == "audio"
    assert _shots_json_path(tmp_path).is_file()
    assert scenes.load_scenes(pid, root=tmp_path) is not None
    assert len(runner_calls) == 1
