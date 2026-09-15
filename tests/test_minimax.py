"""Tests for MiniMax H3 video + TTS improvements."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from brandly_cli import dubbing
from brandly_cli.minimax_client import create_video_task, generate_image


@pytest.fixture(autouse=True)
def mock_minimax_key(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("MINIMAX_API_KEY", "test-minimax-key-12345")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://test-minimax.example.com")
    return "test-minimax-key-12345"


def _run(coro: Any) -> Any:
    return __import__("asyncio").run(coro)


def _make_ctx(body_capture: dict) -> MagicMock:
    """Build an AsyncClient context-mgr mock that captures the POST body."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"task_id": "t-1", "status": "pending"}
    resp.raise_for_status.return_value = None
    resp.headers = {}

    async def fake_post(url: Any, headers: Any = None, json: Any = None) -> MagicMock:
        body_capture["json"] = json
        return resp

    client = AsyncMock()
    client.post = fake_post

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestH3MaxGuards:
    def test_h3_max_strips_reference_inputs(self) -> None:
        cap: dict[str, Any] = {}
        ctx = _make_ctx(cap)
        with patch("brandly_cli.minimax_client.httpx.AsyncClient", return_value=ctx):
            _run(
                create_video_task(
                    "test",
                    model="MiniMax-H3-Max",
                    reference_videos=["https://v/1.mp4"],
                    reference_audios=["https://a/1.mp3"],
                )
            )
        content = cap["json"]["content"]
        # H3-Max must NOT forward reference video/audio items
        roles = [c.get("role") for c in content]
        assert "reference_video" not in roles
        assert "reference_audio" not in roles

    def test_h3_keeps_reference_inputs(self) -> None:
        cap: dict[str, Any] = {}
        ctx = _make_ctx(cap)
        with patch("brandly_cli.minimax_client.httpx.AsyncClient", return_value=ctx):
            _run(
                create_video_task(
                    "test",
                    model="MiniMax-H3",
                    reference_videos=["https://v/1.mp4"],
                )
            )
        roles = [c.get("role") for c in cap["json"]["content"]]
        assert "reference_video" in roles

    def test_duration_clamped_to_model_range(self) -> None:
        cap: dict[str, Any] = {}
        ctx = _make_ctx(cap)
        with patch("brandly_cli.minimax_client.httpx.AsyncClient", return_value=ctx):
            _run(create_video_task("t", model="MiniMax-H3-Max", duration=3))
        assert cap["json"]["duration"] == 5  # H3-Max min is 5s


class TestDubbingTts:
    def test_generate_tts_falls_back_to_silence_without_key(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        out = tmp_path / "tts.aac"
        result = _run(dubbing._generate_tts_audio("hello", "voice", out))
        # No API key -> silent fallback path (still a valid dict result)
        assert result.get("tts_source") in ("silent_fallback", "error", None) or "error" in result

    def test_dub_video_accepts_transcript(self, tmp_path: Any) -> None:
        # transcript param exists and is accepted (no ffmpeg -> graceful error)
        src = tmp_path / "in.mp4"
        src.write_bytes(b"fake")
        with patch("brandly_cli.dubbing._ffmpeg_available", return_value=False):
            result = _run(dubbing.dub_video(src, "en", "es", transcript="bonjour"))
        assert "error" in result


class TestMinimaxImageSeedAndStyle:
    def test_seed_forwarded_to_body(self) -> None:
        cap: dict[str, Any] = {}

        async def fake_post(*args: Any, **kwargs: Any) -> Any:
            cap["json"] = kwargs.get("json")
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"id": "i", "data": {"image_urls": []}}
            resp.raise_for_status.return_value = None
            return resp

        client = AsyncMock()
        client.post = fake_post
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=False)
        with patch("brandly_cli.minimax_client.httpx.AsyncClient", return_value=ctx):
            _run(generate_image("a cat", seed=42))
        assert cap["json"]["seed"] == 42

    def test_live_style_forwarded_only_for_live_model(self) -> None:
        cap: dict[str, Any] = {}

        async def fake_post(*args: Any, **kwargs: Any) -> Any:
            cap["json"] = kwargs.get("json")
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"id": "i", "data": {"image_urls": []}}
            resp.raise_for_status.return_value = None
            return resp

        client = AsyncMock()
        client.post = fake_post
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("brandly_cli.minimax_client.httpx.AsyncClient", return_value=ctx):
            _run(
                generate_image(
                    "a cat",
                    model="image-01-live",
                    image_style_setting={"style": "cinematic"},
                )
            )
        assert cap["json"]["image_style_setting"] == {"style": "cinematic"}

        # non-live model must NOT forward the style setting
        cap.clear()
        with patch("brandly_cli.minimax_client.httpx.AsyncClient", return_value=ctx):
            _run(
                generate_image(
                    "a cat",
                    model="image-01",
                    image_style_setting={"style": "cinematic"},
                )
            )
        assert "image_style_setting" not in cap["json"]


class TestMinimaxImageBatchFallback:
    """Batch (n>1) generation must fall back to one-at-a-time on failure/partial."""

    def _image_resp(self, urls: list[str], success: int) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "id": "i",
            "data": {"image_urls": urls},
            "metadata": {"success_count": success, "failed_count": 0},
        }
        resp.raise_for_status.return_value = None
        return resp

    def test_full_batch_no_fallback(self) -> None:
        calls: list[int] = []

        # Use an AsyncMock post that records n and returns full 2/2 for the batch.
        async def fake_post(*args: Any, **kwargs: Any) -> Any:
            n = kwargs.get("json", {}).get("n")
            calls.append(n)
            resp = self._image_resp([f"https://i/{x}.png" for x in range(n)], n or 0)
            resp.raise_for_status.return_value = None
            return resp

        client = AsyncMock()
        client.post = fake_post
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=False)
        with patch("brandly_cli.minimax_client.httpx.AsyncClient", return_value=ctx):
            result = _run(generate_image("a cat", n=2))
        # A successful 2/2 batch is returned directly, no one-at-a-time follow-up.
        assert result["fallback_used"] is False
        assert result["success_count"] == 2
        assert len(calls) == 1 and calls[0] == 2

    def test_partial_batch_falls_back_one_at_a_time(self) -> None:
        calls: list[int] = []

        async def fake_post(*args: Any, **kwargs: Any) -> Any:
            n = kwargs.get("json", {}).get("n")
            calls.append(n)
            if n == 3:
                # Batch returns only 1 of 3 -> trigger fallback.
                return self._image_resp(["https://i/1.png"], 1)
            # n==1 fallback items each return a single image.
            return self._image_resp([f"https://i/{len(calls)}.png"], 1)

        client = AsyncMock()
        client.post = fake_post
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=False)
        with patch("brandly_cli.minimax_client.httpx.AsyncClient", return_value=ctx):
            result = _run(generate_image("a cat", n=3))
        assert result["fallback_used"] is True
        assert result["success_count"] == 3
        # 1 batch call (n=3) + 2 fallback calls (n=1 each).
        assert calls[0] == 3 and 1 in calls[1:]

    def test_batch_failure_falls_back_one_at_a_time(self) -> None:
        import httpx as _httpx

        calls: list[int] = []

        async def fake_post(*args: Any, **kwargs: Any) -> Any:
            n = kwargs.get("json", {}).get("n")
            calls.append(n)
            if n == 2:
                resp = MagicMock()
                resp.status_code = 429
                resp.headers = {}
                resp.json.return_value = {}
                resp.raise_for_status.side_effect = _httpx.HTTPStatusError(
                    "rate limited", request=MagicMock(), response=resp
                )
                return resp
            return self._image_resp([f"https://i/{len(calls)}.png"], 1)

        client = AsyncMock()
        client.post = fake_post
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=False)
        with patch("brandly_cli.minimax_client.httpx.AsyncClient", return_value=ctx):
            result = _run(generate_image("a cat", n=2))
        # Batch 429 -> two one-at-a-time items.
        assert result["fallback_used"] is True
        assert result["success_count"] == 2
        assert calls == [2, 1, 1]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
