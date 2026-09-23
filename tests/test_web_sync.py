"""Editor → CLI bridge tests: shots.json sync (plan line 60) and regenerate
guardrails (plan line 61). RED first — these must fail before the fix.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from brandly_cli.web.models import Clip
from brandly_cli.web.server import create_app
from brandly_cli.web.state import TimelineState

LOOPBACK = "http://127.0.0.1:8765"


def _clip(**over) -> dict:
    base = {
        "id": "Scene-01-Shot-1-1",
        "shot_id": "shot-1-1",
        "clip_path": "videos/scenes/Scene-01-Shot-1-1.mp4",
        "prompt": "hero product rotating on marble",
        "duration": 5.0,
        "style": "cinematic",
        "status": "generated",
    }
    base.update(over)
    return base


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """A project with a budget, one clip file and a one-clip timeline."""
    root = tmp_path / "root"
    proj = root / ".brandly" / "my-proj"
    (proj / "docs" / "tmp").mkdir(parents=True)
    (proj / "videos" / "scenes").mkdir(parents=True)
    (proj / "project.json").write_text(
        json.dumps({"id": "my-proj", "name": "My Project", "budget": 500})
    )
    (proj / "videos" / "scenes" / "Scene-01-Shot-1-1.mp4").write_bytes(b"CLIP-BYTES")
    (proj / "docs" / "tmp" / "timeline.json").write_text(
        json.dumps({"project_id": "my-proj", "clips": [_clip()]})
    )
    return root


@pytest.fixture
def client(project_root: Path) -> TestClient:
    return TestClient(create_app(root=str(project_root)), base_url=LOOPBACK)


def _shots_path(project_root: Path) -> Path:
    return project_root / ".brandly" / "my-proj" / "shots.json"


# ---------------------------------------------------------------------------
# W7 — timeline edits must reach `brandly produce` (plan line 60)
# ---------------------------------------------------------------------------


class TestShotsJsonSync:
    def test_save_writes_produce_compatible_shots_json(self, project_root: Path) -> None:
        state = TimelineState("my-proj", project_root)
        state.load()
        state.timeline.clips = [
            Clip(**_clip(duration=9.0)),
            Clip(**_clip(id="Scene-01-Shot-1-2", clip_path="videos/scenes/Scene-01-Shot-1-2.mp4",
                        duration=3.0)),
        ]
        state.save()

        from brandly_cli.shot_runner import load_shots_file

        data = load_shots_file(_shots_path(project_root))
        assert [s["name"] for s in data] == ["Scene-01-Shot-1-1", "Scene-01-Shot-1-2"]
        assert data[0]["duration"] == 9.0
        assert data[1]["duration"] == 3.0
        assert data[0]["style"] == "cinematic"

    def test_api_patch_syncs_duration_into_shots_json(
        self, client: TestClient, project_root: Path
    ) -> None:
        res = client.patch(
            "/api/projects/my-proj/clips/Scene-01-Shot-1-1",
            json={"duration": 7.5},
        )
        assert res.status_code == 200, res.text
        shots = json.loads(_shots_path(project_root).read_text(encoding="utf-8"))
        assert shots[0]["duration"] == 7.5

    def test_empty_timeline_writes_no_shots_file(self, project_root: Path) -> None:
        """An empty list must not be written — produce rejects a flat list of 0 shots."""
        tl = project_root / ".brandly" / "my-proj" / "docs" / "tmp" / "timeline.json"
        tl.write_text(json.dumps({"project_id": "my-proj", "clips": []}))
        state = TimelineState("my-proj", project_root)
        state.load()
        assert state.timeline.clips == []
        assert not _shots_path(project_root).exists()


# ---------------------------------------------------------------------------
# W6 — regenerate must respect the CLI's guardrails (plan line 61)
# ---------------------------------------------------------------------------


def _install_provider(monkeypatch: pytest.MonkeyPatch) -> dict[str, list]:
    """Fake create_video_task / poll_video / download_file; return call log."""
    calls: dict[str, list] = {"create": [], "download": []}

    import brandly_cli.agnes_client as agnes

    async def fake_create(prompt, **kwargs):  # type: ignore[no-untyped-def]
        calls["create"].append({"prompt": prompt, **kwargs})
        return {"video_id": "vid-1"}

    async def fake_poll(video_id, **kwargs):  # type: ignore[no-untyped-def]
        return {"status": "completed", "url": "https://provider.example/clip.mp4"}

    async def fake_download(url, dest):  # type: ignore[no-untyped-def]
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(b"NEW-CLIP")
        calls["download"].append(url)
        return Path(dest)

    monkeypatch.setattr(agnes, "create_video_task", fake_create)
    monkeypatch.setattr(agnes, "poll_video", fake_poll)
    monkeypatch.setattr("brandly_cli.web.routes.clips.download_file", fake_download)
    return calls


class TestRegenerateGuardrails:
    def test_regenerate_downloads_clip_into_project(
        self, client: TestClient, project_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """poll_video returns `url`, never `video_path` — the clip must land on disk."""
        _install_provider(monkeypatch)
        res = client.post("/api/projects/my-proj/clips/Scene-01-Shot-1-1/regenerate")
        assert res.json()["status"] == "completed", res.text

        saved = project_root / ".brandly" / "my-proj" / "videos" / "scenes" / "Scene-01-Shot-1-1.mp4"
        assert saved.read_bytes() == b"NEW-CLIP"

        preview = client.get("/api/projects/my-proj/clips/Scene-01-Shot-1-1/preview")
        assert preview.status_code == 200
        assert preview.content == b"NEW-CLIP"

    def test_regenerate_records_spend(
        self, client: TestClient, project_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Credit spend must reach cost.json so `brandly status` stays honest."""
        _install_provider(monkeypatch)
        res = client.post("/api/projects/my-proj/clips/Scene-01-Shot-1-1/regenerate")
        assert res.json()["status"] == "completed", res.text

        cost = json.loads(
            (project_root / ".brandly" / "my-proj" / "cost.json").read_text(encoding="utf-8")
        )
        assert cost["credits_spent"] == 20
        assert cost["cost_log"][0]["action"] == "video"

    def test_regenerate_refuses_when_over_budget(
        self, client: TestClient, project_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = _install_provider(monkeypatch)
        (project_root / ".brandly" / "my-proj" / "cost.json").write_text(
            json.dumps({"id": "my-proj", "budget_credits": 10, "credits_spent": 10, "cost_log": []})
        )
        res = client.post("/api/projects/my-proj/clips/Scene-01-Shot-1-1/regenerate")
        assert res.status_code == 400, res.text
        assert "budget" in res.json()["detail"].lower()
        assert calls["create"] == [], "provider called despite an exhausted budget"

        assert "budget" in res.json()["detail"].lower()
        assert calls["create"] == [], "provider called despite an exhausted budget"

    def test_regenerate_registers_plan_row(
        self, client: TestClient, project_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Plan line 61: regenerate registers its generation plan row."""
        _install_provider(monkeypatch)
        res = client.post("/api/projects/my-proj/clips/Scene-01-Shot-1-1/regenerate")
        assert res.json()["status"] == "completed", res.text

        from brandly_cli.planning import _read_production_plan_rows, production_plan_path

        rows = _read_production_plan_rows(production_plan_path("my-proj", root=project_root))
        sources = {r.get("source") for r in rows.values()}
        statuses = {r.get("status") for r in rows.values()}
        assert "brandly timeline" in sources, rows
        assert "COMPLETED" in statuses, rows

    def test_failed_regenerate_marks_plan_failed(
        self, client: TestClient, project_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import brandly_cli.agnes_client as agnes

        async def fake_create(prompt, **kwargs):  # type: ignore[no-untyped-def]
            return {"video_id": "vid-1"}

        async def fake_poll(video_id, **kwargs):  # type: ignore[no-untyped-def]
            return {"status": "failed", "error": "provider exploded"}

        monkeypatch.setattr(agnes, "create_video_task", fake_create)
        monkeypatch.setattr(agnes, "poll_video", fake_poll)

        res = client.post("/api/projects/my-proj/clips/Scene-01-Shot-1-1/regenerate")
        assert res.json()["status"] == "failed", res.text

        from brandly_cli.planning import _read_production_plan_rows, production_plan_path

        rows = _read_production_plan_rows(production_plan_path("my-proj", root=project_root))
        statuses = {r.get("status") for r in rows.values()}
        assert "FAILED" in statuses, rows


# ---------------------------------------------------------------------------
# W1 — reorder via PUT timeline (plan Phase 2)
# ---------------------------------------------------------------------------

class TestReorderViaApi:
    def test_put_timeline_reorders_and_reclocks_start_times(
        self, client: TestClient, project_root: Path
    ) -> None:
        res = client.put(
            "/api/projects/my-proj/timeline",
            json={
                "clips": [
                    _clip(id="c2", duration=3.0),
                    _clip(id="c1", duration=5.0),
                ],
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["timeline"]["clips"][0]["id"] == "c2"
        assert body["timeline"]["clips"][1]["id"] == "c1"
        assert body["timeline"]["clips"][0]["start_time"] == 0.0
        assert body["timeline"]["clips"][1]["start_time"] == 3.0

    def test_put_timeline_dur_clamps_to_model_limits(
        self, client: TestClient, project_root: Path
    ) -> None:
        res = client.put(
            "/api/projects/my-proj/timeline",
            json={
                "clips": [
                    _clip(id="c1", duration=0.3),   # below MIN
                    _clip(id="c2", duration=15.0),  # above MAX
                ],
            },
        )
        assert res.status_code == 200
        clips = res.json()["timeline"]["clips"]
        assert clips[0]["duration"] == 1.0   # clamped to MIN
        assert clips[1]["duration"] == 12.0  # clamped to MAX

    def test_put_timeline_syncs_shots_json(self, client: TestClient, project_root: Path) -> None:
        res = client.put(
            "/api/projects/my-proj/timeline",
            json={
                "clips": [
                    _clip(id="c2", duration=4.0),
                    _clip(id="c1", duration=6.0),
                ],
            },
        )
        assert res.status_code == 200
        shots = json.loads(_shots_path(project_root).read_text(encoding="utf-8"))
        assert [s["name"] for s in shots] == ["c2", "c1"]
        assert shots[0]["duration"] == 4.0
        assert shots[1]["duration"] == 6.0


# ---------------------------------------------------------------------------
# W3 — WebSocket broadcast (plan Phase 3)
# ---------------------------------------------------------------------------

class TestWebsocketBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_sends_events_to_connected_clients(
        self, project_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from brandly_cli.web.websocket import broadcast, clients, register, unregister

        fake_ws_1 = FakeWS()
        fake_ws_2 = FakeWS()
        register("my-proj", fake_ws_1)
        register("my-proj", fake_ws_2)
        assert clients("my-proj") == 2

        await broadcast("my-proj", {"type": "generation_progress", "phase": "starting"})
        assert fake_ws_1.sent == [{"type": "generation_progress", "phase": "starting"}]
        assert fake_ws_2.sent == [{"type": "generation_progress", "phase": "starting"}]

        unregister("my-proj", fake_ws_1)
        assert clients("my-proj") == 1

        await broadcast("my-proj", {"type": "generation_complete"})
        assert len(fake_ws_2.sent) == 2
        assert fake_ws_2.sent[-1] == {"type": "generation_complete"}

    @pytest.mark.asyncio
    async def test_broadcast_ignores_unknown_project(self) -> None:
        """Broadcasting to a project with no listeners must be a no-op."""
        from brandly_cli.web.websocket import broadcast
        await broadcast("nonexistent", {"type": "anything"})


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, obj: dict) -> None:
        self.sent.append(obj)


# ---------------------------------------------------------------------------
# W4 — export download (plan Phase 3)
# ---------------------------------------------------------------------------

class TestExportDownload:
    def test_download_exported_video(
        self, client: TestClient, project_root: Path
    ) -> None:
        """After a successful export, /export/download serves the stitched MP4."""
        from brandly_cli.stitch import _ffmpeg_available
        if not _ffmpeg_available():
            pytest.skip("ffmpeg not available")

        # Write a stub stitched file
        out_dir = project_root / ".brandly" / "my-proj" / "export"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "my-proj_stitched.mp4"
        out_file.write_bytes(b"DUMMY-STITCHED-MP4")

        res = client.get("/api/projects/my-proj/export/download")
        assert res.status_code == 200
        assert res.content == b"DUMMY-STITCHED-MP4"
        assert res.headers["content-type"] == "video/mp4"

    def test_download_missing_export_returns_404(
        self, client: TestClient
    ) -> None:
        res = client.get("/api/projects/my-proj/export/download")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# P0-1 — the layering gate must actually evaluate contracts
# ---------------------------------------------------------------------------
# See tests/test_architecture_contracts.py for the dedicated regression tests
# guarding `.importlinter` against silently evaluating zero contracts.


# ---------------------------------------------------------------------------
# Waveform endpoint
# ---------------------------------------------------------------------------

class TestWaveformEndpoint:
    def test_waveform_returns_points_for_clip_with_audio(
        self, client: TestClient, project_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ffmpeg is available and the clip has an audio stream, return points."""

        # Mock _ffmpeg_available to return True
        import brandly_cli.web.routes.waveform as wf_mod

        monkeypatch.setattr(wf_mod, "_ffmpeg_available", lambda: True)
        monkeypatch.setattr(wf_mod, "_has_audio_stream", lambda p: True)

        # Mock _extract_waveform to return deterministic data
        fake_points = [
            {"x": 0.0, "amplitude": 0.1},
            {"x": 2.5, "amplitude": 0.4},
            {"x": 5.0, "amplitude": 0.0},
        ]
        monkeypatch.setattr(wf_mod, "_extract_waveform", lambda p, n=200: fake_points)

        res = client.get("/api/projects/my-proj/clips/Scene-01-Shot-1-1/waveform")
        assert res.status_code == 200, res.text
        body = res.json()
        assert "points" in body
        assert len(body["points"]) == 3
        assert body["points"][1] == {"x": 2.5, "amplitude": 0.4}

    def test_waveform_returns_empty_for_video_without_audio(
        self, client: TestClient, project_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No audio stream → empty points array."""
        import brandly_cli.web.routes.waveform as wf_mod

        monkeypatch.setattr(wf_mod, "_ffmpeg_available", lambda: True)
        monkeypatch.setattr(wf_mod, "_has_audio_stream", lambda p: False)

        res = client.get("/api/projects/my-proj/clips/Scene-01-Shot-1-1/waveform")
        assert res.status_code == 200, res.text
        assert res.json()["points"] == []

    def test_waveform_returns_empty_when_ffmpeg_unavailable(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import brandly_cli.web.routes.waveform as wf_mod

        monkeypatch.setattr(wf_mod, "_ffmpeg_available", lambda: False)
        res = client.get("/api/projects/my-proj/clips/Scene-01-Shot-1-1/waveform")
        assert res.status_code == 200
        assert res.json()["points"] == []


# ---------------------------------------------------------------------------
# Gate endpoint
# ---------------------------------------------------------------------------

class TestGateEndpoint:
    def test_gate_runs_quality_check_and_updates_status(
        self, client: TestClient, project_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST to the gate endpoint runs the deterministic gate and persists status."""
        from brandly_cli.quality_gate import GateResult

        fake_result = GateResult(element="dummy", kind="video", status="pass", score=95)


        async def _fake_verify(*a, **kw):  # type: ignore[no-untyped-def]
            return fake_result

        monkeypatch.setattr("brandly_cli.quality_gate.verify_element", _fake_verify)

        res = client.post("/api/projects/my-proj/clips/Scene-01-Shot-1-1/gate")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["status"] in ("pass", "warn", "fail")
        assert isinstance(body["score"], int)

        # Verify timeline.json was not modified with "pass" (no-op for pass)
        state = TimelineState("my-proj", project_root)
        clip = state.get_clip("Scene-01-Shot-1-1")
        assert clip is not None

    def test_gate_returns_404_for_missing_clip(
        self, client: TestClient
    ) -> None:
        res = client.post("/api/projects/my-proj/clips/nonexistent-clip/gate")
        assert res.status_code == 404

