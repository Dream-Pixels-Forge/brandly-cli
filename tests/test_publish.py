"""G6 (decision record DEV-G6-001): dry-run-first publish path.

Anti-drift rules under test:
* dry-run renders the exact request payload and never touches the network;
* live publishing fails closed (non-zero exit, actionable message) when
  credentials are missing;
* no secret material ever lands in a project artifact (tree scan);
* credentials live in the user config store — never in `.env` sprawl.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli import publish as pub
from brandly_cli.cli import cli


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal project tree with one exported platform video."""
    monkeypatch.setenv("BRANDLY_CONFIG_DIR", str(tmp_path / "config"))
    proj_dir = tmp_path / ".brandly" / "test-proj"
    proj_dir.mkdir(parents=True)
    (proj_dir / "project.json").write_text('{"id": "test-proj", "name": "t"}')
    export_dir = proj_dir / "export"
    export_dir.mkdir()
    (export_dir / "master_youtube.mp4").write_bytes(b"fake-video-bytes")
    return tmp_path


class TestAdapterPayload:
    def test_youtube_payload_snapshot(self, tmp_path: Path) -> None:
        video = tmp_path / "master.mp4"
        video.write_bytes(b"fake")
        payload = pub.youtube_payload(video, title="T", description="D",
                                     schedule_iso="2026-10-01T09:00:00+00:00")
        assert payload["platform"] == "youtube"
        assert payload["method"] == "POST"
        assert payload["endpoint"] == "https://www.googleapis.com/upload/youtube/v3/videos"
        assert payload["request_body"]["snippet"]["title"] == "T"
        assert payload["request_body"]["status"]["privacyStatus"] == "private"
        assert payload["request_body"]["status"]["publishAt"] == "2026-10-01T09:00:00Z"
        assert payload["video_file"] == str(video)

    def test_youtube_payload_unscheduled(self, tmp_path: Path) -> None:
        video = tmp_path / "master.mp4"
        video.write_bytes(b"fake")
        payload = pub.youtube_payload(video, title="T", description="D")
        assert "publishAt" not in payload["request_body"]["status"]

    def test_unknown_platform_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(KeyError):
            pub.get_adapter("tumblr")


class TestPublishCli:
    def test_dry_run_json_renders_payload_without_network(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []
        monkeypatch.setattr(pub.urllib.request, "urlopen",
                            lambda *a, **k: calls.append("net") or None)
        runner = CliRunner(env={"ROOT": str(project)})
        result = runner.invoke(
            cli,
            ["publish", "test-proj", "--platform", "youtube", "--dry-run", "--json"],
        )
        assert result.exit_code == 0, result.output
        doc = json.loads(result.output)
        assert doc["dry_run"] is True
        assert doc["payload"]["platform"] == "youtube"
        assert not calls, "dry-run must not touch the network"

    def test_live_without_credentials_fails_closed(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        runner = CliRunner(env={"ROOT": str(project)})
        result = runner.invoke(
            cli,
            ["publish", "test-proj", "--platform", "youtube"],
        )
        assert result.exit_code != 0
        assert "credential" in result.output.lower()
        assert "brandly config set" in result.output

    def test_no_secrets_land_in_project_tree(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from brandly_cli import config_store

        secret = "yt-secret-token-xyz-123"
        config_store.set_credential("youtube", secret)
        runner = CliRunner(env={"ROOT": str(project)})
        result = runner.invoke(
            cli,
            ["publish", "test-proj", "--platform", "youtube", "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        # Scan the whole project tree: the secret must appear nowhere in it.
        proj_tree = project / ".brandly"
        for f in proj_tree.rglob("*"):
            if f.is_file():
                assert secret not in f.read_text(encoding="utf-8", errors="ignore"), f
        # The credential itself lives in the user config dir, not the project.
        assert (project / "config" / "credentials.json").is_file()

