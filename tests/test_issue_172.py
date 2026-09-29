"""Issue #172: `brandly storyboard --from-brief` - shotlist generation from a brief.

One text-model call turns a one-line brief (+ optional --style/--aspect/
--duration context) into a schema-valid shotlist JSON written to --shots.
Fail-closed: malformed JSON or schema violations -> clean error with the
response tail, NO file written. Existing storyboard target without
--force -> refused. Flag absent -> existing behavior unchanged.

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
    env["COLUMNS"] = "200"
    return CliRunner(env=env)


def _valid_payload() -> dict:
    return {
        "acts": {
            "scene-01": {
                "scene": 1,
                "shots": [
                    {
                        "id": "Scene-01-Shot-1-1",
                        "prompt": "Wide shot of a ceramic mug on a oak counter, moody kitchen, morning light",
                        "duration": 6,
                    },
                    {
                        "id": "Scene-01-Shot-1-2",
                        "prompt": "Macro of steam rising from the mug, shallow depth of field",
                        "duration": 5,
                    },
                ],
            },
            "scene-02": {
                "scene": 2,
                "shots": [
                    {
                        "id": "Scene-02-Shot-2-1",
                        "prompt": "Hands wrap around the mug, warm rim light",
                        "duration": 7,
                    }
                ],
            },
        }
    }


def _chat(payload: dict | str) -> AsyncMock:
    content = payload if isinstance(payload, str) else json.dumps(payload)
    return AsyncMock(return_value={"choices": [{"message": {"content": content}}]})


def _invoke(runner: CliRunner, tmp_path: Path, *extra: str) -> object:
    shots = str(tmp_path / "shots.json")
    return runner.invoke(
        cli,
        [
            "storyboard",
            "my-project",
            "--shots",
            shots,
            "--from-brief",
            "10s ad for a ceramic mug, moody kitchen, morning light",
            *extra,
        ],
    )


# ---------------------------------------------------------------------------
# Happy path: valid JSON -> file written
# ---------------------------------------------------------------------------


def test_from_brief_writes_schema_valid_file(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chat = _chat(_valid_payload())
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = _invoke(runner, tmp_path)

    assert result.exit_code == 0, result.output
    chat.assert_awaited_once()
    out = tmp_path / "shots.json"
    assert out.is_file()
    from brandly_cli import shot_runner

    data = shot_runner.load_shots_file(out)  # raises on invalid content
    assert isinstance(data, dict)
    assert "acts" in data
    assert "written" in result.output
    # Stops before keyframe generation: no image model call, no progress file.
    assert not (tmp_path / ".brandly" / "my-project" / "docs" / "tmp").exists()


def test_from_brief_flat_shots_key_normalized_to_list(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {"shots": [_valid_payload()["acts"]["scene-01"]["shots"][0]]}
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", _chat(payload))

    result = _invoke(runner, tmp_path)

    assert result.exit_code == 0, result.output
    from brandly_cli import shot_runner

    data = shot_runner.load_shots_file(tmp_path / "shots.json")
    assert isinstance(data, list)
    assert data[0]["id"] == "Scene-01-Shot-1-1"


def test_brief_context_in_messages(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chat = _chat(_valid_payload())
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = runner.invoke(
        cli,
        [
            "storyboard",
            "my-project",
            "--shots",
            str(tmp_path / "shots.json"),
            "--from-brief",
            "10s ad for a ceramic mug",
            "--style",
            "editorial noir",
            "--aspect",
            "9:16",
            "--duration",
            "15",
        ],
    )

    assert result.exit_code == 0, result.output
    user_content = chat.await_args.args[0][1]["content"]
    assert "10s ad for a ceramic mug" in user_content
    assert "editorial noir" in user_content
    assert "9:16" in user_content
    assert "15" in user_content


# ---------------------------------------------------------------------------
# Fail-closed: error + NO file written
# ---------------------------------------------------------------------------


def test_malformed_json_no_file_written(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "brandly_cli.agnes_client.chat_completion",
        _chat("sorry, no json here"),
    )

    result = _invoke(runner, tmp_path)

    assert result.exit_code == 2, result.output
    assert not (tmp_path / "shots.json").exists()
    assert "Traceback" not in result.output
    assert "sorry, no json here" in result.output  # response tail


def test_api_error_no_file_written(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "brandly_cli.agnes_client.chat_completion",
        AsyncMock(side_effect=RuntimeError("boom")),
    )

    result = _invoke(runner, tmp_path)

    assert result.exit_code == 2, result.output
    assert not (tmp_path / "shots.json").exists()
    assert "RuntimeError" in result.output
    assert "Traceback" not in result.output


def test_duplicate_ids_rejected(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _valid_payload()
    shots = payload["acts"]["scene-01"]["shots"]
    shots[1]["id"] = shots[0]["id"]  # duplicate Scene-01-Shot-1-1
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", _chat(payload))

    result = _invoke(runner, tmp_path)

    assert result.exit_code == 2, result.output
    assert not (tmp_path / "shots.json").exists()
    assert "duplicate" in result.output.lower()


def test_invalid_id_format_rejected(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _valid_payload()
    payload["acts"]["scene-01"]["shots"][0]["id"] = "shot-one"
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", _chat(payload))

    result = _invoke(runner, tmp_path)

    assert result.exit_code == 2, result.output
    assert not (tmp_path / "shots.json").exists()
    assert "Scene-XX-Shot-X-Y" in result.output


def test_bad_duration_rejected(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _valid_payload()
    payload["acts"]["scene-01"]["shots"][0]["duration"] = 99
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", _chat(payload))

    result = _invoke(runner, tmp_path)

    assert result.exit_code == 2, result.output
    assert not (tmp_path / "shots.json").exists()
    assert "duration" in result.output


def test_missing_prompt_rejected(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = _valid_payload()
    del payload["acts"]["scene-01"]["shots"][0]["prompt"]
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", _chat(payload))

    result = _invoke(runner, tmp_path)

    assert result.exit_code == 2, result.output
    assert not (tmp_path / "shots.json").exists()
    assert "prompt" in result.output


# ---------------------------------------------------------------------------
# Overwrite protection
# ---------------------------------------------------------------------------


def test_existing_storyboard_refused_without_force(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "shots.json"
    target.write_text('{"sentinel": true}', encoding="utf-8")
    chat = AsyncMock(side_effect=AssertionError("must not be called"))
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", chat)

    result = _invoke(runner, tmp_path)

    assert result.exit_code == 1, result.output
    assert "--force" in result.output
    assert target.read_text(encoding="utf-8") == '{"sentinel": true}'
    chat.assert_not_awaited()


def test_force_overwrites_existing(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "shots.json").write_text('{"sentinel": true}', encoding="utf-8")
    monkeypatch.setattr("brandly_cli.agnes_client.chat_completion", _chat(_valid_payload()))

    result = _invoke(runner, tmp_path, "--force")

    assert result.exit_code == 0, result.output
    from brandly_cli import shot_runner

    data = shot_runner.load_shots_file(tmp_path / "shots.json")
    assert isinstance(data, dict) and "acts" in data


# ---------------------------------------------------------------------------
# Flag absent: existing behavior preserved
# ---------------------------------------------------------------------------


def test_flag_absent_keeps_existing_behavior(
    runner: CliRunner, tmp_path: Path
) -> None:
    missing = tmp_path / "nope.json"
    result = runner.invoke(
        cli, ["storyboard", "my-project", "--shots", str(missing)]
    )

    assert result.exit_code == 1, result.output
    assert f"Shot list not found: {missing}" in result.output
    assert "--from-brief" not in result.output


def test_help_lists_from_brief(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["storyboard", "--help"])

    assert result.exit_code == 0
    assert "--from-brief" in result.output
    assert "--force" in result.output
    assert "--brief-model" in result.output


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
