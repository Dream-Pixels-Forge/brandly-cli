"""Integration tests for VideoBackend protocol wiring in shot_runner."""

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


def test_shot_runner_accepts_video_backend():
    """shot_runner should accept a VideoBackend instance instead of hard-coding agnes_client."""
    from brandly_cli import shot_runner

    # The function should exist and accept backend param
    assert hasattr(shot_runner, "run_shots")

    # RED: currently run_shots does not accept backend param
    import inspect
    sig = inspect.signature(shot_runner.run_shots)
    params = list(sig.parameters.keys())
    assert "backend" in params, "run_shots must accept backend parameter for VideoBackend injection"
