"""RED tests for VideoBackend usage in production tools."""

from __future__ import annotations

from brandly_cli.video_backend import VideoBackend, VideoBackendCapabilities, VideoTaskResult


class FakeBackend(VideoBackend):
    def capabilities(self):
        return VideoBackendCapabilities(max_duration_seconds=12, reliable_duration_seconds=8, rate_limit_rpm=1)

    async def submit(self, **kwargs):
        return VideoTaskResult(video_id="fake-1", status="pending")

    async def poll(self, video_id, *, max_wait_seconds=300, interval_seconds=5, model_name=None):
        return VideoTaskResult(video_id=video_id, status="completed", url="https://example.com/v.mp4")

    async def fetch(self, video_id):
        return b"bytes"


def test_production_director_uses_backend():
    """director tool should accept VideoBackend injection."""
    import inspect

    from brandly_cli.agent_tools.production import _director
    sig = inspect.signature(_director)
    params = list(sig.parameters.keys())
    assert "backend" in params, "_director must accept backend parameter for VideoBackend injection"
