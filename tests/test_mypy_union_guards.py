"""RED-first contract tests for the PR #264 mypy fixes.

Covers:
1. Team commands fail-honest (clean SystemExit + message) when the team file
   exists but is corrupt — previously crashed with AttributeError (mypy
   union-attr errors in cmd/team.py).
2. ``scenes.REQUIRED_BEATS`` exists as the canonical narrative-beat set
   (previously a dangling reference at cmd/production.py:3359).
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from brandly_cli.cli import cli

_CORRUPT_TEAM_ID = "t-corrupt"


def _make_corrupt_team(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Create a team file that exists but cannot be parsed (load_team -> None)."""
    teams_dir = tmp_path / ".brandly" / "teams"
    teams_dir.mkdir(parents=True)
    (teams_dir / f"{_CORRUPT_TEAM_ID}.json").write_text(
        "{ not valid json", encoding="utf-8"
    )


@pytest.mark.parametrize(
    "args",
    [
        ["members", _CORRUPT_TEAM_ID],
        ["invite", _CORRUPT_TEAM_ID, "member@example.com"],
        ["role", _CORRUPT_TEAM_ID, "user_x", "admin"],
        ["projects", _CORRUPT_TEAM_ID],
        ["add-project", _CORRUPT_TEAM_ID, "p-1234"],
        ["remove-project", _CORRUPT_TEAM_ID, "p-1234"],
        ["delete", _CORRUPT_TEAM_ID],
    ],
)
def test_team_commands_fail_honest_on_corrupt_team_file(
    args: list[str], tmp_path  # type: ignore[no-untyped-def]
) -> None:
    """Corrupt team file -> clean exit(1) with message, never AttributeError."""
    _make_corrupt_team(tmp_path)
    result = CliRunner().invoke(
        cli, ["team", *args, "--root", str(tmp_path)]
    )
    assert result.exit_code == 1
    # RED before the guards: load_team -> None leaked into team_attr access
    # and crashed with AttributeError.
    assert not isinstance(result.exception, AttributeError), (
        f"command {args} crashed on corrupt team file: {result.exception!r}"
    )
    assert "corrupt" in result.output.lower()


def test_scenes_required_beats_constant() -> None:
    """scenes.REQUIRED_BEATS is the canonical narrative-beat set.

    RED before the fix: cmd/production.py:3359 referenced
    ``scenes.REQUIRED_BEATS`` which did not exist (mypy attr-defined).
    """
    from brandly_cli import scenes

    required = getattr(scenes, "REQUIRED_BEATS", None)
    assert required is not None, "scenes.REQUIRED_BEATS is missing"
    assert set(required) == {"setup", "turn", "consequence", "resolve"}
