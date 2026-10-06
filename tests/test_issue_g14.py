"""Contract test: G14 - Provider seam (VideoBackend protocol).

RED test for the provider seam increment.

The CLI should:
1. Have a VideoBackend protocol with submit → poll → fetch clip + capability descriptor
2. shot_runner should depend on the protocol, not a concrete provider
3. The capability descriptor drives G7's split policy and G13's quota estimate
4. A second backend can be added as a new file without changing shot_runner
"""

from __future__ import annotations

from brandly_cli import shot_runner
from brandly_cli.video_backend import (
    AgnesVideoBackend,
    VideoBackend,
    VideoBackendCapabilities,
    VideoTaskResult,
)


class TestVideoBackendProtocol:
    """Test the VideoBackend protocol exists and has required methods."""

    def test_video_backend_protocol_exists(self):
        """VideoBackend protocol must exist."""
        assert hasattr(shot_runner, "VideoBackend"), "VideoBackend must be exported from shot_runner"
        assert VideoBackend is not None

    def test_video_backend_capabilities_dataclass(self):
        """VideoBackendCapabilities must exist with required fields."""
        caps = VideoBackendCapabilities(
            max_duration_seconds=12,
            reliable_duration_seconds=8,
            rate_limit_rpm=1,
            supports_keyframe_mode=True,
            supports_reference_mode=True,
            supports_text_mode=True,
        )
        assert caps.max_duration_seconds == 12
        assert caps.reliable_duration_seconds == 8
        assert caps.rate_limit_rpm == 1

    def test_video_task_result_dataclass(self):
        """VideoTaskResult must exist."""
        result = VideoTaskResult(
            video_id="test-123",
            status="pending",
            url=None,
            progress=0,
            error=None,
        )
        assert result.video_id == "test-123"
        assert result.status == "pending"


class TestAgnesVideoBackend:
    """Test the Agnes implementation of VideoBackend."""

    def test_agnes_backend_implements_protocol(self):
        """AgnesVideoBackend must implement VideoBackend protocol."""
        backend = AgnesVideoBackend()
        assert isinstance(backend, VideoBackend)

    def test_agnes_backend_has_capabilities(self):
        """AgnesVideoBackend must expose capabilities."""
        backend = AgnesVideoBackend()
        caps = backend.capabilities()
        assert isinstance(caps, VideoBackendCapabilities)
        assert caps.max_duration_seconds == 12
        assert caps.reliable_duration_seconds == 8
        assert caps.rate_limit_rpm == 1

    def test_agnes_backend_submit_poll_fetch(self):
        """AgnesVideoBackend must have submit, poll, fetch methods."""
        backend = AgnesVideoBackend()
        assert hasattr(backend, "submit")
        assert hasattr(backend, "poll")
        assert hasattr(backend, "fetch")


class TestShotRunnerUsesProtocol:
    """Test that shot_runner uses the VideoBackend protocol."""

    def test_shot_runner_no_direct_agnes_import(self):
        """shot_runner should not import agnes_client directly."""
        import inspect
        source = inspect.getsource(shot_runner)
        assert "from brandly_cli.agnes_client import" not in source
        assert "import brandly_cli.agnes_client" not in source

    def test_shot_runner_accepts_backend(self):
        """ShotRunner should accept a VideoBackend instance."""
        import dataclasses

        from brandly_cli.shot_runner import RunnerConfig
        fields = {f.name for f in dataclasses.fields(RunnerConfig)}
        assert "video_backend" in fields, "RunnerConfig must have video_backend field"


class TestCapabilityDescriptorDrivesPolicy:
    """Test that capability descriptor drives G7 split and G13 quota."""

    def test_split_policy_uses_capabilities(self):
        """G7 split_long_shots should use backend capabilities."""
        assert hasattr(shot_runner, "split_long_shots")

    def test_quota_estimate_uses_capabilities(self):
        """G13 quota estimate should use backend capabilities."""
        import inspect

        from brandly_cli.cost_tracker import compute_multi_day_schedule
        sig = inspect.signature(compute_multi_day_schedule)
        assert "avg_shot_duration" in sig.parameters


class TestSecondBackendTestDouble:
    """Test that a second backend can be added without changing shot_runner."""

    def test_fake_backend_can_be_created(self):
        """A fake backend for testing should work."""

        class FakeBackend(VideoBackend):
            def capabilities(self) -> VideoBackendCapabilities:
                return VideoBackendCapabilities(
                    max_duration_seconds=30,
                    reliable_duration_seconds=15,
                    rate_limit_rpm=10,
                )

            async def submit(self, **kwargs) -> VideoTaskResult:
                return VideoTaskResult(video_id="fake-1", status="pending")

            async def poll(self, video_id: str) -> VideoTaskResult:
                return VideoTaskResult(video_id=video_id, status="completed", url="http://fake/video.mp4")

            async def fetch(self, video_id: str) -> bytes:
                return b"fake video data"

        backend = FakeBackend()
        assert isinstance(backend, VideoBackend)
        caps = backend.capabilities()
        assert caps.max_duration_seconds == 30
        assert caps.reliable_duration_seconds == 15
