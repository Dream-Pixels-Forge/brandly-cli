"""Contract tests: the director tool's cinematic aspect-ratio policy.

The user requirement: cinematic (and short-film) style defaults to 21:9
unless the caller explicitly passes another ratio. Verified with a mocked
``create_video_task`` so no network is needed.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from brandly_cli.agent_tools import invoke_tool


def _fake_video_task(**kwargs: Any) -> dict[str, Any]:
    return {"video_id": "vid-001", "status": "pending", "mode": "text"}


async def _fake_video_task_async(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _fake_video_task(**kwargs)


class TestDirectorAspectPolicy:
    def test_cinematic_defaults_to_21_9(self, tmp_path) -> None:
        with patch("brandly_cli.agent_tools.production.create_video_task", _fake_video_task_async):
            result = invoke_tool(
                "director",
                project_id="p1",
                shot_id="s1",
                scene_id="sc1",
                prompt="test",
                style="cinematic",
                root=str(tmp_path),
            )
        assert result["aspect_ratio"] == "21:9"

    def test_short_film_defaults_to_21_9(self, tmp_path) -> None:
        with patch("brandly_cli.agent_tools.production.create_video_task", _fake_video_task_async):
            result = invoke_tool(
                "director",
                project_id="p1",
                shot_id="s1",
                scene_id="sc1",
                prompt="test",
                style="short-film",
                root=str(tmp_path),
            )
        assert result["aspect_ratio"] == "21:9"

    def test_explicit_ratio_is_respected(self, tmp_path) -> None:
        with patch("brandly_cli.agent_tools.production.create_video_task", _fake_video_task_async):
            result = invoke_tool(
                "director",
                project_id="p1",
                shot_id="s1",
                scene_id="sc1",
                prompt="test",
                style="cinematic",
                aspect_ratio="2.39:1",
                root=str(tmp_path),
            )
        assert result["aspect_ratio"] == "2.39:1"

    def test_non_cinematic_keeps_16_9(self, tmp_path) -> None:
        with patch("brandly_cli.agent_tools.production.create_video_task", _fake_video_task_async):
            result = invoke_tool(
                "director",
                project_id="p1",
                shot_id="s1",
                scene_id="sc1",
                prompt="test",
                style="ugc",
                root=str(tmp_path),
            )
        assert result["aspect_ratio"] == "16:9"

    def test_direction_record_carries_enforced_ratio(self, tmp_path) -> None:
        with patch("brandly_cli.agent_tools.production.create_video_task", _fake_video_task_async):
            result = invoke_tool(
                "director",
                project_id="p1",
                shot_id="s1",
                scene_id="sc1",
                prompt="test",
                style="cinematic",
                root=str(tmp_path),
            )
        assert result["direction"]["aspect_ratio"] == "21:9"
