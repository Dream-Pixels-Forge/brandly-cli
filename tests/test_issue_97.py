"""Issue #97: publish/schedule path to TikTok/IG/YouTube (G6, decision-gated).

G6 PR 1 shipped the YouTube dry-run + credential-gated live upload; this
closes the remaining adapters on the same ``Adapter`` interface, keeping the
anti-drift rules under test:

* dry-run renders the exact request payload and never touches the network;
* live posting fails closed (non-zero exit, actionable message) when
  credentials are missing;
* scheduling is only offered where the platform actually supports it
  (YouTube ``publishAt``; TikTok direct-post has no schedule — fail closed);
* Instagram requires a publicly reachable video URL — fail closed without one.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli import capabilities as caps_mod
from brandly_cli import publish as pub
from brandly_cli.cli import cli


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("BRANDLY_CONFIG_DIR", str(tmp_path / "config"))
    proj_dir = tmp_path / ".brandly" / "test-proj"
    proj_dir.mkdir(parents=True)
    (proj_dir / "project.json").write_text('{"id": "test-proj", "name": "t"}')
    export_dir = proj_dir / "export"
    export_dir.mkdir()
    (export_dir / "master_tiktok.mp4").write_bytes(b"fake-video-bytes")
    (export_dir / "master_instagram.mp4").write_bytes(b"fake-video-bytes")
    return tmp_path


class TestTikTokAdapter:
    def test_payload_snapshot(self, tmp_path: Path) -> None:
        video = tmp_path / "master.mp4"
        video.write_bytes(b"fake-video-bytes")
        payload = pub.get_adapter("tiktok").build_payload(
            video, title="T", description="D", schedule_iso=None
        )
        assert payload["platform"] == "tiktok"
        assert payload["method"] == "POST"
        assert payload["endpoint"] == "https://open.tiktokapis.com/v2/post/publish/video/init/"
        # TikTok's caption is a single field: title + description fold in.
        assert payload["request_body"]["post_info"]["title"] == "T\n\nD"
        # Private default: only the owner can see it until they publish.
        assert payload["request_body"]["post_info"]["privacy_level"] == "SELF_ONLY"
        assert payload["request_body"]["source_info"]["source"] == "FILE_UPLOAD"
        assert payload["request_body"]["source_info"]["video_size"] == len(b"fake-video-bytes")
        assert payload["video_file"] == str(video)

    def test_schedule_is_rejected_fail_closed(self, tmp_path: Path) -> None:
        video = tmp_path / "master.mp4"
        video.write_bytes(b"fake")
        with pytest.raises(ValueError) as excinfo:
            pub.get_adapter("tiktok").build_payload(
                video, title="T", description="D",
                schedule_iso="2026-10-01T09:00:00+00:00",
            )
        # Actionable: points at the private-post alternative.
        assert "private" in str(excinfo.value)

    def test_chunks_for_files_bigger_than_one_chunk(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        video = tmp_path / "master.mp4"
        video.write_bytes(b"0123456789")  # 10 bytes
        monkeypatch.setattr(pub, "TIKTOK_MAX_CHUNK_BYTES", 4)
        payload = pub.get_adapter("tiktok").build_payload(
            video, title="T", description="D", schedule_iso=None
        )
        source = payload["request_body"]["source_info"]
        assert source["chunk_size"] == 4
        assert source["total_chunk_count"] == math.ceil(10 / 4)


class TestInstagramAdapter:
    def test_payload_snapshot(self, tmp_path: Path) -> None:
        video = tmp_path / "master.mp4"
        video.write_bytes(b"fake")
        payload = pub.get_adapter("instagram").build_payload(
            video, title="T", description="D", schedule_iso=None,
            video_url="https://cdn.example/v.mp4",
        )
        assert payload["platform"] == "instagram"
        assert payload["method"] == "POST"
        assert payload["endpoint"] == "https://graph.facebook.com/v21.0/me/media"
        assert payload["request_body"]["media_type"] == "REELS"
        assert payload["request_body"]["video_url"] == "https://cdn.example/v.mp4"
        assert payload["request_body"]["caption"] == "T\n\nD"
        # The Graph API is a two-step flow: container create -> publish.
        assert payload["follow_up"]["endpoint"] == "https://graph.facebook.com/v21.0/me/media_publish"

    def test_without_video_url_fails_closed(self, tmp_path: Path) -> None:
        video = tmp_path / "master.mp4"
        video.write_bytes(b"fake")
        with pytest.raises(ValueError) as excinfo:
            pub.get_adapter("instagram").build_payload(
                video, title="T", description="D", schedule_iso=None,
            )
        # Actionable: points at --video-url and the share path.
        assert "--video-url" in str(excinfo.value)
        assert "share" in str(excinfo.value)


class TestLiveExecution:
    def test_tiktok_posts_the_init_payload_with_the_credential(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        import urllib.request

        video = tmp_path / "master.mp4"
        video.write_bytes(b"fake")
        payload = pub.get_adapter("tiktok").build_payload(
            video, title="T", description="D", schedule_iso=None
        )

        seen: dict = {}

        def fake_urlopen(req, timeout=None):  # type: ignore[no-untyped-def]
            seen["url"] = req.full_url
            seen["auth"] = req.get_header("Authorization")
            seen["body"] = json.loads(req.data.decode("utf-8"))

            class Resp:
                def __enter__(self):  # type: ignore[no-untyped-def]
                    return self

                def __exit__(self, *args: object) -> None:
                    return None

                def read(self) -> bytes:
                    return json.dumps({"data": {"publish_id": "tt-1"}}).encode("utf-8")

            return Resp()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        result = pub.get_adapter("tiktok").execute(payload, token="tt-token")

        assert seen["url"] == payload["endpoint"]
        assert seen["auth"] == "Bearer tt-token"
        assert seen["body"]["post_info"]["title"] == "T\n\nD"
        assert result["data"]["publish_id"] == "tt-1"


    def test_instagram_creates_then_publishes_the_container(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        import urllib.request

        video = tmp_path / "master.mp4"
        video.write_bytes(b"fake")
        payload = pub.get_adapter("instagram").build_payload(
            video, title="T", description="D", schedule_iso=None,
            video_url="https://cdn.example/v.mp4",
        )

        calls: list[tuple[str, dict]] = []

        def fake_urlopen(req, timeout=None):  # type: ignore[no-untyped-def]
            body = json.loads(req.data.decode("utf-8"))
            calls.append((req.full_url, body))

            class Resp:
                def __enter__(self):  # type: ignore[no-untyped-def]
                    return self

                def __exit__(self, *args: object) -> None:
                    return None

                def read(self) -> bytes:
                    if "media_publish" in req.full_url:
                        return json.dumps({"id": "ig-post-1"}).encode("utf-8")
                    return json.dumps({"id": "ig-container-1"}).encode("utf-8")

            return Resp()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        result = pub.get_adapter("instagram").execute(payload, token="ig-token")

        assert [url for url, _ in calls] == [
            payload["endpoint"],
            payload["follow_up"]["endpoint"],
        ]
        # The publish step reuses the container id from the create response.
        assert calls[1][1]["creation_id"] == "ig-container-1"
        assert result["id"] == "ig-post-1"


class TestPublishCli:
    def test_tiktok_dry_run_posts_nothing(self, project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["publish", "test-proj", "--platform", "tiktok", "--dry-run"],
            env={"ROOT": str(project)},
        )
        assert result.exit_code == 0, result.output
        assert "tiktok" in result.output
        assert "dry-run" in result.output

    def test_tiktok_live_fails_closed_without_credential(self, project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["publish", "test-proj", "--platform", "tiktok"],
            env={"ROOT": str(project)},
        )
        assert result.exit_code == 1, result.output
        assert "No publish credential" in result.output

    def test_instagram_dry_run_without_video_url_is_a_clean_error(
        self, project: Path
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["publish", "test-proj", "--platform", "instagram", "--dry-run"],
            env={"ROOT": str(project)},
        )
        assert result.exit_code == 1, result.output
        assert "--video-url" in result.output

    def test_instagram_dry_run_with_video_url(self, project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["publish", "test-proj", "--platform", "instagram", "--dry-run",
             "--video-url", "https://cdn.example/v.mp4"],
            env={"ROOT": str(project)},
        )
        assert result.exit_code == 0, result.output
        assert "https://cdn.example/v.mp4" in result.output


class TestCapabilityRow:
    def test_publish_schedule_is_supported(self) -> None:
        row = next(c for c in caps_mod.CAPABILITIES if c["id"] == "publish_schedule")
        assert row["status"] == "supported"
        assert row["command"] == "publish"

    def test_readme_roadmap_line_is_synced(self) -> None:
        readme = (Path(__file__).resolve().parent.parent / "README.md").read_text(
            encoding="utf-8"
        )
        publish_lines = [ln for ln in readme.splitlines() if "Publish/schedule" in ln]
        assert publish_lines, "README roadmap lost its publish/schedule line"
        assert any("planned" not in ln.lower() for ln in publish_lines)
