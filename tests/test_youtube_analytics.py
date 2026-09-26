"""G8 PR 2 (issue #99, DEV-G8-003 confirmed): YouTube Analytics API adapter
(credential-gated, G6 pattern, dry-run-first).

Anti-drift rules under test:
* dry-run renders the exact request and never touches the network;
* live ingest fails closed without a stored credential, and the message
  names the exact `brandly config set youtube:analytics <token>` command;
* live ingest writes the SAME project-local snapshot files as PR 1;
* no secret material lands in a project artifact (tree scan);
* TikTok/IG analytics stay planned (capability note).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli import capabilities as caps_mod
from brandly_cli import youtube_analytics as ya
from brandly_cli.cli import cli


REPORT = {
    "reports": [
        {
            "header": {
                "dimensions": ["day"],
                "columns": [
                    {"name": "views"},
                    {"name": "likes"},
                    {"name": "estimatedWatchTime"},
                    {"name": "clickThroughRate"},
                ],
            },
            "rows": [
                ["2026-09-01", 100, 10, 5000, 0.045],
                ["2026-09-02", 200, 20, 9000, 0.05],
            ],
        }
    ]
}


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("BRANDLY_CONFIG_DIR", str(tmp_path / "config"))
    proj_dir = tmp_path / ".brandly" / "test-proj"
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "project.json").write_text('{"id": "test-proj", "name": "t"}')
    return tmp_path


class TestRequestBuilder:
    def test_build_request_snapshot(self) -> None:
        req = ya.YouTubeAnalyticsAdapter().build_request("PROP", days=28)
        assert req["platform"] == "youtube"
        assert req["method"] == "GET"
        assert req["endpoint"].endswith("/properties/PROP/reports:query")
        assert req["query_params"]["metrics"] == ya.ANALYTICS_METRICS

    def test_rows_from_report_maps_to_schema(self) -> None:
        rows = ya.rows_from_report(REPORT)
        assert len(rows) == 2
        assert rows[0] == {
            "date": "2026-09-01",
            "views": 100,
            "likes": 10,
            "watch_time_seconds": 5000,
            "ctr_pct": 4.5,
        }
        # CTR arrives as a fraction from the API; the schema stores percent.

    def test_rows_from_report_empty(self) -> None:
        assert ya.rows_from_report({"reports": []}) == []


class TestIngestCli:
    def test_dry_run_renders_request_without_network(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []
        monkeypatch.setattr(
            ya.urllib.request, "urlopen",
            lambda *a, **k: calls.append("net") or None,
        )
        result = CliRunner().invoke(cli, [
            "metrics", "ingest", "--platform", "youtube",
            "--property", "PROP", "--dry-run", "--json",
            "--root", str(project),
        ])
        assert result.exit_code == 0, result.output
        doc = json.loads(result.output)
        assert doc["dry_run"] is True
        assert doc["request"]["endpoint"].endswith("/properties/PROP/reports:query")
        assert not calls, "dry-run must not touch the network"

    def test_live_without_credentials_fails_closed(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        result = CliRunner().invoke(cli, [
            "metrics", "ingest", "--platform", "youtube",
            "--property", "PROP",
            "--root", str(project),
        ])
        assert result.exit_code != 0
        assert "credential" in result.output.lower()
        assert "brandly config set youtube:analytics" in result.output

    def test_live_with_mocked_http_writes_project_local(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import brandly_cli.config_store as cs

        monkeypatch.setattr(cs, "get_credential", lambda name: "tok" if name == "youtube:analytics" else None)

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps(REPORT).encode("utf-8")

        sent: list = []

        def fake_urlopen(req, timeout=None):
            sent.append(req)
            return _Resp()

        monkeypatch.setattr(ya.urllib.request, "urlopen", fake_urlopen)
        result = CliRunner().invoke(cli, [
            "metrics", "ingest", "--platform", "youtube",
            "--property", "PROP", "--project", "test-proj",
            "--root", str(project),
        ])
        assert result.exit_code == 0, result.output
        snap = project / ".brandly" / "test-proj" / "metrics" / "youtube-2026-09-01.json"
        assert snap.is_file()
        assert sent, "live ingest must send the request"
        # anti-drift: no credential material in the project tree
        for p in (project / ".brandly" / "test-proj").rglob("*"):
            if p.is_file():
                assert "tok" not in p.read_text(encoding="utf-8", errors="ignore")

    def test_missing_property_fails_closed(self, project: Path) -> None:
        result = CliRunner().invoke(cli, [
            "metrics", "ingest", "--platform", "youtube", "--dry-run",
            "--root", str(project),
        ])
        assert result.exit_code != 0
        assert "property" in result.output.lower()


class TestCapabilityNote:
    def test_metrics_note_keeps_tiktok_ig_planned(self) -> None:
        row = next(c for c in caps_mod.CAPABILITIES if c["id"] == "metrics_ingest")
        assert row["status"] == "supported"
        assert "tiktok/ig" in row["note"].lower() or "tiktok" in row["note"].lower()
