"""Issue #154: Rich ✗/⚠ glyphs must not crash on legacy Windows streams.

Repro (issue): a cp1252-encoded stdout makes Rich raise
``UnicodeEncodeError: 'charmap' codec can't encode character '\\u2717'``
mid-command. The fix reconfigures stdout/stderr to UTF-8 once, at
package import (covers CLI, ``python -m brandly_cli``, and direct
library use such as live probes).
"""

from __future__ import annotations

import io
import sys

from rich.console import Console

from brandly_cli import ensure_utf8_output


class _RecordingStream:
    """Stand-in exposing only reconfigure()."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def reconfigure(self, **kwargs: object) -> None:
        self.calls.append(dict(kwargs))


def test_reconfigures_stdout_and_stderr_to_utf8(monkeypatch) -> None:
    out, err = _RecordingStream(), _RecordingStream()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)

    ensure_utf8_output()

    assert out.calls == [{"encoding": "utf-8", "errors": "replace"}]
    assert err.calls == [{"encoding": "utf-8", "errors": "replace"}]


def test_glyph_print_on_cp1252_stream_does_not_crash(monkeypatch) -> None:
    buf = io.BytesIO()
    stream = io.TextIOWrapper(buf, encoding="cp1252", newline="")
    monkeypatch.setattr(sys, "stdout", stream)

    ensure_utf8_output()

    assert stream.encoding == "utf-8"
    # Rich resolves Console().file from sys.stdout lazily at print time.
    Console().print("[red]✗ boom[/red]")
    assert "✗".encode() in buf.getvalue()


def test_stream_without_reconfigure_is_tolerated(monkeypatch) -> None:
    monkeypatch.setattr(sys, "stdout", io.StringIO())  # no reconfigure()
    monkeypatch.setattr(sys, "stderr", io.StringIO())

    ensure_utf8_output()  # must not raise
