"""Issue #126: production monitor — live per-shot progress, gate scores,
provider health for long produce runs.

A 6-hour produce run could only be watched by tailing
``docs/tmp/produce_progress.txt`` in a terminal. The monitor turns that
progress log into structured data the web app can render and stream:

- per-shot rows (OK / RETRY / FAIL / pending, attempts, backoff notes)
- the exact ``--only <id>`` resume command for every failed shot
- gate scores per completed take (from the durable ``gate_*.md`` reports)
- a provider-health strip (video-seconds today from #118 + last 503/429)
- a live tail pushed over the existing ``/ws/{project_id}`` socket
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient


def _project(root: Path, project_id: str = "proj-a") -> Path:
    proj = root / ".brandly" / project_id
    (proj / "docs" / "tmp").mkdir(parents=True, exist_ok=True)
    (proj / "project.json").write_text(
        json.dumps({"id": project_id, "name": "Monitor Fixture"}), encoding="utf-8"
    )
    return proj


def _shots(root: Path, ids: list[str], project_id: str = "proj-a") -> Path:
    shots = root / ".brandly" / project_id / "shots.json"
    shots.write_text(
        json.dumps([{"id": sid, "prompt": f"prompt for {sid}", "duration": 5} for sid in ids]),
        encoding="utf-8",
    )
    return shots


def _progress(root: Path, lines: list[str], stage: str = "produce",
              project_id: str = "proj-a") -> Path:
    proj = root / ".brandly" / project_id
    name = "produce_progress.txt" if stage == "produce" else "storyboard_progress.txt"
    path = proj / "docs" / "tmp" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


PRODUCE_LINES = [
    "2026-09-26T18:01:00Z s1 OK exit=0",
    "2026-09-26T18:02:00Z s2 RETRY exit=1 retry=1 backoff=30s 503 Service Unavailable",
    "2026-09-26T18:03:00Z s2 FAIL exit=1 retry=3 backoff=60s 429 too many requests",
]


class TestShotRows:
    def test_rows_merge_progress_with_shot_list(self, tmp_path: Path) -> None:
        from brandly_cli.web import monitor

        _project(tmp_path)
        _shots(tmp_path, ["s1", "s2", "s3"])
        _progress(tmp_path, PRODUCE_LINES)

        rows = monitor.shot_rows(tmp_path, "proj-a")
        by_id = {r["shot_id"]: r for r in rows}
        assert set(by_id) == {"s1", "s2", "s3"}

        assert by_id["s1"]["produce"] == "OK"
        assert by_id["s1"]["attempts"] == 1
        assert by_id["s1"]["retries"] == 0

        assert by_id["s2"]["produce"] == "FAIL"
        assert by_id["s2"]["retries"] == 3
        assert by_id["s2"]["backoff"] == "60s"
        assert by_id["s2"]["note"].strip() == "429 too many requests"
        assert by_id["s2"]["exit_code"] == 1

        assert by_id["s3"]["produce"] == "pending"
        assert by_id["s3"]["attempts"] == 0

    def test_failed_row_carries_resume_command(self, tmp_path: Path) -> None:
        from brandly_cli.web import monitor

        _project(tmp_path)
        _shots(tmp_path, ["s1", "s2"])
        _progress(tmp_path, PRODUCE_LINES[:1] + [PRODUCE_LINES[2]])

        rows = {r["shot_id"]: r for r in monitor.shot_rows(tmp_path, "proj-a")}
        assert rows["s2"]["resume_command"] == "brandly produce proj-a --only s2"
        assert "--only s2" in rows["s2"]["resume_command"]
        # An OK shot needs no resume command.
        assert rows["s1"].get("resume_command") in (None, "")

    def test_storyboard_stage_is_tracked_separately(self, tmp_path: Path) -> None:
        from brandly_cli.web import monitor

        _project(tmp_path)
        _shots(tmp_path, ["s1", "s2"])
        _progress(tmp_path, ["2026-09-26T18:01:00Z s1 OK exit=0"], stage="storyboard")

        rows = {r["shot_id"]: r for r in monitor.shot_rows(tmp_path, "proj-a")}
        assert rows["s1"]["storyboard"] == "OK"
        assert rows["s2"]["storyboard"] == "pending"
        assert rows["s1"]["produce"] == "pending"  # produce log untouched

    def test_missing_progress_file_reads_all_pending(self, tmp_path: Path) -> None:
        from brandly_cli.web import monitor

        _project(tmp_path)
        _shots(tmp_path, ["s1"])
        rows = monitor.shot_rows(tmp_path, "proj-a")
        assert rows[0]["produce"] == "pending"
        assert rows[0]["storyboard"] == "pending"


GATE_REPORT = """\
# Quality Gate Report — videos/scenes/Scene-01-Shot-1-1.mp4

**Status:** ✓ PASS (72/100)

Gate policy: pre-checks; artifact fail cutoffs distortion≥6, slop≥7, drift≥6

## Failures

- Severe slop detected (8/10)

## Warnings

- AI visual analysis skipped (AGNES_API_KEY not set) — offline pre-checks passed

_Written to .brandly/{project}/docs/tmp/_
"""


class TestGateScores:
    def test_gate_report_surfaces_score_and_issues(self, tmp_path: Path) -> None:
        from brandly_cli.web import monitor

        _project(tmp_path)
        report = tmp_path / ".brandly" / "proj-a" / "docs" / "tmp" / "gate_video_20260926-180000.md"
        report.write_text(GATE_REPORT, encoding="utf-8")

        gates = monitor.gate_scores(tmp_path, "proj-a")
        entry = gates["Scene-01-Shot-1-1"]
        assert entry["score"] == 72
        assert entry["status"] == "pass"
        assert entry["issues"] == ["Severe slop detected (8/10)"]

    def test_newer_report_wins_for_the_same_take(self, tmp_path: Path) -> None:
        from brandly_cli.web import monitor

        _project(tmp_path)
        docs = tmp_path / ".brandly" / "proj-a" / "docs" / "tmp"
        old = GATE_REPORT.replace("(72/100)", "(41/100)").replace("✓ PASS", "✗ FAIL")
        (docs / "gate_video_20260926-100000.md").write_text(old, encoding="utf-8")
        (docs / "gate_video_20260926-180000.md").write_text(GATE_REPORT, encoding="utf-8")

        gates = monitor.gate_scores(tmp_path, "proj-a")
        assert gates["Scene-01-Shot-1-1"]["score"] == 72

    def test_rows_carry_gate_score_for_completed_take(self, tmp_path: Path) -> None:
        from brandly_cli.web import monitor

        _project(tmp_path)
        _shots(tmp_path, ["Scene-01-Shot-1-1"])
        _progress(tmp_path, ["2026-09-26T18:01:00Z Scene-01-Shot-1-1 OK exit=0"])
        docs = tmp_path / ".brandly" / "proj-a" / "docs" / "tmp"
        (docs / "gate_video_20260926-180000.md").write_text(GATE_REPORT, encoding="utf-8")

        rows = monitor.shot_rows(tmp_path, "proj-a")
        assert rows[0]["gate"] == {
            "score": 72,
            "status": "pass",
            "issues": ["Severe slop detected (8/10)"],
        }


class TestProviderHealth:
    def test_video_seconds_today_from_generation_records(self, tmp_path: Path) -> None:
        from datetime import datetime, timezone

        from brandly_cli.web import monitor

        _project(tmp_path)
        now = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
        (tmp_path / ".brandly" / "proj-a" / "docs" / "tmp" / "video_1.json").write_text(
            json.dumps(
                {
                    "asset_type": "video",
                    "generated_at": now.isoformat(),
                    "metadata": {"duration": 42},
                }
            ),
            encoding="utf-8",
        )

        health = monitor.provider_health(tmp_path, "proj-a")
        assert health["video_seconds_today"] == 42
        assert health["quota_seconds"] > 0

    def test_last_error_is_surfaced_with_http_status(self, tmp_path: Path) -> None:
        from brandly_cli.web import monitor

        _project(tmp_path)
        _shots(tmp_path, ["s1", "s2"])
        _progress(tmp_path, PRODUCE_LINES)

        health = monitor.provider_health(tmp_path, "proj-a")
        last = health["last_error"]
        assert last["shot_id"] == "s2"
        assert last["http_status"] == 429
        assert "too many requests" in last["note"]
        # 429 on screen = rate storm, not "quota exhausted" and not "down".
        assert health["status"] == "rate_limit"

    def test_status_is_failed_without_http_marker(self, tmp_path: Path) -> None:
        from brandly_cli.web import monitor

        _project(tmp_path)
        _shots(tmp_path, ["s1"])
        _progress(tmp_path, ["2026-09-26T18:03:00Z s1 FAIL exit=1 clip missing"])

        health = monitor.provider_health(tmp_path, "proj-a")
        assert health["status"] == "failed"
        assert health["last_error"]["http_status"] in (None, 0)

    def test_status_ok_when_no_failures(self, tmp_path: Path) -> None:
        from brandly_cli.web import monitor

        _project(tmp_path)
        _shots(tmp_path, ["s1"])
        _progress(tmp_path, ["2026-09-26T18:01:00Z s1 OK exit=0"])

        health = monitor.provider_health(tmp_path, "proj-a")
        assert health["status"] == "ok"
        assert health["last_error"] is None


class TestTail:
    def test_tail_returns_only_new_lines_after_offset(self, tmp_path: Path) -> None:
        from brandly_cli.web import monitor

        _project(tmp_path)
        path = _progress(tmp_path, PRODUCE_LINES[:2])

        first = monitor.tail(tmp_path, "proj-a", "produce", 0)
        assert first["lines"] == PRODUCE_LINES[:2]
        assert first["offset"] == 2

        path.write_text("\n".join(PRODUCE_LINES) + "\n", encoding="utf-8")
        second = monitor.tail(tmp_path, "proj-a", "produce", first["offset"])
        assert second["lines"] == [PRODUCE_LINES[2]]
        assert second["offset"] == 3

    def test_tail_reset_when_the_file_shrinks(self, tmp_path: Path) -> None:
        from brandly_cli.web import monitor

        _project(tmp_path)
        path = _progress(tmp_path, PRODUCE_LINES)
        # A resumed run rewrites the log from scratch.
        path.write_text(PRODUCE_LINES[0] + "\n", encoding="utf-8")

        result = monitor.tail(tmp_path, "proj-a", "produce", 3)
        assert result["lines"] == [PRODUCE_LINES[0]]
        assert result["offset"] == 1


class TestMonitorRoutes:
    def test_monitor_snapshot_shape(self, tmp_path: Path) -> None:
        from brandly_cli.web.server import create_app

        _project(tmp_path)
        _shots(tmp_path, ["s1"])
        _progress(tmp_path, PRODUCE_LINES[:1])

        app = create_app(root=str(tmp_path))
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        res = client.get("/api/projects/proj-a/monitor")
        assert res.status_code == 200
        data = res.json()
        assert data["project_id"] == "proj-a"
        assert [r["shot_id"] for r in data["shots"]] == ["s1"]
        assert "provider" in data and "shots" in data
        assert data["provider"]["quota_seconds"] > 0

    def test_monitor_unknown_project_is_404(self, tmp_path: Path) -> None:
        from brandly_cli.web.server import create_app

        _project(tmp_path)
        app = create_app(root=str(tmp_path))
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        assert client.get("/api/projects/nope/monitor").status_code == 404

    def test_monitor_tail_route_returns_new_lines(self, tmp_path: Path) -> None:
        from brandly_cli.web.server import create_app

        _project(tmp_path)
        _progress(tmp_path, PRODUCE_LINES)

        app = create_app(root=str(tmp_path))
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        res = client.get("/api/projects/proj-a/monitor/tail?stage=produce&offset=1")
        assert res.status_code == 200
        data = res.json()
        assert data["lines"] == [PRODUCE_LINES[1], PRODUCE_LINES[2]]
        assert data["offset"] == 3


class TestLiveTailWebsocket:
    def test_new_progress_line_is_pushed_over_the_socket(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from brandly_cli.web import monitor
        from brandly_cli.web.server import create_app

        monkeypatch.setattr(monitor, "TAIL_INTERVAL", 0.02)

        _project(tmp_path)
        _shots(tmp_path, ["s1", "s9"])
        path = _progress(tmp_path, PRODUCE_LINES[:1])

        app = create_app(root=str(tmp_path))
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        with client.websocket_connect(
            # LocalGuardMiddleware only admits loopback Host/Origin, exactly as
            # a browser on 127.0.0.1 sends them (TestClient's default
            # "testserver" host would be rejected with 1008).
            "/ws/proj-a",
            headers={"host": "127.0.0.1:8765", "origin": "http://127.0.0.1:8765"},
        ) as ws:
            # The pre-existing line is history (already in the snapshot);
            # only the line appended after connect must stream in.
            path.write_text(
                "\n".join(PRODUCE_LINES[:1] + ["2026-09-26T19:00:00Z s9 OK exit=0"]) + "\n",
                encoding="utf-8",
            )
            msg = ws.receive_json()

        assert msg["type"] == "monitor_tail"
        assert msg["stage"] == "produce"
        assert msg["lines"] == ["2026-09-26T19:00:00Z s9 OK exit=0"]

        # The pushed line is exactly what a refreshed snapshot would show.
        rows = {r["shot_id"]: r for r in monitor.shot_rows(tmp_path, "proj-a")}
        assert rows["s9"]["produce"] == "OK"
