"""Issue #173: `brandly gate --explain` - text-model diagnosis of gate failures.

Opt-in flag on the element gate: after the report, ONE text-model call
turns the structured gate result (+ optional shot prompt + recent
progress-log lines) into per-failure diagnoses with copy-pasteable
suggested commands. Read-only and fail-open: flag off = no call, flag on
with API error / malformed JSON = report unchanged + dim note.

Run under `.venv\\Scripts\\python` (editable install points at src/).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from brandly_cli import quality_gate
from brandly_cli.cli import cli

# ---------------------------------------------------------------------------
# Helpers / fixtures
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


def _failing_element(tmp_path: Path) -> Path:
    """Zero-byte file: deterministic pre-check FAIL, no vision call."""
    p = tmp_path / "broken.png"
    p.write_bytes(b"")
    return p


def _pass_vision() -> dict[str, Any]:
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


def _diagnoses_payload() -> dict[str, Any]:
    return {
        "diagnoses": [
            {
                "shot_id": "broken.png",
                "likely_cause": "The element file is empty so the pre-check failed.",
                "suggested_change": "Regenerate the asset; the previous upload wrote 0 bytes.",
                "suggested_command": "brandly image my-project -d 'a red widget'",
            }
        ]
    }


def _chat_returning(payload: dict[str, Any] | str) -> AsyncMock:
    content = payload if isinstance(payload, str) else json.dumps(payload)
    return AsyncMock(return_value={"choices": [{"message": {"content": content}}]})


# ---------------------------------------------------------------------------
# Flag off -> no call, unchanged output
# ---------------------------------------------------------------------------


def test_flag_off_makes_no_api_call(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    element = _failing_element(tmp_path)
    chat = AsyncMock(side_effect=AssertionError("must not be called without --explain"))
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = runner.invoke(cli, ["gate", "my-project", str(element)])

    assert result.exit_code == 2, result.output
    assert "GATE FAIL" in result.output
    assert "AI explanation" not in result.output
    chat.assert_not_awaited()


def test_help_lists_explain(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["gate", "--help"])

    assert result.exit_code == 0
    assert "--explain" in result.output


# ---------------------------------------------------------------------------
# Flag on -> diagnoses rendered, exit code unchanged
# ---------------------------------------------------------------------------


def test_flag_on_renders_diagnoses(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    element = _failing_element(tmp_path)
    chat = _chat_returning(_diagnoses_payload())
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = runner.invoke(
        cli, ["gate", "my-project", str(element), "--explain"]
    )

    assert result.exit_code == 2, result.output
    assert "AI explanation" in result.output
    assert "The element file is empty" in result.output
    assert "Regenerate the asset" in result.output
    assert "brandly image my-project -d 'a red widget'" in result.output
    chat.assert_awaited_once()


def test_flag_on_invalid_json_falls_back(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    element = _failing_element(tmp_path)
    chat = _chat_returning("this is not json at all")
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = runner.invoke(
        cli, ["gate", "my-project", str(element), "--explain"]
    )

    assert result.exit_code == 2, result.output
    assert "GATE FAIL" in result.output  # report unchanged
    assert "Explanation unavailable" in result.output
    assert "AI explanation" not in result.output


def test_flag_on_api_error_falls_back(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    element = _failing_element(tmp_path)
    chat = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = runner.invoke(
        cli, ["gate", "my-project", str(element), "--explain"]
    )

    assert result.exit_code == 2, result.output
    assert "GATE FAIL" in result.output
    assert "Explanation unavailable (RuntimeError)" in result.output


def test_clean_gate_skips_explain_call(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PASS has no issues/warnings: only the gate's own vision call runs."""
    monkeypatch.setenv("AGNES_API_KEY", "test-key")
    img = _content_image(tmp_path)
    chat = _chat_returning(_pass_vision())
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = runner.invoke(
        cli, ["gate", "my-project", str(img), "-d", "a red widget", "--explain"]
    )

    assert result.exit_code == 0, result.output
    assert "Nothing to explain" in result.output
    assert chat.await_count == 1  # vision check only


# ---------------------------------------------------------------------------
# JSON mode
# ---------------------------------------------------------------------------


def test_json_mode_includes_explain_key(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    element = _failing_element(tmp_path)
    chat = _chat_returning(_diagnoses_payload())
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = runner.invoke(
        cli, ["gate", "my-project", str(element), "--explain", "-o", "json"]
    )

    assert result.exit_code == 2, result.output
    assert '"explain"' in result.output
    assert "The element file is empty" in result.output


def test_json_mode_error_keeps_valid_json(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    element = _failing_element(tmp_path)
    chat = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = runner.invoke(
        cli, ["gate", "my-project", str(element), "--explain", "-o", "json"]
    )

    assert result.exit_code == 2, result.output
    assert '"explain_error"' in result.output
    assert "RuntimeError" in result.output


# ---------------------------------------------------------------------------
# Context gathering + read-only guarantee (unit level)
# ---------------------------------------------------------------------------


def test_context_includes_shot_prompt_and_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = tmp_path / ".brandly" / "my-project"
    (proj / "docs" / "tmp").mkdir(parents=True)
    (proj / "shots.json").write_text(
        json.dumps(
            [
                {
                    "id": "Scene-01-Shot-1-1",
                    "prompt": "a red widget on marble, rim light",
                }
            ]
        ),
        encoding="utf-8",
    )
    (proj / "docs" / "tmp" / "produce_progress.txt").write_text(
        "2026-09-29T00:00:00Z Scene-01-Shot-1-1 RETRY exit=1 retry=2 "
        "backoff=60s generation error: 503\n",
        encoding="utf-8",
    )
    element = tmp_path / "media" / "Scene-01-Shot-1-1.mp4"
    result = quality_gate.GateResult(element=str(element), kind="video")
    result.add_issue("Severe distortion detected by AI review (score 7/10)")

    chat = _chat_returning({"diagnoses": []})
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    from brandly_cli.cmd.gate import _explain_gate

    diags, err = _explain_gate(tmp_path, "my-project", element, result)

    assert err is None
    chat.assert_awaited_once()
    user_content = chat.await_args.args[0][1]["content"]
    assert "a red widget on marble, rim light" in user_content
    assert "generation error: 503" in user_content


def test_explain_writes_no_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    element = tmp_path / "asset.mp4"
    result = quality_gate.GateResult(element=str(element), kind="video")
    result.add_issue("Output looks like generic AI slop (slop 8/10)")

    chat = _chat_returning(_diagnoses_payload())
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    def tree() -> list[str]:
        return sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))

    from brandly_cli.cmd.gate import _explain_gate

    before = tree()
    _explain_gate(tmp_path, "my-project", element, result)
    after = tree()

    assert before == after
    chat.assert_awaited_once()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
