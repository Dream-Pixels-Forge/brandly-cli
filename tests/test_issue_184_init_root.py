"""Regression tests for issue #184: ``brandly init`` must create the project
in the **current working directory**, never in an ancestor ``.brandly`` store.

RED test: ``cli._get_root`` walked UP from ``cwd`` looking for a ``.brandly``
marker and hijacked the root to the first ancestor that had one — most notably
the user's home directory, where the persistent global store lives. So
``init`` from a subfolder created the project in the *ancestor's* store
instead of ``$(pwd)/.brandly/``, and the working directory ended up with no
project at all.

The walk-up stays for *read/resume* commands (it correctly finds an existing
store) but must not apply when *creating* a new project.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from brandly_cli.cli import _get_root


class _Ctx:
    """Minimal stand-in for a click.Context — only ``obj`` is consulted."""

    def __init__(self, root: str | None = None) -> None:
        self.obj: dict[str, Any] = {"root": root} if root else {}


def _nest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """``<tmp>/home/.brandly`` exists (like the user's home) and cwd is
    ``<tmp>/home/Videos/Platform``."""
    home = tmp_path / "home"
    (home / ".brandly").mkdir(parents=True)
    sub = home / "Videos" / "Platform"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    monkeypatch.delenv("ROOT", raising=False)
    return home, sub


class TestGetRootCreateMode:
    def test_create_prefers_cwd_over_ancestor_store(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home, sub = _nest(tmp_path, monkeypatch)

        root = _get_root(_Ctx(), create=True)  # type: ignore[arg-type]

        assert root == sub.resolve(), (
            f"init must use cwd ({sub.resolve()}), not the ancestor store "
            f"({root}) — issue #184"
        )
        assert root != home.resolve()

    def test_create_still_honours_explicit_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _nest(tmp_path, monkeypatch)
        explicit = tmp_path / "elsewhere"
        explicit.mkdir()

        root = _get_root(_Ctx(root=str(explicit)), create=True)  # type: ignore[arg-type]

        assert root == Path(explicit).resolve()

    def test_create_still_honours_root_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _nest(tmp_path, monkeypatch)
        env_root = tmp_path / "from-env"
        env_root.mkdir()
        monkeypatch.setenv("ROOT", str(env_root))

        root = _get_root(_Ctx(), create=True)  # type: ignore[arg-type]

        assert root == Path(env_root).resolve()


class TestGetRootReadModeUnchanged:
    """The walk-up is correct for *reading* an existing store — keep it."""

    def test_read_mode_still_walks_up_to_existing_store(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home, sub = _nest(tmp_path, monkeypatch)

        root = _get_root(_Ctx())  # type: ignore[arg-type]

        assert root == home.resolve(), (
            "read commands must still walk up to the existing store"
        )

    def test_read_mode_falls_back_to_cwd_when_no_store(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Nest deep enough that the 10-level walk-up cannot reach the real
        # user's home store (tmp_path sits under it on this machine).
        sub = tmp_path
        for i in range(14):
            sub = sub / f"l{i}"
        sub.mkdir(parents=True)
        monkeypatch.chdir(sub)
        monkeypatch.delenv("ROOT", raising=False)

        root = _get_root(_Ctx())  # type: ignore[arg-type]

        assert root == sub.resolve()


class TestWarnIfAncestorStore:
    def test_warns_when_an_ancestor_store_was_skipped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from brandly_cli.cli import _warn_if_ancestor_store

        home, _ = _nest(tmp_path, monkeypatch)
        deeper = home / "Videos" / "Platform" / "nested"
        deeper.mkdir(parents=True)

        warned: list[str] = []
        monkeypatch.setattr(
            "brandly_cli.cli.console.print", lambda msg: warned.append(str(msg))
        )

        assert _warn_if_ancestor_store(deeper) is True
        assert warned, "init must tell the user an ancestor store was skipped"
        assert "brandly" in warned[0].lower()

    def test_silent_when_no_ancestor_store(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from brandly_cli.cli import _warn_if_ancestor_store

        # Same hermeticity guard: nest past the 10-level walk-up limit.
        sub = tmp_path
        for i in range(14):
            sub = sub / f"d{i}"
        sub.mkdir(parents=True)
        warned: list[str] = []
        monkeypatch.setattr(
            "brandly_cli.cli.console.print", lambda msg: warned.append(str(msg))
        )

        assert _warn_if_ancestor_store(sub) is False
        assert not warned, "no warning when there is no ancestor store"


class TestInitEndToEnd:
    """The full CLI path: init from a subfolder under a home store."""

    def test_init_creates_project_in_cwd_not_ancestor_store(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home, sub = _nest(tmp_path, monkeypatch)

        from brandly_cli.cli import cli

        result = CliRunner().invoke(
            cli,
            ["init", "-n", "Platform", "-i", "test idea", "-s", "cinematic", "--shots", "3"],
        )
        assert result.exit_code == 0, result.output

        local_store = sub / ".brandly"
        assert local_store.is_dir(), (
            f"init must create {local_store} — issue #184 (got {result.output})"
        )
        for child in (home / ".brandly").iterdir():
            assert "Platform" not in child.name, (
                f"init leaked the project into the ancestor store: {child}"
            )

    def test_init_surfaces_the_ancestor_store_hint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _nest(tmp_path, monkeypatch)

        from brandly_cli.cli import cli

        result = CliRunner().invoke(
            cli,
            ["init", "-n", "Platform", "-i", "test idea", "-s", "cinematic", "--shots", "3"],
        )
        assert result.exit_code == 0, result.output
        assert "--root" in result.output, (
            "init must hint at --root when an ancestor store was skipped"
        )

