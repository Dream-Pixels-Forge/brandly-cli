"""Contract tests: the director tool's cinematic aspect-ratio policy.

The user requirement: cinematic (and short-film) style defaults to 21:9
unless the caller explicitly passes another ratio. Verified with an injected
fake ``VideoBackend`` so no network is needed — ``_director`` now submits
through the backend seam (``brandly_cli.video_backend``) instead of calling
``create_video_task`` directly.
"""

from __future__ import annotations

from typing import Any

from brandly_cli.agent_tools import invoke_tool
from brandly_cli.video_backend import VideoBackend, VideoTaskResult


class _FakeBackend(VideoBackend):
    """Deterministic test double: returns one pending task, never calls Agnes."""

    async def submit(self, **kwargs: Any) -> VideoTaskResult:
        return VideoTaskResult(video_id="vid-001", status="pending")


def test_cinematic_defaults_to_21_9(tmp_path) -> None:
    result = invoke_tool(
        "director",
        project_id="p1",
        shot_id="s1",
        scene_id="sc1",
        prompt="test",
        style="cinematic",
        backend=_FakeBackend(),
        root=str(tmp_path),
    )
    assert result["aspect_ratio"] == "21:9"


def test_short_film_defaults_to_21_9(tmp_path) -> None:
    result = invoke_tool(
        "director",
        project_id="p1",
        shot_id="s1",
        scene_id="sc1",
        prompt="test",
        style="short-film",
        backend=_FakeBackend(),
        root=str(tmp_path),
    )
    assert result["aspect_ratio"] == "21:9"


def test_explicit_ratio_is_respected(tmp_path) -> None:
    result = invoke_tool(
        "director",
        project_id="p1",
        shot_id="s1",
        scene_id="sc1",
        prompt="test",
        style="cinematic",
        aspect_ratio="2.39:1",
        backend=_FakeBackend(),
        root=str(tmp_path),
    )
    assert result["aspect_ratio"] == "2.39:1"


def test_non_cinematic_keeps_16_9(tmp_path) -> None:
    result = invoke_tool(
        "director",
        project_id="p1",
        shot_id="s1",
        scene_id="sc1",
        prompt="test",
        style="ugc",
        backend=_FakeBackend(),
        root=str(tmp_path),
    )
    assert result["aspect_ratio"] == "16:9"


def test_direction_record_carries_enforced_ratio(tmp_path) -> None:
    result = invoke_tool(
        "director",
        project_id="p1",
        shot_id="s1",
        scene_id="sc1",
        prompt="test",
        style="cinematic",
        backend=_FakeBackend(),
        root=str(tmp_path),
    )
    assert result["direction"]["aspect_ratio"] == "21:9"
