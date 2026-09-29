"""Issue #150: documented-transient 5xx are never retried; poll aborts on them.

Agnes docs (Common Error Codes) classify 500 / 502 / 504 / 520 / 522 / 524 as
transient "retry later" errors — but ``_retry_with_backoff`` only retries
429/503 and re-raises every other status immediately.

Worse on the polling path: ``poll_video`` catches only (429, 503), so a
transient 500/502/504 mid-poll is re-raised and kills ``brandly video
--wait`` / ``produce`` even though the async task keeps running server-side.

Also: the poll wait ``10 * 2 ** (attempts % 3)`` cycles 20, 40, 10, 20...
(non-monotonic). Target: monotonic growth capped at 60 s.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from brandly_cli import agnes_client
from brandly_cli.agnes_client import _retry_with_backoff, poll_video

BODY_500 = json.dumps(
    {"error": {"code": "internal_error", "message": "boom (request id: R1)"}}
)


def _status_error(status: int, text: str) -> httpx.HTTPStatusError:
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    resp.headers = {}
    return httpx.HTTPStatusError(
        f"HTTP {status}", request=MagicMock(), response=resp
    )


# ---------------------------------------------------------------------------
# _retry_with_backoff: any 5xx is retryable (docs: "retry later")
# ---------------------------------------------------------------------------


class Test5xxRetries:
    @pytest.mark.parametrize("status", [500, 502, 504, 520, 522, 524])
    async def test_retried_then_success(self, status: int) -> None:
        calls = {"n": 0}

        async def _req() -> dict:
            calls["n"] += 1
            if calls["n"] < 2:
                raise _status_error(status, BODY_500)
            return {"ok": True}

        async def fake_sleep(s: float) -> None:
            pass

        with patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep):
            result = await _retry_with_backoff(
                _req, max_retries=3, base_delay=0.01, model="m"
            )
        assert result == {"ok": True}
        assert calls["n"] == 2

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
    async def test_4xx_still_raise_immediately(self, status: int) -> None:
        calls = {"n": 0}

        async def _req() -> dict:
            calls["n"] += 1
            raise _status_error(status, "{}")

        async def fake_sleep(s: float) -> None:
            pass

        with patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep):
            with pytest.raises(httpx.HTTPStatusError):
                await _retry_with_backoff(
                    _req, max_retries=3, base_delay=0.01, model="m"
                )
        assert calls["n"] == 1


# ---------------------------------------------------------------------------
# poll_video: transient 5xx must not kill the wait
# ---------------------------------------------------------------------------


class TestPollSurvivesTransient5xx:
    async def test_poll_continues_past_transient_500(self) -> None:
        status_calls = {"n": 0}

        async def fake_status(video_id: str, *, model_name: str | None = None) -> dict:
            status_calls["n"] += 1
            if status_calls["n"] < 3:
                raise _status_error(500, BODY_500)
            return {"status": "completed", "progress": 100, "url": "https://x/v.mp4"}

        async def fake_sleep(s: float) -> None:
            pass

        with (
            patch.object(agnes_client, "get_video_status", side_effect=fake_status),
            patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep),
        ):
            result = await poll_video("vid-1", max_wait_seconds=60, interval_seconds=1)

        assert result["status"] == "completed"
        assert status_calls["n"] == 3

    async def test_poll_backoff_is_monotonic_and_capped(self) -> None:
        status_calls = {"n": 0}
        sleeps: list[float] = []

        async def fake_status(video_id: str, *, model_name: str | None = None) -> dict:
            status_calls["n"] += 1
            if status_calls["n"] < 6:
                raise _status_error(503, BODY_500)
            return {"status": "completed", "progress": 100, "url": "https://x/v.mp4"}

        async def fake_sleep(s: float) -> None:
            sleeps.append(s)

        with (
            patch.object(agnes_client, "get_video_status", side_effect=fake_status),
            patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep),
        ):
            result = await poll_video("vid-1", max_wait_seconds=120, interval_seconds=1)

        assert result["status"] == "completed"
        assert len(sleeps) == 5
        assert sleeps == sorted(sleeps)  # was 20, 40, 10, 20, 40 (cycling %3)
        assert max(sleeps) <= 60

    async def test_poll_still_raises_for_4xx(self) -> None:
        async def fake_status(video_id: str, *, model_name: str | None = None) -> dict:
            raise _status_error(400, '{"code":"invalid_request"}')

        async def fake_sleep(s: float) -> None:
            pass

        with (
            patch.object(agnes_client, "get_video_status", side_effect=fake_status),
            patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await poll_video("vid-1", max_wait_seconds=5, interval_seconds=1)
