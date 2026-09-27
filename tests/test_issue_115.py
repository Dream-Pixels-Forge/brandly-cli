"""Issue #115: produce --continue-on-fail — one stuck shot must not block the
whole shot list.

Default behaviour is unchanged (stop on first terminal failure). With
--continue-on-fail the runner records FAIL, prints a CONTINUE notice, runs the
remaining shots, then prints a summary with --only re-run commands and exits 1.
"""

from __future__ import annotations

from pathlib import Path

from brandly_cli import shot_runner


def _shots(ids: list[str]) -> list[shot_runner.Shot]:
    return [
        shot_runner.Shot(
            id=sid, act="", style="cinematic", folder="scenes",
            prompt=f"p {sid}", duration=5,
        )
        for sid in ids
    ]


def _config(tmp_path: Path, shots, generate_one, continue_on_fail: bool) -> shot_runner.RunnerConfig:  # type: ignore[no-untyped-def]
    scenes = tmp_path / "videos" / "scenes"
    scenes.mkdir(parents=True, exist_ok=True)
    progress = shot_runner.ProgressLog(tmp_path / "docs" / "tmp" / "produce_progress.txt")
    return shot_runner.RunnerConfig(
        shots=shots,
        generate_one=generate_one,
        scenes_dir=scenes,
        progress=progress,
        interval=0.0,
        continue_on_fail=continue_on_fail,
    )


def _gen(result_for: dict, default: bool = True):  # type: ignore[no-untyped-def]
    def generate_one(shot):  # type: ignore[no-untyped-def]
        ok = result_for.get(shot.id, default)
        if ok:
            return (True, 0, "")
        return (False, 1, "provider 503")
    return generate_one


def test_continue_on_fail_runs_all_shots(tmp_path: Path) -> None:
    shots = _shots(["s1", "s2", "s3"])
    config = _config(tmp_path, shots, _gen({"s2": False}), continue_on_fail=True)
    messages: list[str] = []
    config.say = messages.append
    rc = shot_runner.run_shots(config)
    assert rc == 1
    # s1 and s3 completed; s2 failed but did not stop the run
    done = config.progress.completed_ids(s.id for s in shots)
    assert done == {"s1", "s3"}
    assert any("s2 FAIL" in m for m in messages)
    assert any("CONTINUE" in m and "s2" in m for m in messages)
    # summary lists the failed shot with a re-run command
    assert any("--only s2" in m for m in messages)


def test_continue_on_fail_all_ok_returns_0(tmp_path: Path) -> None:
    shots = _shots(["s1", "s2"])
    config = _config(tmp_path, shots, _gen({}), continue_on_fail=True)
    assert shot_runner.run_shots(config) == 0
    done = config.progress.completed_ids(s.id for s in shots)
    assert done == {"s1", "s2"}


def test_default_still_stops_on_first_failure(tmp_path: Path) -> None:
    shots = _shots(["s1", "s2", "s3"])
    config = _config(tmp_path, shots, _gen({"s2": False}), continue_on_fail=False)
    messages: list[str] = []
    config.say = messages.append
    assert shot_runner.run_shots(config) == 1
    done = config.progress.completed_ids(s.id for s in shots)
    # s3 never ran: the run stopped at s2
    assert done == {"s1"}
    assert not any("s3 OK" in m for m in messages)


def test_multiple_failures_all_listed(tmp_path: Path) -> None:
    shots = _shots(["s1", "s2", "s3", "s4"])
    config = _config(tmp_path, shots, _gen({"s2": False, "s3": False}), continue_on_fail=True)
    messages: list[str] = []
    config.say = messages.append
    assert shot_runner.run_shots(config) == 1
    assert any("--only s2" in m for m in messages)
    assert any("--only s3" in m for m in messages)
    done = config.progress.completed_ids(s.id for s in shots)
    assert done == {"s1", "s4"}
