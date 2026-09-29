"""Issue #170: opt-in LLM prompt enhancement (--llm-enhance) for image/video.

The deterministic prompt pipeline (style presets, sheet hints, reference
notes) stays the default. With --llm-enhance the assembled prompt gets ONE
polish pass through an Agnes text model with a preservation contract
(subject/instructions, <Picture N>/<Audio N> binding tokens, aspect/duration
statements). Any failure or lost binding token falls back to the
deterministic prompt (fail-open).

Run under `.venv\\Scripts\\python` (editable install points at src/).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from brandly_cli.cli import cli
from brandly_cli.utils import generate_project_id

# ---------------------------------------------------------------------------
# Helpers (image harness: --root, stop-at-generate fakes)
# ---------------------------------------------------------------------------


def _image(tmp_path: Path, *args: str) -> object:
    return CliRunner().invoke(cli, ["--root", str(tmp_path), "image", *args])


def _install_stopping_generate(monkeypatch: pytest.MonkeyPatch, captured: dict[str, str]):
    """generate_image that records the prompt it received, then aborts.

    Aborting avoids the download/result handling paths — the prompt handed
    to the provider call is the artifact under test (issue #170).
    """

    async def fake_generate(prompt: str, *, model: str, size: str, ratio: str) -> dict[str, Any]:
        captured["prompt"] = prompt
        raise RuntimeError("stop-here (issue #170 probe)")

    monkeypatch.setattr("brandly_cli.cmd.generation.generate_image", fake_generate)


def _install_stopping_create_video(monkeypatch: pytest.MonkeyPatch, captured: dict[str, str]):
    async def fake_create(prompt: str, **kwargs: Any) -> dict[str, Any]:
        captured["prompt"] = prompt
        raise RuntimeError("stop-here (issue #170 probe)")

    monkeypatch.setattr("brandly_cli.cmd.generation.create_video_task", fake_create)


# ---------------------------------------------------------------------------
# Video harness (copied pattern from test_production_plan.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    return tmp_path / ".brandly"


@pytest.fixture
def video_runner(tmp_path: Path) -> CliRunner:
    import os

    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


def _write_project(project_dir: Path, project_id: str) -> None:
    proj_file = project_dir / project_id / "project.json"
    proj_file.parent.mkdir(parents=True, exist_ok=True)
    proj_file.write_text(
        json.dumps(
            {
                "id": project_id,
                "name": "Test Project",
                "description": "A test product description",
                "status": "pending",
                "current_phase": "asset",
                "style": "cinematic",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "phases": {},
            }
        )
    )


def _ensure_plan(tmp_path: Path, project_id: str) -> None:
    plan_dir = tmp_path / ".brandly" / project_id / "docs" / "plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "production_plan.md").write_text(
        "| Plan | Asset | Shot ID | Model | Source | Status | Created | Updated |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )


# ---------------------------------------------------------------------------
# Unit: llm_enhance_prompt (fail-open contract)
# ---------------------------------------------------------------------------


def _ok_response(content: str) -> dict[str, Any]:
    return {"choices": [{"message": {"content": content}}]}


async def test_enhance_returns_model_text(monkeypatch: pytest.MonkeyPatch) -> None:
    from brandly_cli import prompt_enhance

    chat = AsyncMock(return_value=_ok_response("  polished prompt text  "))
    monkeypatch.setattr(prompt_enhance, "chat_completion", chat)

    out = await prompt_enhance.llm_enhance_prompt(
        "a ceramic mug on oak table", context="command=image; ratio=1:1"
    )

    assert out == "polished prompt text"
    chat.assert_awaited_once()
    messages = chat.await_args.args[0]
    assert messages[0]["role"] == "system"
    assert "<Picture N>" in messages[0]["content"]
    assert "<Audio N>" in messages[0]["content"]
    assert "a ceramic mug on oak table" in messages[1]["content"]
    assert "command=image; ratio=1:1" in messages[1]["content"]


async def test_enhance_forwards_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    from brandly_cli import prompt_enhance

    chat = AsyncMock(return_value=_ok_response("x"))
    monkeypatch.setattr(prompt_enhance, "chat_completion", chat)

    await prompt_enhance.llm_enhance_prompt("p", model="agnes-3.0-flash")

    assert chat.await_args.kwargs["model"] == "agnes-3.0-flash"


async def test_enhance_falls_back_on_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from brandly_cli import prompt_enhance

    monkeypatch.setattr(prompt_enhance, "chat_completion", AsyncMock(side_effect=RuntimeError("boom")))

    assert await prompt_enhance.llm_enhance_prompt("p") is None


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {}}]},
        _ok_response(""),
        _ok_response("   "),
        _ok_response(123),  # type: ignore[arg-type]
    ],
)
async def test_enhance_falls_back_on_malformed_response(
    monkeypatch: pytest.MonkeyPatch, response: dict[str, Any]
) -> None:
    from brandly_cli import prompt_enhance

    monkeypatch.setattr(prompt_enhance, "chat_completion", AsyncMock(return_value=response))

    assert await prompt_enhance.llm_enhance_prompt("p") is None


async def test_enhance_rejects_lost_binding_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    from brandly_cli import prompt_enhance

    base = "hero walks <Picture 1> while score plays <Audio 2>"

    keep = AsyncMock(return_value=_ok_response(f"cinematic {base} wide shot"))
    monkeypatch.setattr(prompt_enhance, "chat_completion", keep)
    assert await prompt_enhance.llm_enhance_prompt(base) is not None

    drop_audio = AsyncMock(return_value=_ok_response("cinematic hero <Picture 1> wide shot"))
    monkeypatch.setattr(prompt_enhance, "chat_completion", drop_audio)
    assert await prompt_enhance.llm_enhance_prompt(base) is None

    drop_all = AsyncMock(return_value=_ok_response("cinematic hero walks wide shot"))
    monkeypatch.setattr(prompt_enhance, "chat_completion", drop_all)
    assert await prompt_enhance.llm_enhance_prompt(base) is None


async def test_enhance_without_tokens_accepts_any_output(monkeypatch: pytest.MonkeyPatch) -> None:
    from brandly_cli import prompt_enhance

    monkeypatch.setattr(prompt_enhance, "chat_completion", AsyncMock(return_value=_ok_response("new text <Picture 9>")))

    assert await prompt_enhance.llm_enhance_prompt("plain prompt") == "new text <Picture 9>"


# ---------------------------------------------------------------------------
# CLI wiring: brandly image
# ---------------------------------------------------------------------------


def test_image_help_lists_llm_flags(tmp_path: Path) -> None:
    result = _image(tmp_path, "--help")

    assert result.exit_code == 0
    assert "--llm-enhance" in result.output
    assert "--llm-model" in result.output


def test_image_without_flag_never_calls_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, str] = {}
    _install_stopping_generate(monkeypatch, captured)
    enhance = AsyncMock(side_effect=AssertionError("model must not be called"))
    monkeypatch.setattr("brandly_cli.prompt_enhance.llm_enhance_prompt", enhance)

    result = _image(tmp_path, "-p", "a ceramic mug on oak table")

    assert result.exit_code == 1  # stop-here probe aborts after capture
    assert "stop-here" in result.output
    assert captured["prompt"] == "a ceramic mug on oak table"
    enhance.assert_not_awaited()


def test_image_flag_uses_model_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}
    _install_stopping_generate(monkeypatch, captured)
    monkeypatch.setattr(
        "brandly_cli.prompt_enhance.llm_enhance_prompt",
        AsyncMock(return_value="ENHANCED PROMPT"),
    )

    result = _image(tmp_path, "-p", "a ceramic mug", "--llm-enhance")

    assert result.exit_code == 1
    assert captured["prompt"] == "ENHANCED PROMPT"
    assert "Prompt enhanced via LLM" in result.output


def test_image_flag_falls_back_when_model_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, str] = {}
    _install_stopping_generate(monkeypatch, captured)
    monkeypatch.setattr(
        "brandly_cli.prompt_enhance.llm_enhance_prompt",
        AsyncMock(return_value=None),
    )

    result = _image(tmp_path, "-p", "a ceramic mug", "--llm-enhance")

    assert result.exit_code == 1
    assert captured["prompt"] == "a ceramic mug"
    assert "LLM enhancement unavailable" in result.output


# ---------------------------------------------------------------------------
# CLI wiring: brandly video
# ---------------------------------------------------------------------------


def test_video_help_lists_llm_flags(video_runner: CliRunner) -> None:
    result = video_runner.invoke(cli, ["video", "--help"])

    assert result.exit_code == 0
    assert "--llm-enhance" in result.output
    assert "--llm-model" in result.output


def test_video_without_flag_never_calls_model(
    video_runner: CliRunner, project_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = generate_project_id()
    _write_project(project_dir, pid)
    _ensure_plan(tmp_path, pid)
    captured: dict[str, str] = {}
    _install_stopping_create_video(monkeypatch, captured)
    enhance = AsyncMock(side_effect=AssertionError("model must not be called"))
    monkeypatch.setattr("brandly_cli.prompt_enhance.llm_enhance_prompt", enhance)

    result = video_runner.invoke(
        cli, ["video", pid, "-p", "hero walks through neon alley", "--no-wait"]
    )

    assert result.exit_code == 1
    assert "stop-here" in result.output
    assert "hero walks through neon alley" in captured["prompt"]
    enhance.assert_not_awaited()


def test_video_flag_uses_model_prompt(
    video_runner: CliRunner, project_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = generate_project_id()
    _write_project(project_dir, pid)
    _ensure_plan(tmp_path, pid)
    captured: dict[str, str] = {}
    _install_stopping_create_video(monkeypatch, captured)
    monkeypatch.setattr(
        "brandly_cli.prompt_enhance.llm_enhance_prompt",
        AsyncMock(return_value="ENHANCED VIDEO PROMPT"),
    )

    result = video_runner.invoke(
        cli,
        ["video", pid, "-p", "hero walks through neon alley", "--no-wait", "--llm-enhance"],
    )

    assert result.exit_code == 1
    assert captured["prompt"] == "ENHANCED VIDEO PROMPT"
    assert "Prompt enhanced via LLM" in result.output


def test_video_flag_falls_back_when_model_fails(
    video_runner: CliRunner, project_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = generate_project_id()
    _write_project(project_dir, pid)
    _ensure_plan(tmp_path, pid)
    captured: dict[str, str] = {}
    _install_stopping_create_video(monkeypatch, captured)
    monkeypatch.setattr(
        "brandly_cli.prompt_enhance.llm_enhance_prompt",
        AsyncMock(return_value=None),
    )

    result = video_runner.invoke(
        cli,
        ["video", pid, "-p", "hero walks through neon alley", "--no-wait", "--llm-enhance"],
    )

    assert result.exit_code == 1
    assert "hero walks through neon alley" in captured["prompt"]
    assert "LLM enhancement unavailable" in result.output
