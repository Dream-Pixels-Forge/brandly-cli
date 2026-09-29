"""Brandly CLI - AI product video orchestrator for any AI tool."""

import sys

from brandly_cli.__about__ import __version__

__all__ = ["__version__", "ensure_utf8_output"]


def ensure_utf8_output() -> None:
    """Reconfigure stdout/stderr to UTF-8 (issue #154).

    Rich's ✗/⚠ glyphs cannot be encoded by legacy Windows charmaps
    (cp1252), so a ``UnicodeEncodeError`` would abort a command
    mid-run. Runs at package import so the CLI, ``python -m
    brandly_cli``, and direct library use (live probes) are all
    covered — not just the ``cli()`` callback.

    Safe no-op when a stream has no ``reconfigure()`` (e.g. StringIO)
    or rejects reconfiguration; UTF-8 output with ``errors="replace"``
    can never raise on write.
    """
    for _stream in (sys.stdout, sys.stderr):
        if _stream is not None and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


ensure_utf8_output()
