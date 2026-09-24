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
* ``re_edit`` stitches the scene clips (``stitch``), ``validate`` runs the
  G3 scene gate (``scenes.evaluate_all`` + deterministic quality runner),
  and ``publish`` calls the platform exporters (``export_platforms``) —
  all fail closed.
* The remaining fabricated stub (``concept``) reports "not implemented"
  instead of pretending to succeed.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from click.testing import CliRunner, Result

from brandly_cli import (
    export_platforms,
    layout,
    quality_gate,
    scenes,
    shot_runner,
    stitch,
)
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


# asset became a real produce-runner phase in PR B; re_edit/validate/publish
# became real phases in PR C. The remaining fabricated stub (concept) must
# still report "not implemented".
@pytest.mark.parametrize("phase", ["concept"])
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


# ---------------------------------------------------------------------------
# PR C: real re_edit / validate / publish phases
#
# re_edit stitches the scene clips (``stitch.stitch_videos``), validate runs
# the G3 scene gate (``scenes.evaluate_all`` with the deterministic quality
# runner, the same contract as ``brandly gate --all-scenes``), and publish
# calls the platform exporters (``export_platforms.export_for_platform``).
# All three fail closed: no scene manifest, missing clips, a non-pass gate
# verdict, or an export error must block the phase advance.
# ---------------------------------------------------------------------------


def _clip_paths(root: Path, pid: str = PID) -> list[Path]:
    """Expected scene clip paths from the manifest, in stitch order."""
    manifest = scenes.load_scenes(pid, root=root)
    assert manifest is not None
    videos_root = layout.resolve_media_root(root, pid, "videos")
    expected: list[Path] = []
    for entry in manifest["scenes"]:
        for shot in entry["shots"]:
            expected.append(
                videos_root / str(shot.get("folder") or "scenes") / str(shot["clip"])
            )
    return expected


def _write_fake_clips(root: Path, pid: str = PID) -> list[Path]:
    paths = _clip_paths(root, pid)
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake-clip")
    return paths


def _patch_runner_writing_clips(monkeypatch: pytest.MonkeyPatch) -> None:
    def runner(
        ctx: Any, project_id: str, data: Any, root: Any, *args: Any, **kwargs: Any
    ) -> None:
        _write_fake_clips(Path(root), project_id)

    monkeypatch.setattr(production, "_run_produce_runner", runner)


def _patch_runner_no_clips(monkeypatch: pytest.MonkeyPatch) -> None:
    def runner(
        ctx: Any, project_id: str, data: Any, root: Any, *args: Any, **kwargs: Any
    ) -> None:
        pass

    monkeypatch.setattr(production, "_run_produce_runner", runner)


def _make_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, write_clips: bool = True
) -> Director:
    """Create the project, then run the real script + asset phases."""
    _make_project(tmp_path)
    director = _director(tmp_path)
    script_result = asyncio.run(director.run_phase(PID, "script"))
    assert "error" not in script_result, script_result
    if write_clips:
        _patch_runner_writing_clips(monkeypatch)
    else:
        _patch_runner_no_clips(monkeypatch)
    asset_result = asyncio.run(director.run_phase(PID, "asset"))
    assert "error" not in asset_result, asset_result
    return director


def _patch_verify(
    monkeypatch: pytest.MonkeyPatch, status: str, calls: list[Any]
) -> None:
    async def fake_verify(clip: Path, **kwargs: Any) -> SimpleNamespace:
        calls.append((clip, kwargs))
        return SimpleNamespace(status=status)

    monkeypatch.setattr(quality_gate, "verify_element", fake_verify)


def _stitched_assets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Director:
    """re_edit on top of _make_assets: fake stitch writes final.mp4."""
    director = _make_assets(tmp_path, monkeypatch, write_clips=True)

    async def fake_stitch(
        clips: list[Path], output: Path, **kwargs: Any
    ) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake-final")
        return {"output_path": str(output), "duration_seconds": 12.5}

    monkeypatch.setattr(stitch, "stitch_videos", fake_stitch)
    re_edit_result = asyncio.run(director.run_phase(PID, "re_edit"))
    assert "error" not in re_edit_result, re_edit_result
    return director


def test_re_edit_phase_stitches_scene_clips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    director = _make_assets(tmp_path, monkeypatch, write_clips=True)
    expected_clips = _clip_paths(tmp_path)
    expected_output = layout.resolve_media_root(tmp_path, PID, "videos") / "final.mp4"
    stitch_calls: list[tuple[list[Path], Path]] = []

    async def fake_stitch(
        clips: list[Path], output: Path, **kwargs: Any
    ) -> dict[str, Any]:
        stitch_calls.append((list(clips), output))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake-final")
        return {
            "output_path": str(output),
            "duration_seconds": 12.5,
            "size_bytes": 1024,
            "transitions_applied": ["fade"],
            "color_grade": "cinematic",
        }

    monkeypatch.setattr(stitch, "stitch_videos", fake_stitch)

    result = asyncio.run(director.run_phase(PID, "re_edit"))

    assert "error" not in result, result
    assert len(stitch_calls) == 1
    assert stitch_calls[0][0] == expected_clips  # every clip, in scene order
    assert Path(stitch_calls[0][1]) == expected_output
    assert result["result"]["clips"] == len(expected_clips)
    assert expected_output.is_file()
    proj = _read(tmp_path)
    assert proj.phases["re_edit"].status == "completed"
    assert proj.current_phase == "validate"


def test_re_edit_phase_fails_closed_when_clips_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    director = _make_assets(tmp_path, monkeypatch, write_clips=False)

    async def fake_music(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"task_id": "music-fake"}

    monkeypatch.setattr(Director, "generate_music", fake_music)
    audio_result = asyncio.run(director.run_phase(PID, "audio"))
    assert "error" not in audio_result, audio_result  # current_phase → re_edit

    called = {"n": 0}

    async def fake_stitch(*args: Any, **kwargs: Any) -> dict[str, Any]:
        called["n"] += 1
        return {}

    monkeypatch.setattr(stitch, "stitch_videos", fake_stitch)

    result = asyncio.run(director.run_phase(PID, "re_edit"))

    assert "error" in result
    assert "missing" in result["error"]
    assert "re-run" in result["error"]
    assert called["n"] == 0  # never reaches ffmpeg with an incomplete set
    proj = _read(tmp_path)
    assert proj.phases["re_edit"].status == "failed"
    assert proj.current_phase == "re_edit"  # advance is blocked


def test_re_edit_phase_fails_closed_without_scene_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_project(tmp_path)
    director = _director(tmp_path)
    asyncio.run(director.run_phase(PID, "script"))  # manifest written by asset only

    async def fake_music(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"task_id": "music-fake"}

    monkeypatch.setattr(Director, "generate_music", fake_music)
    asyncio.run(director.run_phase(PID, "audio"))  # current_phase → re_edit
    result = asyncio.run(director.run_phase(PID, "re_edit"))

    assert "error" in result
    assert "manifest" in result["error"]
    proj = _read(tmp_path)
    assert proj.phases["re_edit"].status == "failed"
    assert proj.current_phase == "re_edit"


def test_validate_phase_runs_scene_gate_and_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    director = _make_assets(tmp_path, monkeypatch, write_clips=True)
    expected_clips = _clip_paths(tmp_path)
    calls: list[tuple[Path, dict[str, Any]]] = []
    _patch_verify(monkeypatch, "pass", calls)

    result = asyncio.run(director.run_phase(PID, "validate"))

    assert "error" not in result, result
    assert result["result"]["verdict"] == "pass"
    assert [clip for clip, _ in calls] == expected_clips  # every present clip gated
    for _, kwargs in calls:
        assert kwargs["use_ai"] is False  # deterministic runner, like the gate CLI
    proj = _read(tmp_path)
    assert proj.phases["validate"].status == "completed"
    assert proj.current_phase == "publish"


@pytest.mark.parametrize("verdict", ["fail", "warn"])
def test_validate_phase_blocks_advance_when_gate_not_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, verdict: str
) -> None:
    director = _stitched_assets(tmp_path, monkeypatch)  # current_phase → validate
    _patch_verify(monkeypatch, verdict, [])

    result = asyncio.run(director.run_phase(PID, "validate"))

    assert "error" in result
    assert "S01" in result["error"]  # names the failing scene
    assert verdict in result["error"].lower()
    proj = _read(tmp_path)
    assert proj.phases["validate"].status == "failed"
    assert proj.current_phase == "validate"  # advance is blocked


def test_validate_phase_fails_closed_without_scene_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_project(tmp_path)
    director = _director(tmp_path)
    result = asyncio.run(director.run_phase(PID, "validate"))

    assert "error" in result
    assert "manifest" in result["error"]
    proj = _read(tmp_path)
    assert proj.phases["validate"].status == "failed"


def _patch_export(
    monkeypatch: pytest.MonkeyPatch, calls: list[Any], error: str | None = None
) -> None:
    async def fake_export(
        input_video: Path, platform: str, out_dir: Path, **kwargs: Any
    ) -> dict[str, Any]:
        calls.append((input_video, platform, out_dir))
        if error is not None:
            return {"error": error}
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{Path(input_video).stem}_{platform}{Path(input_video).suffix}"
        out.write_bytes(b"fake-export")
        return {
            "platform": platform,
            "output_path": str(out),
            "ratio": "9:16",
            "duration_seconds": 12.5,
            "file_size_bytes": 8,
            "captions_added": False,
        }

    monkeypatch.setattr(export_platforms, "export_for_platform", fake_export)


def test_publish_phase_exports_platforms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stitched_assets(tmp_path, monkeypatch)
    final = layout.resolve_media_root(tmp_path, PID, "videos") / "final.mp4"
    export_dir = layout.resolve_project_dir(tmp_path, PID) / "export"
    calls: list[tuple[Path, str, Path]] = []
    _patch_export(monkeypatch, calls)

    result = asyncio.run(_director(tmp_path).run_phase(PID, "publish"))

    assert "error" not in result, result
    assert result["result"]["platforms"] == ["tiktok", "youtube_standard"]
    assert len(calls) == 2
    assert all(Path(c[0]) == final for c in calls)  # exports the stitched final
    assert all(Path(c[2]) == export_dir for c in calls)
    for _, platform, _ in calls:
        assert (export_dir / f"final_{platform}.mp4").is_file()
    proj = _read(tmp_path)
    assert proj.phases["publish"].status == "completed"
    assert proj.current_phase == "done"


def test_publish_phase_fails_closed_on_export_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stitched_assets(tmp_path, monkeypatch)
    calls: list[Any] = []
    _patch_export(monkeypatch, calls, error="ffmpeg not found. Install FFmpeg first.")

    result = asyncio.run(_director(tmp_path).run_phase(PID, "publish"))

    assert "error" in result
    assert "tiktok" in result["error"]  # names the failing platform
    proj = _read(tmp_path)
    assert proj.phases["publish"].status == "failed"
    assert proj.current_phase == "validate"  # stuck before publish: advance blocked


def test_publish_phase_fails_closed_when_no_video(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_assets(tmp_path, monkeypatch, write_clips=False)  # no final.mp4, no clips
    calls: list[Any] = []
    _patch_export(monkeypatch, calls)

    result = asyncio.run(_director(tmp_path).run_phase(PID, "publish"))

    assert "error" in result
    assert "no video" in result["error"].lower()
    assert calls == []
    proj = _read(tmp_path)
    assert proj.phases["publish"].status == "failed"
    assert proj.current_phase == "audio"  # stuck before re_edit: advance blocked



def test_run_execute_completes_full_pipeline_to_done(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = _make_project(tmp_path)
    # init/trends/concept stay completed from the state-only era (concept is
    # still an honest stub in this PR), so the real run starts at script.
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
    runner_calls: list[Any] = []

    def runner(
        ctx: Any, project_id: str, data: Any, root: Any, *args: Any, **kwargs: Any
    ) -> None:
        runner_calls.append(project_id)
        _write_fake_clips(Path(root), project_id)

    monkeypatch.setattr(production, "_run_produce_runner", runner)

    async def fake_music(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"task_id": "music-fake", "status": "completed"}

    monkeypatch.setattr(Director, "generate_music", fake_music)

    async def fake_stitch(
        clips: list[Path], output: Path, **kwargs: Any
    ) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake-final")
        return {"output_path": str(output), "duration_seconds": 12.5}

    monkeypatch.setattr(stitch, "stitch_videos", fake_stitch)

    verify_calls: list[Path] = []

    async def fake_verify(clip: Path, **kwargs: Any) -> SimpleNamespace:
        verify_calls.append(clip)
        return SimpleNamespace(status="pass")

    monkeypatch.setattr(quality_gate, "verify_element", fake_verify)

    export_calls: list[str] = []

    async def fake_export(
        input_video: Path, platform: str, out_dir: Path, **kwargs: Any
    ) -> dict[str, Any]:
        export_calls.append(platform)
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{Path(input_video).stem}_{platform}{Path(input_video).suffix}"
        out.write_bytes(b"fake-export")
        return {"platform": platform, "output_path": str(out)}

    monkeypatch.setattr(export_platforms, "export_for_platform", fake_export)

    result = _invoke(tmp_path, ["run", pid, "--execute", "--yes"])

    assert result.exit_code == 0, result.output
    proj = _read(tmp_path, pid)
    for phase in PHASE_ORDER:
        assert proj.phases[phase].status == "completed", phase
    assert proj.current_phase == "done"
    assert proj.status == "completed"
    assert len(runner_calls) == 1
    assert verify_calls == _clip_paths(tmp_path, pid)
    assert export_calls == ["tiktok", "youtube_standard"]
    final = layout.resolve_media_root(tmp_path, pid, "videos") / "final.mp4"
    assert final.is_file()
    export_dir = layout.resolve_project_dir(tmp_path, pid) / "export"
    assert (export_dir / "final_tiktok.mp4").is_file()
    assert (export_dir / "final_youtube_standard.mp4").is_file()

