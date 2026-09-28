"""Issue #124: min spacing between video creates across retries + park after N consecutive failed shots.

Observed in a 6-hour 503/429 window: internal 503 backoffs (2s-120s) plus
shot retries kept two video creates inside the provider's 1/min window, so
the CLI's own retry storm re-tripped the limiter - the only two successful
creates in the window both came after 60+ minutes of zero create attempts.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from brandly_cli import agnes_client, shot_runner

# ---------------------------------------------------------------------------
# Create-spacing guard
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_spacing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agnes_client, "_LAST_VIDEO_CREATE_AT", None)
    monkeypatch.setattr(agnes_client, "MIN_VIDEO_CREATE_GAP_SECONDS", 0.0)
    monkeypatch.setenv("AGNES_API_KEY", "k")
    monkeypatch.setenv("AGNES_BASE_URL", "https://test-api.example.com/v1")


async def test_first_create_never_sleeps() -> None:
    sleeps: list[float] = []

    async def fake_sleep(s: float) -> None:
        sleeps.append(s)

    with patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep):
        await agnes_client._enforce_video_create_spacing()
    assert sleeps == []


async def test_second_create_inside_gap_sleeps_the_remainder() -> None:
    sleeps: list[float] = []

    async def fake_sleep(s: float) -> None:
        sleeps.append(s)

    with (
        patch.object(agnes_client, "MIN_VIDEO_CREATE_GAP_SECONDS", 60.0),
        patch.object(agnes_client.asyncio, "sleep", side_effect=fake_sleep),
    ):
        await agnes_client._enforce_video_create_spacing()  # first: no sleep
        await agnes_client._enforce_video_create_spacing()  # second: ~60s
    assert len(sleeps) == 1
    assert sleeps[0] >= 55.0


async def test_create_video_task_enforces_spacing_on_every_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    async def fake_guard(gap: float | None = None) -> None:
        calls.append(1)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"id": "t1", "status": "pending"}
    resp.raise_for_status.return_value = None
    resp.headers = {}
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(agnes_client, "_enforce_video_create_spacing", side_effect=fake_guard),
        patch.object(agnes_client.httpx, "AsyncClient", return_value=ctx),
    ):
        await agnes_client.create_video_task("a shot")
    assert calls == [1]


# ---------------------------------------------------------------------------
# Park after N consecutive failed shots (compose with --continue-on-fail)
# ---------------------------------------------------------------------------

def _shots(ids: list[str]) -> list[shot_runner.Shot]:
    return [
        shot_runner.Shot(
            id=sid, act="", style="cinematic", folder="scenes",
            prompt=f"p {sid}", duration=5,
        )
        for sid in ids
    ]


def _config(tmp_path: Path, shots, generate_one, park_after: int) -> shot_runner.RunnerConfig:  # type: ignore[no-untyped-def]
    scenes = tmp_path / "videos" / "scenes"
    scenes.mkdir(parents=True, exist_ok=True)
    progress = shot_runner.ProgressLog(tmp_path / "docs" / "tmp" / "produce_progress.txt")
    return shot_runner.RunnerConfig(
        shots=shots,
        generate_one=generate_one,
        scenes_dir=scenes,
        progress=progress,
        interval=0.0,
        continue_on_fail=True,
        park_after_consecutive_failures=park_after,
    )


def _gen(result_for: dict, default: bool = True):  # type: ignore[no-untyped-def]
    def generate_one(shot):  # type: ignore[no-untyped-def]
        ok = result_for.get(shot.id, default)
        return (True, 0, "") if ok else (False, 1, "503")
    return generate_one


def test_park_after_two_consecutive_failures(tmp_path: Path) -> None:
    shots = _shots(["s1", "s2", "s3", "s4"])
    config = _config(tmp_path, shots, _gen({"s1": False, "s2": False}), park_after=2)
    messages: list[str] = []
    config.say = messages.append
    rc = shot_runner.run_shots(config)
    assert rc == 1
    assert any("PARK" in m for m in messages)
    # s3/s4 were never attempted
    assert not any("s3 " in m or "s4 " in m for m in messages)


def test_success_resets_the_consecutive_counter(tmp_path: Path) -> None:
    shots = _shots(["s1", "s2", "s3", "s4", "s5"])
    # fail, fail, success, fail, fail -> never 3 consecutive -> no park
    config = _config(
        tmp_path, shots, _gen({"s1": False, "s2": False, "s4": False, "s5": False}),
        park_after=3,
    )
    messages: list[str] = []
    config.say = messages.append
    rc = shot_runner.run_shots(config)
    assert rc == 1  # failures happened, but no early park
    assert not any("PARK" in m for m in messages)
    assert any("s5" in m for m in messages)  # the run reached the end


def test_park_disabled_when_zero(tmp_path: Path) -> None:
    shots = _shots(["s1", "s2", "s3"])
    config = _config(tmp_path, shots, _gen({"s1": False, "s2": False, "s3": False}), park_after=0)
    messages: list[str] = []
    config.say = messages.append
    rc = shot_runner.run_shots(config)
    assert rc == 1
    assert not any("PARK" in m for m in messages)


def test_park_message_suggests_resume(tmp_path: Path) -> None:
    shots = _shots(["s1", "s2"])
    config = _config(tmp_path, shots, _gen({"s1": False, "s2": False}), park_after=2)
    messages: list[str] = []
    config.say = messages.append
    shot_runner.run_shots(config)
    park_lines = [m for m in messages if "PARK" in m]
    assert park_lines
    assert any("resume" in m.lower() for m in park_lines)
