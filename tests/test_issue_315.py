"""Issue #315: `brandly report` must signal headless non-submission.

In a non-interactive shell the consent prompt hits EOF, the run ends with
nothing submitted, and the exit code is 0 — six consecutive runs LOOKED
successful to a calling agent. Also `_resolve_token`'s gh fallback only read
``~/.config/gh/hosts.yml`` — on Windows gh stores hosts under
``%AppData%\\GitHub CLI`` and honors ``GH_CONFIG_DIR``, so an authenticated
gh was missed.

Ruling:
1. non-tty EOF at consent → explicit "NOT SUBMITTED" warning + exit 2
   (user-declined stays exit 0; ``--auto`` submit failure → exit 1);
2. ``_resolve_token`` order: GITHUB_TOKEN → GH_TOKEN → $GH_CONFIG_DIR/hosts.yml
   → %APPDATA%/GitHub CLI/hosts.yml (win32) → $XDG_CONFIG_HOME/gh/hosts.yml
   → ~/.config/gh/hosts.yml.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli import issue_tracker
from brandly_cli.cli import cli


def _hosts(path: Path, token: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "github.com:\n  oauth_token: " + token + "\n", encoding="utf-8"
    )
    return path


class TestResolveTokenDiscovery:
    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in ("GITHUB_TOKEN", "GH_TOKEN", "GH_CONFIG_DIR", "XDG_CONFIG_HOME"):
            monkeypatch.delenv(key, raising=False)

    def test_env_token_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "env-token")
        assert issue_tracker._resolve_token() == "env-token"

    def test_gh_config_dir_honored(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """GH_CONFIG_DIR is gh's documented config override (#315)."""
        _hosts(tmp_path / "hosts.yml", "ghdir-token")
        monkeypatch.setenv("GH_CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(issue_tracker.Path, "home", staticmethod(lambda: tmp_path / "nonexistent-home"))
        assert issue_tracker._resolve_token() == "ghdir-token"

    def test_windows_appdata_location(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Windows gh stores hosts under %AppData%/GitHub CLI (#315)."""
        appdata = tmp_path / "AppData" / "Roaming"
        _hosts(appdata / "GitHub CLI" / "hosts.yml", "win-token")
        monkeypatch.setenv("APPDATA", str(appdata))
        monkeypatch.setattr(issue_tracker.sys, "platform", "win32")
        monkeypatch.setattr(issue_tracker.Path, "home", staticmethod(lambda: tmp_path / "nonexistent-home"))
        assert issue_tracker._resolve_token() == "win-token"

    def test_xdg_config_home_honored(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _hosts(tmp_path / "gh" / "hosts.yml", "xdg-token")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        monkeypatch.setattr(issue_tracker.Path, "home", staticmethod(lambda: tmp_path / "nonexistent-home"))
        assert issue_tracker._resolve_token() == "xdg-token"

    def test_default_dot_config_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _hosts(tmp_path / ".config" / "gh" / "hosts.yml", "home-token")
        monkeypatch.setattr(issue_tracker.Path, "home", staticmethod(lambda: tmp_path))
        assert issue_tracker._resolve_token() == "home-token"

    def test_no_token_returns_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(issue_tracker.Path, "home", staticmethod(lambda: tmp_path / "empty"))
        assert issue_tracker._resolve_token() is None


class TestReportHeadlessExitCodes:
    @pytest.fixture(autouse=True)
    def _isolate_consent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            issue_tracker, "_consent_path", lambda: tmp_path / "consent.json"
        )

    def _invoke(self, *args: str, **kwargs):  # type: ignore[no-untyped-def]
        return CliRunner().invoke(cli, ["report", *args], **kwargs)

    def test_non_tty_eof_exits_2_with_not_submitted(self) -> None:
        """EOF at the consent prompt must be a loud, detectable no-op (#315)."""
        result = self._invoke("-e", "test error", input="")
        assert result.exit_code == 2, (
            f"non-tty EOF must exit 2, got {result.exit_code}: {result.output}"
        )
        assert "NOT SUBMITTED" in result.output

    def test_user_decline_stays_exit_0(self) -> None:
        result = self._invoke("-e", "test error", input="n\n")
        assert result.exit_code == 0, result.output
        assert "skipped" in result.output.lower()

    def test_auto_submit_failure_exits_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            issue_tracker,
            "submit_issue",
            lambda ctx, body: {"ok": False, "error": "boom"},
        )
        result = self._invoke("-e", "test error", "--auto")
        assert result.exit_code == 1, (
            f"a failed --auto submission must exit 1, got {result.exit_code}"
        )

    def test_auto_submit_success_exits_0(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            issue_tracker,
            "submit_issue",
            lambda ctx, body: {"ok": True, "url": "https://x", "number": 1},
        )
        result = self._invoke("-e", "test error", "--auto")
        assert result.exit_code == 0, result.output

    def test_piped_yes_still_submits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Piped stdin with an explicit yes is consent, not an abort (#315)."""
        submitted: list[bool] = []

        def _submit(ctx, body):  # type: ignore[no-untyped-def]
            submitted.append(True)
            return {"ok": True, "url": "https://x", "number": 2}

        monkeypatch.setattr(issue_tracker, "submit_issue", _submit)
        result = self._invoke("-e", "test error", input="y\n")
        assert result.exit_code == 0, result.output
        assert submitted, "piped y must submit the report"


class TestAskPermissionEof:
    def test_eof_returns_none_rather_than_raising(self) -> None:
        import io

        cons_backup = issue_tracker._load_consent()
        try:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(
                    issue_tracker,
                    "_load_consent",
                    lambda: {},
                )
                # Rich Console.input on an exhausted stream raises EOFError.
                mp.setattr(sys, "stdin", io.StringIO(""))
                assert issue_tracker.ask_permission({}, "body") is None
        finally:
            issue_tracker._save_consent(cons_backup) if cons_backup else None
