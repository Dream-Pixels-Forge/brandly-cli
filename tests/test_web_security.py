"""Security + wiring tests for the web timeline server (RED first).

These encode the contract fixed after the wiring review:
* the server owns the project root (no client-supplied ``root``),
* every path that reaches the filesystem is contained inside the project,
* paid/long actions require a per-run token and a loopback Host,
* async routes await instead of calling ``asyncio.run``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from brandly_cli.web.server import create_app

LOOPBACK = "http://127.0.0.1:8765"


def _timeline(clip_path: str = "videos/scenes/Scene-01-Shot-1-1.mp4") -> dict:
    return {
        "project_id": "my-proj",
        "clips": [
            {
                "id": "c1",
                "shot_id": "s1",
                "clip_path": clip_path,
                "prompt": "hello",
                "duration": 5.0,
                "status": "generated",
            }
        ],
    }


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """A root with one project, one clip file, and an existing timeline."""
    root = tmp_path / "root"
    proj = root / ".brandly" / "my-proj"
    (proj / "docs" / "tmp").mkdir(parents=True)
    (proj / "videos" / "scenes").mkdir(parents=True)
    (proj / "project.json").write_text(json.dumps({"id": "my-proj", "name": "My Project"}))
    (proj / "videos" / "scenes" / "Scene-01-Shot-1-1.mp4").write_bytes(b"CLIP-BYTES")
    (proj / "docs" / "tmp" / "timeline.json").write_text(json.dumps(_timeline()))
    (tmp_path / "secret.txt").write_text("TOP-SECRET")
    return root


def _client(project_root: Path, token: str | None = None, **client_kwargs) -> TestClient:  # type: ignore[no-untyped-def]
    """A client for ``create_app`` that speaks from a loopback host."""
    client_kwargs.setdefault("base_url", LOOPBACK)
    return TestClient(create_app(root=str(project_root), token=token), **client_kwargs)


@pytest.fixture
def client(project_root: Path) -> TestClient:
    return _client(project_root)


class TestSafeJoin:
    def test_rejects_parent_traversal(self, project_root: Path) -> None:
        from brandly_cli.web.security import safe_join

        assert safe_join(project_root, "..", "secret.txt") is None
        assert safe_join(project_root, "../../secret.txt") is None

    def test_rejects_absolute_escape(self, project_root: Path) -> None:
        import sys

        pytest.skip("Windows-only: C:/... is a relative path on POSIX") if sys.platform != "win32" else None
        from brandly_cli.web.security import safe_join

        assert safe_join(project_root, "C:/Windows/win.ini") is None

    def test_allows_in_root_child(self, project_root: Path) -> None:
        from brandly_cli.web.security import safe_join

        proj_dir = project_root / ".brandly" / "my-proj"
        resolved = safe_join(proj_dir, "videos", "scenes", "Scene-01-Shot-1-1.mp4")
        assert resolved is not None
        assert resolved.read_bytes() == b"CLIP-BYTES"


class TestPreviewRoutes:
    def test_preview_serves_clip_by_id(self, client: TestClient) -> None:
        res = client.get("/api/projects/my-proj/clips/c1/preview")
        assert res.status_code == 200
        assert res.content == b"CLIP-BYTES"

    def test_preview_404_for_unknown_clip(self, client: TestClient) -> None:
        assert client.get("/api/projects/my-proj/clips/nope/preview").status_code == 404

    def test_thumb_404_when_not_generated(self, client: TestClient) -> None:
        assert client.get("/api/projects/my-proj/clips/c1/thumb").status_code == 404

    def test_preview_rejects_escaping_clip_path(self, client: TestClient, project_root: Path) -> None:
        tmp = project_root / ".brandly" / "my-proj" / "docs" / "tmp" / "timeline.json"
        tmp.write_text(json.dumps(_timeline(clip_path="../../../secret.txt")))
        assert client.get("/api/projects/my-proj/clips/c1/preview").status_code == 404

    def test_legacy_proxy_routes_are_gone(self, client: TestClient) -> None:
        """The old path-based proxies were the traversal hole; they must be removed."""
        assert client.get("/proxy/video/my-proj?path=clip.mp4").status_code == 404
        assert client.get("/proxy/thumb/my-proj?path=t.png").status_code == 404


class TestServerOwnsRoot:
    def test_client_root_query_is_ignored(self, project_root: Path, tmp_path: Path) -> None:
        other = tmp_path / "other"
        (other / ".brandly" / "ghost").mkdir(parents=True)
        client = _client(project_root)
        res = client.get("/api/projects", params={"root": str(other)})
        assert [p["id"] for p in res.json()["projects"]] == ["my-proj"]

    def test_config_reports_bound_root_and_package_version(self, project_root: Path) -> None:
        import brandly_cli
        from brandly_cli.stitch import TRANSITIONS

        data = _client(project_root).get("/api/config").json()
        assert Path(data["root"]).resolve() == project_root.resolve()
        assert data["version"] == brandly_cli.__version__
        assert data["transitions"] == list(TRANSITIONS)


class TestLocalGuard:
    def test_token_required_when_configured(self, project_root: Path) -> None:
        client = _client(project_root, token="s3cret")
        assert client.get("/api/config").status_code == 401
        assert client.get("/api/config", params={"token": "s3cret"}).status_code == 200
        assert client.get("/api/config", headers={"X-Brandly-Token": "s3cret"}).status_code == 200

    def test_static_and_index_stay_reachable_without_token(self, project_root: Path) -> None:
        assert _client(project_root, token="s3cret").get("/").status_code == 200

    def test_foreign_host_is_rejected(self, project_root: Path) -> None:
        client = _client(project_root)
        res = client.get("/api/config", headers={"Host": "evil.example.com"})
        assert res.status_code == 403

    def test_cross_origin_is_rejected(self, project_root: Path) -> None:
        res = _client(project_root).get(
            "/api/config", headers={"Origin": "https://evil.example.com"}
        )
        assert res.status_code == 403


class TestProjectExistence:
    def test_unknown_project_timeline_is_404(self, client: TestClient) -> None:
        assert client.get("/api/projects/ghost-proj/timeline").status_code == 404

    def test_unknown_project_creates_no_directories(
        self, client: TestClient, project_root: Path
    ) -> None:
        res = client.get("/api/projects/ghost-proj/timeline")
        assert res.status_code == 404
        assert not (project_root / ".brandly" / "ghost-proj").exists()

    def test_put_timeline_clamps_duration(self, client: TestClient) -> None:
        res = client.put(
            "/api/projects/my-proj/timeline",
            json={"clips": [dict(_timeline()["clips"][0], duration=999.0)]},
        )
        assert res.status_code == 200
        assert res.json()["timeline"]["clips"][0]["duration"] == 12.0


class TestAsyncRoutes:
    def test_export_awaits_stitch(
        self, client: TestClient, project_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called: list[list[Path]] = []

        async def fake_stitch(clips, output, **_kwargs):  # type: ignore[no-untyped-def]
            called.append(list(clips))
            Path(output).write_bytes(b"STITCHED")
            return {"duration_seconds": 5.0}

        monkeypatch.setattr("brandly_cli.stitch.stitch_videos", fake_stitch)
        res = client.post("/api/projects/my-proj/export")
        assert called, "stitch_videos was never awaited"
        assert res.json().get("error") in (None, ""), res.json()

    def test_regenerate_awaits_provider_calls(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import brandly_cli.agnes_client as agnes

        async def fake_create(prompt, **_kwargs):  # type: ignore[no-untyped-def]
            return {"video_id": "vid-1"}

        async def fake_poll(video_id, **_kwargs):  # type: ignore[no-untyped-def]
            return {"status": "completed", "url": "http://example.com/test.mp4"}

        monkeypatch.setattr(agnes, "create_video_task", fake_create)
        monkeypatch.setattr(agnes, "poll_video", fake_poll)
        # Mock download_file in the route module where it's imported
        from brandly_cli.web.routes import clips as clips_route
        async def fake_download(url, dest):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("fake mp4 content", encoding="utf-8")
        monkeypatch.setattr(clips_route, "download_file", fake_download)
        res = client.post("/api/projects/my-proj/clips/c1/regenerate")
        body = res.json()
        assert body["status"] == "completed", body
        assert "asyncio.run" not in str(body.get("error", ""))

