"""Issue #151: fail fast on create-side 503 — 3 spaced attempts, then park.

``create_video_task`` ran ``max_retries=5`` (=> 6 attempts), and every
attempt is forced >= 60 s apart by the #124 spacing guard. On a sustained
503 outage that burns **6+ minutes per shot inside the client**, before the
shot-level retries and the inter-shot interval even start.

Decision (user-confirmed): fail fast + park — **3 attempts (~3 min max)**,
then an accurate error; long outages are handled by ``--park-after``
(default 3 consecutive failed shots) which parks with a resume hint.

The 60 s spacing guard itself is an invariant and must survive this change.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from brandly_cli import agnes_client
from brandly_cli.agnes_client import create_video_task

BODY_503 = json.dumps(
    {
        "error": {
            "code": "service_unavailable",
            "message": "upstream unavailable (request id: REQ511)",
            "type": "AgnesAI_error",
        }
    }
)


def _failing_client(calls: dict) -> MagicMock:
    """AsyncClient context whose POST always raises 503."""
    resp = MagicMock()
    resp.status_code = 503
    resp.text = BODY_503
    resp.headers = {}

    async def _post(*args: object, **kwargs: object) -> MagicMock:
        calls["n"] += 1
        e = httpx.HTTPStatusError(
            "HTTP 503", request=MagicMock(), response=resp
        )
        raise e

    client = AsyncMock()
    client.post = _post
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGNES_API_KEY", "k")
    monkeypatch.setenv("AGNES_BASE_URL", "https://test-api.example.com/v1")
    monkeypatch.setattr(agnes_client, "_LAST_VIDEO_CREATE_AT", None)
    monkeypatch.setattr(agnes_client, "MIN_VIDEO_CREATE_GAP_SECONDS", 60.0)


class TestCreate503Budget:
    async def test_exactly_three_attempts(self) -> None:
        calls = {"n": 0}
        console = MagicMock()

        async def fake_sleep(s: float) -> None:
            pass

        with (
            patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep),
            patch.object(agnes_client, "console", console),
            patch.object(
                agnes_client.httpx, "AsyncClient", return_value=_failing_client(calls)
            ),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await create_video_task("a shot")

        assert calls["n"] == 3  # was 6 (max_retries=5)

    async def test_60s_spacing_survives_the_smaller_budget(self) -> None:
        """Issue #124 invariant: no two create attempts < 60 s apart."""
        calls = {"n": 0}
        sleeps: list[float] = []

        async def fake_sleep(s: float) -> None:
            sleeps.append(s)

        with (
            patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep),
            patch.object(
                agnes_client.httpx, "AsyncClient", return_value=_failing_client(calls)
            ),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await create_video_task("a shot")

        assert calls["n"] == 3
        gap_sleeps = [s for s in sleeps if s >= 55.0]
        assert len(gap_sleeps) == 2  # attempt 2 and 3 waited out the window

    async def test_exhausted_message_points_at_park_and_resume(self) -> None:
        calls = {"n": 0}
        console = MagicMock()

        async def fake_sleep(s: float) -> None:
            pass

        with (
            patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep),
            patch.object(agnes_client, "console", console),
            patch.object(
                agnes_client.httpx, "AsyncClient", return_value=_failing_client(calls)
            ),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await create_video_task("a shot")

        out = " ".join(str(c) for c in console.print.call_args_list)
        assert "park-after" in out
        assert "gave up after 3 attempts" in out
