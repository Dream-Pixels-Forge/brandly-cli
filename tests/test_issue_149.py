"""Issue #149: retry loop sleeps after the final attempt; exhausted messages lie.

Three defects in ``_retry_with_backoff`` and its callers:

1. The loop computes a backoff and ``await asyncio.sleep(...)`` **after the
   last failed attempt** before raising — up to ~64-120 s of dead waiting on
   the video-create endpoint after the run has already failed.
2. After retries are exhausted, callers still print "The retry logic will
   wait and retry." / "Will retry shortly..." — there is no retry left.
3. The exhaustion path prints only ``str(HTTPStatusError)`` (status line):
   the response body and the Agnes ``request id`` are dropped, so the log
   can't be handed to support.

Fix: sleep only between attempts, and print
"gave up after N attempts over X.Xs" + body + request id on exhaustion.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from brandly_cli import agnes_client
from brandly_cli.agnes_client import _retry_with_backoff, create_video_task, generate_image

ALWAYS_503_BODY = json.dumps(
    {
        "error": {
            "code": "service_unavailable",
            "message": "upstream unavailable (request id: REQ123ABC456)",
            "type": "AgnesAI_error",
        }
    }
)


def _status_error(status: int, text: str) -> httpx.HTTPStatusError:
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    resp.headers = {}
    return httpx.HTTPStatusError(
        f"HTTP {status}", request=MagicMock(), response=resp
    )


def _always(status: int, text: str) -> tuple:
    calls = {"n": 0}

    async def _req() -> dict:
        calls["n"] += 1
        raise _status_error(status, text)

    return _req, calls


def _console_out(console: MagicMock) -> str:
    return " ".join(str(c) for c in console.print.call_args_list)


# ---------------------------------------------------------------------------
# No sleep after the final attempt
# ---------------------------------------------------------------------------


class TestNoFinalSleep:
    @pytest.mark.parametrize("status", [429, 500, 503])
    async def test_sleeps_only_between_attempts(self, status: int) -> None:
        sleeps: list[float] = []
        req, calls = _always(status, ALWAYS_503_BODY)

        async def fake_sleep(s: float) -> None:
            sleeps.append(s)

        with patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep):
            with pytest.raises(httpx.HTTPStatusError):
                await _retry_with_backoff(
                    req, max_retries=3, base_delay=0.01, model="m"
                )

        assert calls["n"] == 4  # max_retries + 1 attempts
        assert len(sleeps) == 3  # ...but only max_retries sleeps (no final one)

    async def test_timeout_path_skips_final_sleep(self) -> None:
        sleeps: list[float] = []
        calls = {"n": 0}

        async def _req() -> dict:
            calls["n"] += 1
            raise httpx.TimeoutException("timeout")

        async def fake_sleep(s: float) -> None:
            sleeps.append(s)

        with patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep):
            with pytest.raises(httpx.TimeoutException):
                await _retry_with_backoff(_req, max_retries=3, base_delay=0.01)

        assert calls["n"] == 4
        assert len(sleeps) == 3


# ---------------------------------------------------------------------------
# Exhaustion message: attempts, elapsed, body, request id
# ---------------------------------------------------------------------------


class TestExhaustedMessage:
    async def test_message_carries_attempts_elapsed_body_request_id(self) -> None:
        req, _ = _always(503, ALWAYS_503_BODY)
        console = MagicMock()

        async def fake_sleep(s: float) -> None:
            pass

        with (
            patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep),
            patch.object(agnes_client, "console", console),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await _retry_with_backoff(
                    req, max_retries=2, base_delay=0.01, model="m"
                )

        out = _console_out(console)
        assert "gave up after" in out
        assert "attempts" in out
        assert "over " in out and "s" in out
        assert "REQ123ABC456" in out  # request id reaches the log
        assert "upstream unavailable" in out  # body reaches the log


# ---------------------------------------------------------------------------
# Callers: no post-hoc "will retry" lies after exhaustion
# ---------------------------------------------------------------------------


def _failing_async_client(status: int, text: str, calls: dict) -> MagicMock:
    """AsyncClient context whose verbs always raise HTTPStatusError(status)."""

    async def _call(*args: object, **kwargs: object) -> MagicMock:
        calls["n"] += 1
        raise _status_error(status, text)

    client = AsyncMock()
    client.post = _call
    client.get = _call
    client.delete = _call
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestNoPostHocRetryPromises:
    async def test_create_video_task_503_does_not_promise_retry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AGNES_API_KEY", "k")
        monkeypatch.setenv("AGNES_BASE_URL", "https://test-api.example.com/v1")
        monkeypatch.setattr(agnes_client, "_LAST_VIDEO_CREATE_AT", None)
        monkeypatch.setattr(agnes_client, "MIN_VIDEO_CREATE_GAP_SECONDS", 0.0)
        calls = {"n": 0}
        console = MagicMock()

        async def fake_sleep(s: float) -> None:
            pass

        with (
            patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep),
            patch.object(agnes_client, "console", console),
            patch.object(
                agnes_client.httpx,
                "AsyncClient",
                return_value=_failing_async_client(503, ALWAYS_503_BODY, calls),
            ),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await create_video_task("a shot")

        out = _console_out(console)
        assert "retry logic will wait" not in out
        assert "Will retry shortly" not in out

    async def test_get_video_status_503_does_not_promise_retry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AGNES_API_KEY", "k")
        monkeypatch.setenv("AGNES_BASE_URL", "https://test-api.example.com/v1")
        console = MagicMock()

        async def fake_sleep(s: float) -> None:
            pass

        with (
            patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep),
            patch.object(agnes_client, "console", console),
            patch.object(
                agnes_client.httpx,
                "AsyncClient",
                return_value=_failing_async_client(503, ALWAYS_503_BODY, {"n": 0}),
            ),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await agnes_client.get_video_status("vid-1")

        out = _console_out(console)
        assert "Service unavailable. Will retry shortly" not in out

    async def test_generate_image_503_does_not_promise_retry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AGNES_API_KEY", "k")
        monkeypatch.setenv("AGNES_BASE_URL", "https://test-api.example.com/v1")
        console = MagicMock()

        async def fake_sleep(s: float) -> None:
            pass

        with (
            patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep),
            patch.object(agnes_client, "console", console),
            patch.object(
                agnes_client.httpx,
                "AsyncClient",
                return_value=_failing_async_client(503, ALWAYS_503_BODY, {"n": 0}),
            ),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await generate_image("a cat")

        out = _console_out(console)
        assert "temporarily unavailable. Please try again later" not in out

    async def test_chat_503_does_not_promise_retry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AGNES_API_KEY", "k")
        monkeypatch.setenv("AGNES_BASE_URL", "https://test-api.example.com/v1")
        console = MagicMock()

        async def fake_sleep(s: float) -> None:
            pass

        with (
            patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep),
            patch.object(agnes_client, "console", console),
            patch.object(
                agnes_client.httpx,
                "AsyncClient",
                return_value=_failing_async_client(503, ALWAYS_503_BODY, {"n": 0}),
            ),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await agnes_client.chat_completion([{"role": "user", "content": "hi"}])

        out = _console_out(console)
        assert "chat API temporarily unavailable" not in out
