"""Issue #114: durable in-flight video-task ledger + job-resume --sweep.

A crash between create and download previously stranded the server-side
task (and its spent quota) with no recovery handle. The video command now
persists the task id before polling and clears it on terminal states;
job-resume --sweep adopts everything left in the ledger.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner

from brandly_cli import inflight
from brandly_cli.cli import cli

PROJECT = "inflight-proj"


def test_add_remove_roundtrip(tmp_path: Path) -> None:
    inflight.add(tmp_path, PROJECT, "task_1", note="scene=1 shot=1")
    inflight.add(tmp_path, PROJECT, "task_2")
    assert [e["video_id"] for e in inflight.entries(tmp_path, PROJECT)] == ["task_1", "task_2"]
    inflight.remove(tmp_path, PROJECT, "task_1")
    assert [e["video_id"] for e in inflight.entries(tmp_path, PROJECT)] == ["task_2"]


def test_add_dedupes_by_video_id(tmp_path: Path) -> None:
    inflight.add(tmp_path, PROJECT, "task_1")
    inflight.add(tmp_path, PROJECT, "task_1")
    assert len(inflight.entries(tmp_path, PROJECT)) == 1


def test_corrupted_ledger_degrades_to_empty(tmp_path: Path) -> None:
    path = tmp_path / ".brandly" / PROJECT / "docs" / "tmp" / "inflight_jobs.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    assert inflight.entries(tmp_path, PROJECT) == []


def test_missing_ledger_is_empty(tmp_path: Path) -> None:
    assert inflight.entries(tmp_path, PROJECT) == []


def test_sweep_resumes_completed_and_clears_failed(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / ".brandly" / PROJECT / "docs" / "tmp").mkdir(parents=True)
    inflight.add(tmp_path, PROJECT, "task_done", note="s=1")
    inflight.add(tmp_path, PROJECT, "task_failed")
    inflight.add(tmp_path, PROJECT, "task_running")

    statuses = {
        "task_done": {"status": "completed", "progress": 100, "url": "https://x/v.mp4"},
        "task_failed": {"status": "failed", "progress": 0, "error": "boom"},
        "task_running": {"status": "queued", "progress": 10},
    }

    async def fake_status(video_id, model_name=None):  # type: ignore[no-untyped-def]
        return statuses[video_id]

    saved = MagicMock(return_value=tmp_path / "v.mp4")

    monkeypatch.setattr("brandly_cli.agnes_client.get_video_status", fake_status)
    monkeypatch.setattr("brandly_cli.cmd.providers._save_artifact", saved)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["job-resume", "--sweep", PROJECT],
        env={"ROOT": str(tmp_path)},
    )
    assert result.exit_code == 0, result.output
    assert "task_done" in result.output and "task_failed" in result.output
    assert "task_running" in result.output
    # completed -> downloaded + removed; failed -> removed; running -> kept
    left = [e["video_id"] for e in inflight.entries(tmp_path, PROJECT)]
    assert left == ["task_running"]
