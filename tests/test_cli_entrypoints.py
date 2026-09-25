"""Regression tests: the CLI entry points and the import order must always work.

Three long-standing defects are pinned here:

* ``python -m brandly_cli.cli`` ran ``main()`` before the ``cmd.*`` command
  groups were registered, so every command was missing ("No such command
  'list'"). ``make e2e`` uses exactly this entry point.
* Importing any ``brandly_cli.cmd.<module>`` *first* raised
  ``ImportError: cannot import name 'register' ... (most likely due to a
  circular import)`` — ``cli.py`` imported the ``cmd`` package at import time,
  while every ``cmd`` module imports its shared helpers from ``cli``. The graph
  therefore only worked from one side, which is a footgun for library users and
  for any agent that imports a command module directly.
* ``agent_surface``'s default subprocess runner decoded the CLI's stdout with
  the platform locale codec, so UTF-8 CLI output (→, ✓, —) raised
  ``UnicodeDecodeError`` on Windows and the tool result came back as ``None``.

Every check runs in a real subprocess: these are entry-point contracts, and the
in-process view is exactly what masked the bugs (pytest happens to import
``brandly_cli.cli`` before any ``cmd`` module).
"""

from __future__ import annotations

import subprocess
import sys

from brandly_cli import agent_surface

COMMANDS = ("init", "run", "plan", "director", "gate", "tools")


def _run_python(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a fresh interpreter, decoding its streams as UTF-8 (never locale)."""
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def _entrypoint_help(module: str) -> str:
    proc = _run_python("-m", module, "--help")

    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_cmd_submodule_can_be_imported_first() -> None:
    """``import brandly_cli.cmd.<module>`` first must not hit the cli⇄cmd cycle."""
    proc = _run_python(
        "-c",
        "from brandly_cli.cmd import production; "
        "print('Director' if production.Director else 'missing')",
    )

    assert proc.returncode == 0, proc.stderr
    assert "Director" in proc.stdout


def test_cmd_first_import_order_can_still_drive_the_root_cli() -> None:
    """Importing a cmd module first must not disable the root ``cli`` group."""
    proc = _run_python(
        "-c",
        "from brandly_cli.cmd import gate; "
        "from click.testing import CliRunner; "
        "from brandly_cli.cli import cli; "
        "result = CliRunner().invoke(cli, ['--help']); "
        "print('exit', result.exit_code); print(result.output)",
    )

    assert proc.returncode == 0, proc.stderr
    assert "exit 0" in proc.stdout
    for command in COMMANDS:
        assert command in proc.stdout, proc.stdout


def test_module_entrypoint_registers_every_command() -> None:
    """``python -m brandly_cli.cli`` is a supported entry point (Makefile e2e)."""
    help_text = _entrypoint_help("brandly_cli.cli")

    for command in COMMANDS:
        assert command in help_text, help_text


def test_package_entrypoint_still_registers_every_command() -> None:
    """``python -m brandly_cli`` keeps working (agent_surface's runner uses it)."""
    help_text = _entrypoint_help("brandly_cli")

    for command in COMMANDS:
        assert command in help_text, help_text


def test_default_subprocess_runner_decodes_utf8_stdout() -> None:
    """Agent tool dispatch must survive non-ASCII CLI output on any locale."""
    script = "import sys; sys.stdout.reconfigure(encoding='utf-8'); print('\\u2192 ok')"

    code, out, err = agent_surface._subprocess_runner([sys.executable, "-c", script])

    assert code == 0, err
    assert out is not None and "\u2192 ok" in out
