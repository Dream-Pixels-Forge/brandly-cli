"""Issue #171: gate --judge-model selection + multi-frame scene judging.

P1: ``brandly gate --judge-model`` threads a vision-judge model through
``verify_element`` into the single multimodal ``chat_completion`` call —
default stays DEFAULT_AGNES_TEXT_MODEL (no behavior change).

P2: ``brandly gate --judge-frames N`` (2-8, videos) sends N labeled frames
of a clip in ONE model call with a cross-frame consistency verdict, then
aggregates per-frame verdicts worst-case into the existing single-verdict
schema. The single-frame path stays the default and the fallback.

Run under `.venv\\Scripts\\python` (editable install points at src/).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from brandly_cli import quality_gate
from brandly_cli.cli import cli
from brandly_cli.constants import DEFAULT_AGNES_TEXT_MODEL

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def runner(tmp_path: Path) -> CliRunner:
    import os

    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _content_image(tmp_path: Path, name: str = "asset.png") -> Path:
    """A decodable image that passes the offline blank-guard (dark block)."""
    from PIL import Image

    p = tmp_path / name
    im = Image.new("RGB", (512, 288), (150, 150, 150))
    px = im.load()
    for x in range(200, 312):
        for y in range(80, 208):
            px[x, y] = (30, 30, 35)
    im.save(p)
    return p


def _pass_verdict() -> dict[str, Any]:
    return {
        "quality_score": 92,
        "slop": 1,
        "distortion": 0,
        "drift": None,
        "matte_background": True,
        "identity_bleed": False,
        "identity_bleed_detail": "",
        "issues": [],
        "verdict": "pass",
        "notes": "great",
    }


def _chat_returning(payload: dict[str, Any]) -> AsyncMock:
    return AsyncMock(return_value={"choices": [{"message": {"content": json.dumps(payload)}}]})


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# P1 — judge model selection
# ---------------------------------------------------------------------------


def test_verify_element_forwards_model_to_chat_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGNES_API_KEY", "test-key")
    img = _content_image(tmp_path)
    chat = _chat_returning(_pass_verdict())
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = _run(quality_gate.verify_element(img, model="agnes-3.0-flash", write_report=False))

    assert result.status == quality_gate.PASS
    chat.assert_awaited_once()
    assert chat.await_args.kwargs["model"] == "agnes-3.0-flash"


def test_verify_element_default_model_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGNES_API_KEY", "test-key")
    img = _content_image(tmp_path)
    chat = _chat_returning(_pass_verdict())
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    _run(quality_gate.verify_element(img, write_report=False))

    assert chat.await_args.kwargs["model"] == DEFAULT_AGNES_TEXT_MODEL


def test_gate_cmd_judge_model_reaches_chat(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGNES_API_KEY", "test-key")
    img = _content_image(tmp_path)
    chat = _chat_returning(_pass_verdict())
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = runner.invoke(
        cli, ["gate", "my-project", str(img), "-d", "a red widget", "--judge-model", "agnes-3.0-flash"]
    )

    assert result.exit_code == 0, result.output
    assert chat.await_args.kwargs["model"] == "agnes-3.0-flash"


def test_gate_cmd_default_model_unchanged(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGNES_API_KEY", "test-key")
    img = _content_image(tmp_path)
    chat = _chat_returning(_pass_verdict())
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = runner.invoke(cli, ["gate", "my-project", str(img), "-d", "a red widget"])

    assert result.exit_code == 0, result.output
    assert chat.await_args.kwargs["model"] == DEFAULT_AGNES_TEXT_MODEL


def test_gate_help_lists_judge_flags(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["gate", "--help"])

    assert result.exit_code == 0
    assert "--judge-model" in result.output
    assert "--judge-frames" in result.output


def test_gate_judge_frames_range_validated(runner: CliRunner) -> None:
    for bad in ("0", "9"):
        result = runner.invoke(cli, ["gate", "my-project", "x.mp4", "--judge-frames", bad])
        assert result.exit_code == 1, result.output
        assert "--judge-frames must be between 1 and 8" in result.output


# ---------------------------------------------------------------------------
# P2 — multi-frame vision check (one chat_completion call, N labeled frames)
# ---------------------------------------------------------------------------


def test_multiframe_single_call_carries_all_frames(tmp_path: Path) -> None:
    frames = [_content_image(tmp_path, f"f{i}.png") for i in (1, 2, 3)]
    ref = _content_image(tmp_path, "ref.png")
    chat = _chat_returning(
        {
            "frames": [
                {"frame": 1, "quality_score": 90, "verdict": "pass", "issues": []},
                {"frame": 2, "quality_score": 88, "verdict": "pass", "issues": []},
                {"frame": 3, "quality_score": 85, "verdict": "pass", "issues": []},
            ],
            "consistency": {"cross_frame_identity": 1, "issues": [], "verdict": "pass"},
            "notes": "stable",
        }
    )
    with patch("brandly_cli.agnes_client.chat_completion", chat):
        parsed = _run(
            quality_gate._run_vision_check_multi(
                frames,
                reference=ref,
                description="a hero shot",
                expect_matt_background=False,
                kind="video",
                model="agnes-3.0-flash",
            )
        )

    chat.assert_awaited_once()
    assert chat.await_args.kwargs["model"] == "agnes-3.0-flash"
    messages = chat.await_args.args[0]
    user_content = messages[1]["content"]
    # one leading text block + reference + 3 frames
    assert isinstance(user_content, list)
    assert len(user_content) == 5
    text = user_content[0]["text"]
    assert "REFERENCE" in text
    for i in (1, 2, 3):
        assert f"FRAME {i}" in text
    assert parsed["frames"][0]["frame"] == 1
    assert parsed["consistency"]["verdict"] == "pass"


def test_multiframe_without_reference_labels_only_frames(tmp_path: Path) -> None:
    frames = [_content_image(tmp_path, f"g{i}.png") for i in (1, 2)]
    chat = _chat_returning({"frames": [], "consistency": {}})
    with patch("brandly_cli.agnes_client.chat_completion", chat):
        _run(
            quality_gate._run_vision_check_multi(
                frames,
                reference=None,
                description="",
                expect_matt_background=False,
                kind="video",
                model="m",
            )
        )

    user_content = chat.await_args.args[0][1]["content"]
    assert len(user_content) == 3  # text + 2 frames, no reference
    assert "REFERENCE" not in user_content[0]["text"]


# ---------------------------------------------------------------------------
# P2 — aggregation (worst-case per metric, frame-prefixed issues)
# ---------------------------------------------------------------------------


def test_multi_aggregate_worst_case_across_frames() -> None:
    parsed = {
        "frames": [
            {"frame": 1, "quality_score": 92, "slop": 1, "distortion": 0, "drift": None,
             "verdict": "pass", "issues": []},
            {"frame": 2, "quality_score": 60, "slop": 4, "distortion": 3, "drift": None,
             "verdict": "warn", "issues": ["soft focus"]},
            {"frame": 3, "quality_score": 40, "slop": 7, "distortion": 7, "drift": None,
             "verdict": "fail", "issues": ["melted face"]},
        ],
        "consistency": {"cross_frame_identity": 2, "issues": [], "verdict": "pass"},
        "notes": "one bad frame",
    }

    agg = quality_gate._aggregate_multi_verdict(parsed)

    assert agg["quality_score"] == 40
    assert agg["slop"] == 7
    assert agg["distortion"] == 7
    assert agg["verdict"] == "fail"
    assert "frame 2: soft focus" in agg["issues"]
    assert "frame 3: melted face" in agg["issues"]
    assert agg["frames"] == parsed["frames"]
    assert agg["consistency"] == parsed["consistency"]

    result = quality_gate.GateResult(element="x", kind="video")
    quality_gate._apply_ai_verdict(
        result, agg, expect_matt_background=False, has_reference=False
    )
    result.finalize()
    assert result.status == quality_gate.FAIL
    assert result.score == 40


def test_multi_aggregate_consistency_issues_promote_to_fail() -> None:
    parsed = {
        "frames": [
            {"frame": 1, "quality_score": 95, "slop": 0, "distortion": 0,
             "verdict": "pass", "issues": []},
            {"frame": 2, "quality_score": 93, "slop": 0, "distortion": 0,
             "verdict": "pass", "issues": []},
        ],
        "consistency": {
            "cross_frame_identity": 8,
            "issues": ["character wardrobe changes between frames"],
            "verdict": "fail",
        },
        "notes": "",
    }

    agg = quality_gate._aggregate_multi_verdict(parsed)
    assert agg["verdict"] == "fail"
    assert any("consistency:" in i for i in agg["issues"])

    result = quality_gate.GateResult(element="x", kind="video")
    quality_gate._apply_ai_verdict(
        result, agg, expect_matt_background=False, has_reference=False
    )
    result.finalize()
    assert result.status == quality_gate.FAIL


def test_multi_aggregate_empty_returns_empty() -> None:
    assert quality_gate._aggregate_multi_verdict({}) == {}
    assert quality_gate._aggregate_multi_verdict({"frames": []}) == {}
    assert quality_gate._aggregate_multi_verdict("not a dict") == {}  # type: ignore[arg-type]


def test_multi_aggregate_identity_bleed_any_frame() -> None:
    parsed = {
        "frames": [
            {"frame": 1, "quality_score": 90, "slop": 0, "distortion": 0,
             "verdict": "pass", "issues": [], "identity_bleed": False},
            {"frame": 2, "quality_score": 90, "slop": 0, "distortion": 0,
             "verdict": "fail", "issues": [], "identity_bleed": True,
             "identity_bleed_detail": "face swapped at frame 2"},
        ],
        "consistency": {"verdict": "pass", "issues": []},
    }

    agg = quality_gate._aggregate_multi_verdict(parsed)
    assert agg["identity_bleed"] is True
    assert agg["identity_bleed_detail"] == "face swapped at frame 2"
    assert agg["verdict"] == "fail"


# ---------------------------------------------------------------------------
# P2 — verify_element wiring
# ---------------------------------------------------------------------------


def test_verify_element_multiframe_uses_multi_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGNES_API_KEY", "test-key")
    frame0 = _content_image(tmp_path, "frame0.png")
    extras = [_content_image(tmp_path, "e1.png"), _content_image(tmp_path, "e2.png")]
    multi_payload = {
        "frames": [
            {"frame": 1, "quality_score": 90, "slop": 1, "distortion": 0,
             "verdict": "pass", "issues": []},
        ],
        "consistency": {"verdict": "pass", "issues": []},
    }
    seen: dict[str, Any] = {}

    async def fake_multi(frames: list[Path], **kwargs: Any) -> dict[str, Any]:
        seen["frames"] = list(frames)
        seen["model"] = kwargs.get("model")
        return multi_payload

    monkeypatch.setattr(quality_gate, "_precheck", lambda result, path: frame0)
    monkeypatch.setattr(quality_gate, "_extra_video_frames", lambda v, n: extras)
    monkeypatch.setattr(quality_gate, "_run_vision_check_multi", fake_multi)
    monkeypatch.setattr(
        quality_gate,
        "_run_vision_check",
        AsyncMock(side_effect=AssertionError("single path must not run")),
    )

    result = _run(
        quality_gate.verify_element(
            tmp_path / "clip.mp4",
            judge_frames=3,
            model="agnes-3.0-flash",
            write_report=False,
        )
    )

    assert seen["frames"] == [frame0, *extras]
    assert seen["model"] == "agnes-3.0-flash"
    assert result.status == quality_gate.PASS
    assert result.checks["video_frames"]["status"] == quality_gate.PASS


def test_verify_element_default_uses_single_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGNES_API_KEY", "test-key")
    img = _content_image(tmp_path)
    single = AsyncMock(return_value=_pass_verdict())
    monkeypatch.setattr(quality_gate, "_run_vision_check", single)
    monkeypatch.setattr(
        quality_gate,
        "_run_vision_check_multi",
        AsyncMock(side_effect=AssertionError("multi path must not run by default")),
    )

    result = _run(quality_gate.verify_element(img, write_report=False))

    single.assert_awaited_once()
    assert result.status == quality_gate.PASS


def test_multiframe_ignored_for_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGNES_API_KEY", "test-key")
    img = _content_image(tmp_path)
    single = AsyncMock(return_value=_pass_verdict())
    monkeypatch.setattr(quality_gate, "_run_vision_check", single)
    monkeypatch.setattr(
        quality_gate,
        "_run_vision_check_multi",
        AsyncMock(side_effect=AssertionError("images are single-frame")),
    )

    _run(quality_gate.verify_element(img, judge_frames=3, write_report=False))

    single.assert_awaited_once()


def test_multiframe_falls_back_when_no_extra_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGNES_API_KEY", "test-key")
    frame0 = _content_image(tmp_path, "only.png")
    single = AsyncMock(return_value=_pass_verdict())
    monkeypatch.setattr(quality_gate, "_precheck", lambda result, path: frame0)
    monkeypatch.setattr(quality_gate, "_extra_video_frames", lambda v, n: [])
    monkeypatch.setattr(quality_gate, "_run_vision_check", single)
    monkeypatch.setattr(
        quality_gate,
        "_run_vision_check_multi",
        AsyncMock(side_effect=AssertionError("no extras -> single path")),
    )

    result = _run(
        quality_gate.verify_element(
            tmp_path / "clip.mp4", judge_frames=3, write_report=False
        )
    )

    single.assert_awaited_once()
    assert result.checks["video_frames"]["status"] == quality_gate.WARN


# ---------------------------------------------------------------------------
# P2 — frame extraction spacing (ffmpeg mocked)
# ---------------------------------------------------------------------------


def test_extra_video_frames_spreads_timestamps(tmp_path: Path, monkeypatch) -> None:
    video = tmp_path / "clip.mp4"
    monkeypatch.setattr(quality_gate, "_probe_video", lambda p: {"duration": 6.0})
    seen_ts: list[float] = []

    def fake_frame_at(v: Path, ts: float) -> Path | None:
        seen_ts.append(round(ts, 3))
        return tmp_path / f"t{len(seen_ts)}.png"

    monkeypatch.setattr(quality_gate, "_frame_at", fake_frame_at)

    extras = quality_gate._extra_video_frames(video, 3)

    assert len(extras) == 3
    assert seen_ts == [1.5, 3.0, 4.5]


def test_extra_video_frames_no_duration_returns_empty(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(quality_gate, "_probe_video", lambda p: None)
    monkeypatch.setattr(
        quality_gate,
        "_frame_at",
        lambda v, ts: (_ for _ in ()).throw(AssertionError("must not extract")),
    )

    assert quality_gate._extra_video_frames(tmp_path / "clip.mp4", 3) == []


def test_extra_video_frames_skips_failed_extraction(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(quality_gate, "_probe_video", lambda p: {"duration": 4.0})

    def fake_frame_at(v: Path, ts: float) -> Path | None:
        return None if ts >= 2.0 else tmp_path / "ok.png"

    monkeypatch.setattr(quality_gate, "_frame_at", fake_frame_at)

    extras = quality_gate._extra_video_frames(tmp_path / "clip.mp4", 3)

    assert len(extras) == 1  # only the t=1.0 extraction succeeded
