r"""Issue #221: an Agnes token failure (HTTP 401) prints a hint that points at
the wrong problem, and ``brandly agnes-chat`` leaks a raw traceback.

1. The reference-payload tip ("use --no-auto-refs / --auto-ref-category to
   slim the request further") is emitted on EVERY create failure — including
   a 401, which is an account/API-key problem a payload hint cannot affect,
   and whose advice would destroy the character references a project depends
   on if followed.
2. ``brandly agnes-chat`` lets the provider error propagate as a raw
   traceback through click internals instead of a short message and a
   non-zero exit.

Run under ``.venv\\Scripts\\python`` (editable install points at ``src/``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from click.testing import CliRunner

from brandly_cli.cli import cli
from brandly_cli.utils import generate_project_id


def _http_401() -> httpx.HTTPStatusError:
    req = httpx.Request("POST", "https://apihub.agnes-ai.com/v1/videos")
    resp = httpx.Response(
        401,
        request=req,
        json={
            "error": {
                "code": "",
                "message": "This token status is unavailable (request id: 1)",
                "type": "AgnesAI_error",
            }
        },
    )
    return httpx.HTTPStatusError(
        "Client error '401 Unauthorized' for url "
        "'https://apihub.agnes-ai.com/v1/videos'",
        request=req,
        response=resp,
    )


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
    proj_file.write_text(json.dumps({"id": project_id, "name": "Test"}))


def _ensure_plan(tmp_path: Path, project_id: str) -> None:
    plan_dir = tmp_path / ".brandly" / project_id / "docs" / "plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "production_plan.md").write_text(
        "| Plan | Asset | Shot ID | Model | Source | Status | Created | Updated |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )


class TestVideo401AuthMessage:
    def test_401_gets_auth_message_not_payload_tip(
        self, video_runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _ensure_plan(tmp_path, pid)

        def fake_create(prompt: str, **kwargs: Any) -> dict[str, Any]:
            raise _http_401()

        with patch("brandly_cli.cmd.generation.create_video_task", new=fake_create):
            result = video_runner.invoke(
                cli, ["video", pid, "-p", "hero walks", "--no-wait"]
            )
        assert result.exit_code != 0, result.output
        assert (
            "token" in result.output.lower()
        ), "a 401 must be reported as a token/auth problem"
        assert (
            "no-auto-refs" not in result.output
        ), "the reference-payload tip must NOT be emitted on a 401"
        assert (
            "not a payload problem" in result.output
        ), "the auth-specific message must say it is not a payload problem"

    def test_timeout_still_gets_payload_tip(
        self, video_runner: CliRunner, project_dir: Path, tmp_path: Path
    ) -> None:
        # Guard: the tip is still emitted on the statuses it is relevant to.
        pid = generate_project_id()
        _write_project(project_dir, pid)
        _ensure_plan(tmp_path, pid)

        def fake_create(prompt: str, **kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("Connection timed out after 30000ms")

        with patch("brandly_cli.cmd.generation.create_video_task", new=fake_create):
            result = video_runner.invoke(
                cli, ["video", pid, "-p", "hero walks", "--no-wait"]
            )
        assert result.exit_code != 0, result.output
        assert (
            "no-auto-refs" in result.output
        ), "the payload tip is still relevant on a timeout"


class TestAgnesChatCleanExit:
    def test_401_is_a_clean_exit_not_a_traceback(
        self, video_runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AGNES_API_KEY", "test-key")

        async def fake_chat(messages: Any, model: str = "", **kw: Any) -> dict[str, Any]:
            raise _http_401()

        monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", fake_chat)
        result = video_runner.invoke(
            cli, ["agnes-chat", "reply with the single word: pong"]
        )
        assert not isinstance(
            result.exception, httpx.HTTPStatusError
        ), "a provider error must not leak a traceback through click internals"
        assert result.exit_code == 1, result.output
        assert "401" in result.output
