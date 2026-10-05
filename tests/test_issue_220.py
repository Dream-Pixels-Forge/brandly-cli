r"""Issue #220: ``brandly memory`` fails silently (exit code 0) on misuse,
shows an empty store on first run, and exposes a ``budget`` preference that
can never be set or read.

Run under ``.venv\\Scripts\\python`` (editable install points at ``src/``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli import memory
from brandly_cli.cli import cli


@pytest.fixture
def runner(tmp_path: Path) -> CliRunner:
    import os

    env = os.environ.copy()
    env["ROOT"] = str(tmp_path)
    return CliRunner(env=env)


class TestMemoryCliExitCode:
    def test_misuse_exits_nonzero(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        # `brandly memory like` without a hook reached the usage branch and
        # exited 0 — a silent no-op that corrupts trust in scripted/agent/CI
        # callers doing `brandly memory like "$HOOK" && echo ok`.
        result = runner.invoke(cli, ["memory", "like"])
        assert result.exit_code != 0, (
            "misuse must exit non-zero, not print usage and exit 0"
        )
        assert "Usage" in result.output

    def test_like_with_hook_still_exits_zero(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        # Guard: the valid path is unchanged.
        result = runner.invoke(cli, ["memory", "like", "some-hook"])
        assert result.exit_code == 0, result.output
        assert "Liked hook" in result.output


class TestFreshStoreSelfDescribing:
    def test_fresh_view_shows_the_full_schema(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        # A virgin store used to render a bare heading with zero fields — no
        # schema, no indication of what is even settable.
        result = runner.invoke(cli, ["memory", "view"])
        assert result.exit_code == 0, result.output
        assert (
            "preferred_style" in result.output
        ), "the defaults must be visible on a fresh store"
        assert "liked_hooks" in result.output
        assert "target_platforms" in result.output

    def test_stored_values_win_over_defaults(self, tmp_path: Path) -> None:
        # Guard: a stored preference survives the defaults merge.
        store = tmp_path / ".brandly" / "user-preferences.json"
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps({"preferred_style": "cinematic"}))
        prefs = memory.UserPreferences(tmp_path).get()
        assert prefs.get("preferred_style") == "cinematic"
        assert "liked_hooks" in prefs  # the defaults are still present


class TestDeadBudgetKey:
    def test_reset_seeds_the_same_defaults(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        result = runner.invoke(cli, ["memory", "reset"])
        assert result.exit_code == 0, result.output
        store = tmp_path / ".brandly" / "user-preferences.json"
        data = json.loads(store.read_text())
        assert "preferred_style" in data
        assert (
            "budget" not in data
        ), "the write-never, read-never budget key must be gone"

    def test_budget_key_is_dropped_even_if_stored(self, tmp_path: Path) -> None:
        # An old stored file may still carry the dead key — view must stop
        # advertising something unusable.
        store = tmp_path / ".brandly" / "user-preferences.json"
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps({"budget": 500, "preferred_style": "noir"}))
        prefs = memory.UserPreferences(tmp_path).get()
        assert "budget" not in prefs, "view must stop advertising the dead key"
        assert prefs.get("preferred_style") == "noir"
