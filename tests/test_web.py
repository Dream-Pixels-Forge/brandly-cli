"""Tests for the web timeline editor module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def runner(tmp_path: Path):
    """Click-like runner with tmp_path available."""
    import os
    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    from click.testing import CliRunner
    r = CliRunner(env=env)
    r.tmp_path = tmp_path
    return r


class TestClipModel:
    """Tests for the Clip Pydantic model."""

    def test_clip_defaults(self) -> None:
        from brandly_cli.web.models import Clip

        clip = Clip(id="shot-1", shot_id="shot-1", clip_path="videos/scenes/test.mp4", prompt="test")
        assert clip.duration == 5.0  # default
        assert clip.status == "pending"
        assert clip.transition_duration == 0.5
        assert clip.volume == 1.0

    def test_clip_start_time(self) -> None:
        from brandly_cli.web.models import Clip

        clip = Clip(id="s1", shot_id="s1", clip_path="x", prompt="p")
        clip.start_time = 3.0
        assert clip.start_time == 3.0
        assert clip.end_time == 8.0  # 3.0 + 5.0 default duration

    def test_clip_thumbnail_path(self) -> None:
        from brandly_cli.web.models import Clip

        clip = Clip(id="s1", shot_id="s1", clip_path="videos/scenes/Scene-01-Shot-1.mp4", prompt="p")
        assert clip.thumbnail_path == "thumbnails/Scene-01-Shot-1.png"


class TestProjectTimeline:
    """Tests for the ProjectTimeline model."""

    def test_total_duration_empty(self) -> None:
        from brandly_cli.web.models import ProjectTimeline

        tl = ProjectTimeline(project_id="test")
        assert tl.total_duration == 0.0

    def test_total_duration_computed(self) -> None:
        from brandly_cli.web.models import Clip, ProjectTimeline

        clips = [
            Clip(id="c1", shot_id="c1", clip_path="x", prompt="p", duration=5.0),
            Clip(id="c2", shot_id="c2", clip_path="x", prompt="p", duration=3.0),
        ]
        tl = ProjectTimeline(project_id="test", clips=clips)
        assert tl.total_duration == 8.0


class TestTimelineState:
    """Tests for TimelineState load/save/reorder."""

    def test_load_creates_from_scratch(self, runner) -> None:  # type: ignore[reportUnknownVariableType]
        from brandly_cli.web.state import TimelineState

        state = TimelineState("test-proj", runner.tmp_path)
        timeline = state.load()
        assert timeline.project_id == "test-proj"
        assert len(timeline.clips) == 0
        assert (runner.tmp_path / ".brandly" / "test-proj" / "docs" / "tmp" / "timeline.json").exists()

    def test_save_and_reload(self, runner) -> None:  # type: ignore[reportUnknownVariableType]
        from brandly_cli.web.models import Clip
        from brandly_cli.web.state import TimelineState

        state = TimelineState("test-proj", runner.tmp_path)
        state.load()
        state.timeline.clips = [
            Clip(id="c1", shot_id="c1", clip_path="videos/scenes/Scene-01-Shot-1.mp4", prompt="hello", duration=5.0),
        ]
        state.save()

        state2 = TimelineState("test-proj", runner.tmp_path)
        timeline2 = state2.load()
        assert len(timeline2.clips) == 1
        assert timeline2.clips[0].id == "c1"
        assert timeline2.clips[0].duration == 5.0

    def test_reorder_clips(self, runner) -> None:  # type: ignore[reportUnknownVariableType]
        from brandly_cli.web.models import Clip
        from brandly_cli.web.state import TimelineState

        state = TimelineState("test-proj", runner.tmp_path)
        state.load()
        state.timeline.clips = [
            Clip(id="c1", shot_id="c1", clip_path="x", prompt="p", duration=5.0),
            Clip(id="c2", shot_id="c2", clip_path="x", prompt="p", duration=3.0),
            Clip(id="c3", shot_id="c3", clip_path="x", prompt="p", duration=4.0),
        ]
        for c in state.timeline.clips:
            c.start_time = 0.0
        state.save()

        state.reorder_clips(["c3", "c1", "c2"])
        ids = [c.id for c in state.timeline.clips]
        assert ids == ["c3", "c1", "c2"]
        assert state.timeline.clips[0].start_time == 0.0
        assert state.timeline.clips[1].start_time == 4.0
        assert state.timeline.clips[2].start_time == 9.0

    def test_update_clip_duration(self, runner) -> None:  # type: ignore[reportUnknownVariableType]
        from brandly_cli.web.models import Clip, ClipUpdate
        from brandly_cli.web.state import TimelineState

        state = TimelineState("test-proj", runner.tmp_path)
        state.load()
        state.timeline.clips = [
            Clip(id="c1", shot_id="c1", clip_path="x", prompt="p", duration=5.0),
        ]
        state.save()

        updated = state.update_clip("c1", ClipUpdate(duration=7.0))
        assert updated is not None
        assert updated.duration == 7.0

    def test_update_clip_duration_clamped(self, runner) -> None:  # type: ignore[reportUnknownVariableType]
        from brandly_cli.web.models import Clip, ClipUpdate
        from brandly_cli.web.state import TimelineState

        state = TimelineState("test-proj", runner.tmp_path)
        state.load()
        state.timeline.clips = [
            Clip(id="c1", shot_id="c1", clip_path="x", prompt="p", duration=5.0),
        ]
        state.save()

        updated = state.update_clip("c1", ClipUpdate(duration=15.0))
        assert updated.duration == 12.0

        updated2 = state.update_clip("c1", ClipUpdate(duration=0.5))
        assert updated2.duration == 1.0

    def test_get_clip_not_found(self, runner) -> None:  # type: ignore[reportUnknownVariableType]
        from brandly_cli.web.state import TimelineState

        state = TimelineState("test-proj", runner.tmp_path)
        state.load()
        assert state.get_clip("nonexistent") is None


class TestProjectsRoute:
    """Tests for the projects API endpoint."""

    def test_list_projects_empty(self, runner) -> None:  # type: ignore[reportUnknownVariableType]
        from fastapi.testclient import TestClient

        from brandly_cli.web.server import create_app

        app = create_app(root=str(runner.tmp_path))
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        res = client.get("/api/projects")
        assert res.status_code == 200
        data = res.json()
        assert data["projects"] == []

    def test_list_projects_with_project(self, runner) -> None:  # type: ignore[reportUnknownVariableType]
        from fastapi.testclient import TestClient

        from brandly_cli.web.server import create_app

        proj_dir = runner.tmp_path / ".brandly" / "my-proj"
        proj_dir.mkdir(parents=True)
        (proj_dir / "project.json").write_text(json.dumps({
            "id": "my-proj",
            "name": "My Project",
            "status": "running",
            "style": "cinematic",
            "shot_count": 3,
        }))

        app = create_app(root=str(runner.tmp_path))
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        res = client.get("/api/projects")
        assert res.status_code == 200
        data = res.json()
        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "My Project"


class TestTimelineRoute:
    """Tests for the timeline API endpoint."""

    def test_get_timeline_for_existing_project(self, runner) -> None:  # type: ignore[reportUnknownVariableType]
        from fastapi.testclient import TestClient

        from brandly_cli.web.server import create_app

        (runner.tmp_path / ".brandly" / "my-proj").mkdir(parents=True)

        app = create_app(root=str(runner.tmp_path))
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        res = client.get("/api/projects/my-proj/timeline")
        assert res.status_code == 200
        data = res.json()
        assert data["timeline"]["project_id"] == "my-proj"
        assert data["timeline"]["clips"] == []


class TestClipRoute:
    """Tests for the clips API endpoint."""

    def test_patch_clip(self, runner) -> None:  # type: ignore[reportUnknownVariableType]
        from fastapi.testclient import TestClient

        from brandly_cli.web.server import create_app

        proj_dir = runner.tmp_path / ".brandly" / "my-proj" / "docs" / "tmp"
        proj_dir.mkdir(parents=True)
        (proj_dir / "timeline.json").write_text(json.dumps({
            "project_id": "my-proj",
            "clips": [
                {"id": "c1", "shot_id": "s1", "clip_path": "videos/scenes/test.mp4",
                 "prompt": "hello", "duration": 5.0, "status": "generated"}
            ],
        }))

        app = create_app(root=str(runner.tmp_path))
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        res = client.patch(
            "/api/projects/my-proj/clips/c1",
            json={"duration": 7.0},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["clip"]["duration"] == 7.0

    def test_patch_clip_not_found(self, runner) -> None:  # type: ignore[reportUnknownVariableType]
        from fastapi.testclient import TestClient

        from brandly_cli.web.server import create_app

        app = create_app(root=str(runner.tmp_path))
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        res = client.patch(
            "/api/projects/my-proj/clips/nonexistent",
            json={"duration": 7.0},
        )
        assert res.status_code == 404


class TestSpaBundle:
    """Issue #61: the shipped SPA must be a real built bundle, never the
    dev placeholder. A silently stale/drify static dir is a prod outage for
    every ``brandly studio`` user."""

    def test_root_serves_built_spa_not_placeholder(self, runner) -> None:  # type: ignore[reportUnknownVariableType]
        from fastapi.testclient import TestClient

        from brandly_cli.web.server import create_app

        app = create_app(root=str(runner.tmp_path))
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        res = client.get("/")
        assert res.status_code == 200
        body = res.text
        assert "Frontend SPA not yet built" not in body, (
            "GET / serves the dev placeholder — static bundle missing/stale (issue #61)"
        )
        assert "/static/" in body, (
            "GET / does not reference the built /static/ bundle (issue #61)"
        )

    def test_static_index_matches_source_build(self) -> None:
        from brandly_cli.web import server as server_module

        static_dir = Path(server_module.__file__).parent / "static"
        index = static_dir / "index.html"
        assert index.is_file(), "static/index.html missing — run npm run build in web/"
        body = index.read_text(encoding="utf-8")
        assert "/static/assets/" in body, (
            "static/index.html is not a vite build output (issue #61)"
        )
        assets = list((static_dir / "assets").glob("index-*.js"))
        assert assets, "static/assets bundle missing — run npm run build in web/"
        for asset in assets:
            assert asset.stat().st_size > 10_000, (
                f"{asset.name} suspiciously small — stale bundle? (issue #61)"
            )
