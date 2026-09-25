"""G8 PR 1 (issue #99, DEV-G8-001/002/003 confirmed): metrics import +
analyze source labelling.

Anti-drift rules under test:
* ingested metrics live project-local (``.brandly/<project>/metrics/``),
  never in the user config store (DEV-G8-001);
* import validation is deterministic and fail-closed (unknown platform,
  malformed row, out-of-range value);
* ``analyze`` prefers the latest ingest over heuristics and always labels
  the source in its output (DEV-G8-002, G5 scope-truth rule);
* no network, no credentials anywhere in this PR (G8 PR 2 territory);
* capability row goes ``partial`` → ``supported`` (YouTube Analytics API
  stays a planned next step, G8 PR 2).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli import capabilities as caps_mod
from brandly_cli import metrics as m
from brandly_cli.analyzer import analyze_video
from brandly_cli.cli import cli

CSV = "date,views,likes,watch_time_seconds,ctr_pct\n"


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Root with one project; returns the root (ROOT env shape, test_publish)."""
    monkeypatch.setenv("BRANDLY_CONFIG_DIR", str(tmp_path / "config"))
    proj_dir = tmp_path / ".brandly" / "test-proj"
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "project.json").write_text('{"id": "test-proj", "name": "t"}')
    return tmp_path


class TestImport:
    def test_csv_writes_one_snapshot_per_date(self, tmp_path: Path) -> None:
        csv = tmp_path / "stats.csv"
        csv.write_text(CSV + "2026-09-01,100,10,5000,4.5\n2026-09-02,200,20,9000,5.0\n")
        proj = tmp_path / ".brandly" / "p"
        proj.mkdir(parents=True, exist_ok=True)
        written = m.import_metrics(csv, "youtube", proj)
        assert len(written) == 2
        snap = json.loads((proj / "metrics" / "youtube-2026-09-01.json").read_text())
        assert snap["platform"] == "youtube"
        assert snap["schema"] == m.METRICS_SCHEMA_VERSION
        assert snap["rows"][0]["views"] == 100

    def test_json_import(self, tmp_path: Path) -> None:
        src = tmp_path / "stats.json"
        src.write_text(
            json.dumps(
                [
                    {
                        "date": "2026-09-01",
                        "views": 10,
                        "likes": 1,
                        "watch_time_seconds": 60,
                        "ctr_pct": 2.0,
                    }
                ]
            )
        )
        proj = tmp_path / ".brandly" / "p"
        proj.mkdir(parents=True, exist_ok=True)
        written = m.import_metrics(src, "youtube", proj)
        assert len(written) == 1
        assert written[0].name == "youtube-2026-09-01.json"

    def test_unknown_platform_fail_closed(self, tmp_path: Path) -> None:
        csv = tmp_path / "s.csv"
        csv.write_text(CSV + "2026-09-01,10,1,60,1.0\n")
        proj = tmp_path / ".brandly" / "p"
        proj.mkdir(parents=True, exist_ok=True)
        with pytest.raises(ValueError):
            m.import_metrics(csv, "tumblr", proj)

    def test_malformed_row_fail_closed(self, tmp_path: Path) -> None:
        for bad in (
            "2026-09-01,-5,1,60,1.0\n",  # negative views
            "2026-09-01,10,1,60,150.0\n",  # ctr_pct out of range
            "09/01/2026,10,1,60,1.0\n",  # non-ISO date
            "2026-09-01,ten,1,60,1.0\n",  # non-numeric
        ):
            csv = tmp_path / "bad.csv"
            csv.write_text(CSV + bad)
            proj = tmp_path / ".brandly" / "p"
            proj.mkdir(parents=True, exist_ok=True)
            with pytest.raises(ValueError):
                m.import_metrics(csv, "youtube", proj)

    def test_ingest_stays_in_project_dir(self, project: Path) -> None:
        csv = project / "s.csv"
        csv.write_text(CSV + "2026-09-01,10,1,60,1.0\n")
        m.import_metrics(csv, "youtube", project / ".brandly" / "test-proj")
        # Nothing but project.json may sit in the project dir's parent layout;
        # the ingest never writes outside `.brandly/<project>/metrics/`.
        assert not (project / "metrics").exists()
        assert not (project / "s.json").exists()
        proj_root_files = [p.name for p in (project / ".brandly" / "test-proj").iterdir()]
        assert "s.json" not in proj_root_files


class TestLatestIngest:
    def test_latest_by_date_wins(self, tmp_path: Path) -> None:
        proj = tmp_path / ".brandly" / "p"
        proj.mkdir(parents=True, exist_ok=True)
        csv = tmp_path / "s.csv"
        csv.write_text(CSV + "2026-09-01,10,1,60,1.0\n2026-09-03,20,2,90,2.0\n")
        m.import_metrics(csv, "youtube", proj)
        latest = m.latest_ingest(proj, "youtube")
        assert latest is not None and latest.name == "youtube-2026-09-03.json"

    def test_latest_ingest_missing_is_none(self, tmp_path: Path) -> None:
        proj = tmp_path / ".brandly" / "p"
        proj.mkdir(parents=True, exist_ok=True)
        assert m.latest_ingest(proj, "youtube") is None

    def test_latest_snapshot_payload(self, tmp_path: Path) -> None:
        proj = tmp_path / ".brandly" / "p"
        proj.mkdir(parents=True, exist_ok=True)
        csv = tmp_path / "s.csv"
        csv.write_text(CSV + "2026-09-03,20,2,90,2.0\n")
        m.import_metrics(csv, "youtube", proj)
        snap = m.latest_snapshot(proj, "youtube")
        assert snap["date"] == "2026-09-03"
        assert snap["rows"][0]["ctr_pct"] == 2.0


class TestMetricsCli:
    def test_import_command_writes_project_local(self, project: Path) -> None:
        src = project / "s.csv"
        src.write_text(CSV + "2026-09-01,10,1,60,1.0\n")
        runner = CliRunner(env={"ROOT": str(project)})
        result = runner.invoke(
            cli,
            [
                "metrics",
                "import",
                str(src),
                "--platform",
                "youtube",
                "--project",
                "test-proj",
            ],
        )
        assert result.exit_code == 0, result.output
        assert (
            project / ".brandly" / "test-proj" / "metrics" / "youtube-2026-09-01.json"
        ).is_file()

    def test_import_unknown_platform_exits_1(self, project: Path) -> None:
        src = project / "s.csv"
        src.write_text(CSV + "2026-09-01,10,1,60,1.0\n")
        runner = CliRunner(env={"ROOT": str(project)})
        result = runner.invoke(
            cli,
            [
                "metrics",
                "import",
                str(src),
                "--platform",
                "myspace",
                "--project",
                "test-proj",
            ],
        )
        assert result.exit_code != 0

    def test_show_lists_latest_per_platform(self, project: Path) -> None:
        src = project / "s.csv"
        src.write_text(CSV + "2026-09-01,10,1,60,1.0\n2026-09-03,20,2,90,2.0\n")
        m.import_metrics(src, "youtube", project / ".brandly" / "test-proj")
        runner = CliRunner(env={"ROOT": str(project)})
        result = runner.invoke(
            cli,
            [
                "metrics",
                "show",
                "--project",
                "test-proj",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        doc = json.loads(result.output)
        assert doc["youtube"]["date"] == "2026-09-03"


class TestAnalyzeSourceLabelling:
    """DEV-G8-002: ingest beats heuristics; output always labels the source."""

    @staticmethod
    def _ingest(root: Path, ctr: float = 6.0) -> None:
        proj = root / ".brandly" / "test-proj"
        proj.mkdir(parents=True, exist_ok=True)
        src = root / "s.csv"
        src.write_text(CSV + f"2026-09-03,1000,50,45000,{ctr}\n")
        m.import_metrics(src, "youtube", proj)

    def test_heuristic_source_when_no_ingest(self, project: Path) -> None:
        video = project / "v.mp4"
        video.write_bytes(b"\x00\x00")
        result = asyncio.run(analyze_video(video, root=project))
        assert "error" not in result
        assert result["source"] == "heuristic"

    def test_ingested_source_preferred(self, project: Path) -> None:
        video = project / "v.mp4"
        video.write_bytes(b"\x00\x00")
        self._ingest(project, ctr=6.0)
        result = asyncio.run(analyze_video(video, root=project))
        assert result["source"] == "ingested"
        assert result["metadata"]["metrics"]["ctr_pct"] == 6.0
        # 6% CTR maps to a 6/10 ctr row (deterministic blend rule)
        assert result["ctr_prediction"] == 6


class TestCapabilityRow:
    def test_metrics_ingest_supported_with_metrics_command(self) -> None:
        row = next(c for c in caps_mod.CAPABILITIES if c["id"] == "metrics_ingest")
        assert row["status"] == "supported"
        assert row.get("command") == "metrics"
