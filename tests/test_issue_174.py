"""Issue #174: `brandly gate-drift <project>` - pre-generation prompt drift check.

One text-model call over ALL shot prompts (+ style/aspect context) returns
structured drifts across campaigns; printed as a table (text) or JSON.
Exit codes: 0 = report only (or none found), 1 = --strict with a high
severity drift, 2 = error (bad response, API failure, no shots.json).

Read-only: never edits prompts. Fail-open to a clean error, no traceback.

Run under `.venv\\Scripts\\python` (editable install points at src/).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from brandly_cli.cli import cli


@pytest.fixture
def runner(tmp_path: Path) -> CliRunner:
    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    # Wide console so rich renders table cells on one unwrapped line.
    env["COLUMNS"] = "200"
    return CliRunner(env=env)


def _write_shots(root: Path, project_id: str = "my-project") -> Path:
    proj = root / ".brandly" / project_id
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "shots.json").write_text(
        json.dumps(
            {
                "character": "Nova, a chrome android",
                "acts": {
                    "act1": {
                        "style": "cyberpunk neon",
                        "shots": [
                            {
                                "id": "S01-Shot-1",
                                "prompt": "Nova walks the neon alley, rim light",
                            },
                            {
                                "id": "S01-Shot-2",
                                "prompt": "Nova at the noodle bar, warm key light",
                            },
                            {
                                "id": "S02-Shot-1",
                                "prompt": "A courier hands Nova a package",
                            },
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return proj


def _drift_payload(*, high: bool = True) -> dict:
    drifts = [
        {
            "shot_ids": ["S01-Shot-2"],
            "dimension": "character",
            "evidence": "Calls the character 'the girl' instead of Nova",
            "severity": "high" if high else "medium",
            "suggested_fix": "Replace 'the girl' with 'Nova' in the prompt",
        },
        {
            "shot_ids": ["S02-Shot-1"],
            "dimension": "lighting",
            "evidence": "Prompt says daylight; campaign is neon night",
            "severity": "low",
            "suggested_fix": "Use 'neon night, wet asphalt reflections'",
        },
    ]
    return {"drifts": drifts}


def _chat(payload: dict | str) -> AsyncMock:
    content = payload if isinstance(payload, str) else json.dumps(payload)
    return AsyncMock(return_value={"choices": [{"message": {"content": content}}]})


# ---------------------------------------------------------------------------
# Happy path: table + exit codes
# ---------------------------------------------------------------------------


def test_valid_drift_json_renders_table_exit_0(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_shots(tmp_path)
    chat = _chat(_drift_payload())
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = runner.invoke(cli, ["gate-drift", "my-project"])

    assert result.exit_code == 0, result.output
    chat.assert_awaited_once()
    assert "character" in result.output
    assert "Calls the character 'the girl' instead of Nova" in result.output
    assert "Replace 'the girl' with 'Nova'" in result.output
    assert "lighting" in result.output


def test_strict_high_drift_exits_1(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_shots(tmp_path)
    monkeypatch.setattr(
        "brandly_cli.agnes_client.chat_completion", _chat(_drift_payload(high=True))
    )

    result = runner.invoke(cli, ["gate-drift", "my-project", "--strict"])

    assert result.exit_code == 1, result.output
    assert "character" in result.output


def test_strict_without_high_drift_exits_0(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_shots(tmp_path)
    monkeypatch.setattr(
        "brandly_cli.agnes_client.chat_completion", _chat(_drift_payload(high=False))
    )

    result = runner.invoke(cli, ["gate-drift", "my-project", "--strict"])

    assert result.exit_code == 0, result.output


def test_no_drifts_message(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_shots(tmp_path)
    monkeypatch.setattr(
        "brandly_cli.agnes_client.chat_completion", _chat({"drifts": []})
    )

    result = runner.invoke(cli, ["gate-drift", "my-project"])

    assert result.exit_code == 0, result.output
    assert "No prompt drift" in result.output


def test_json_output_mode(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_shots(tmp_path)
    monkeypatch.setattr(
        "brandly_cli.agnes_client.chat_completion", _chat(_drift_payload())
    )

    result = runner.invoke(cli, ["gate-drift", "my-project", "-o", "json"])

    assert result.exit_code == 0, result.output
    assert '"drifts"' in result.output
    assert "S01-Shot-2" in result.output


# ---------------------------------------------------------------------------
# Fail-open: clean error, exit 2, no traceback
# ---------------------------------------------------------------------------


def test_malformed_response_exits_2_no_traceback(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_shots(tmp_path)
    monkeypatch.setattr(
        "brandly_cli.agnes_client.chat_completion",
        _chat("sorry, here is prose instead of json"),
    )

    result = runner.invoke(cli, ["gate-drift", "my-project"])

    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert "sorry, here is prose instead of json" in result.output  # response tail


def test_api_error_exits_2_no_traceback(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_shots(tmp_path)
    monkeypatch.setattr(
        "brandly_cli.agnes_client.chat_completion",
        AsyncMock(side_effect=RuntimeError("boom")),
    )

    result = runner.invoke(cli, ["gate-drift", "my-project"])

    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert "RuntimeError" in result.output


def test_missing_shots_json_exits_2(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chat = AsyncMock(side_effect=AssertionError("must not be called"))
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = runner.invoke(cli, ["gate-drift", "my-project"])

    assert result.exit_code == 2, result.output
    assert "shots.json" in result.output
    chat.assert_not_awaited()


def test_empty_shots_json_exits_2(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = tmp_path / ".brandly" / "my-project"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "shots.json").write_text("[]", encoding="utf-8")
    chat = AsyncMock(side_effect=AssertionError("must not be called"))
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = runner.invoke(cli, ["gate-drift", "my-project"])

    assert result.exit_code == 2, result.output
    chat.assert_not_awaited()


def test_help_lists_command(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["gate-drift", "--help"])

    assert result.exit_code == 0
    assert "--strict" in result.output
    assert "PROJECT" in result.output


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
