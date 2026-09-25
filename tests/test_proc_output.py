"""Subprocess output capture must never depend on the platform locale codec.

Two failure modes are pinned here (both pre-existing; the second was found via
the agent-surface runner bug where a tool result silently came back ``None``):

* ``subprocess.run(..., text=True)`` without an encoding decodes with the
  platform locale codec (cp1252 on Windows) — non-ASCII output (→, ✓, accented
  paths) raised ``UnicodeDecodeError`` in the reader thread and the captured
  stream was lost.
* strict ``bytes.decode()`` on ffmpeg/ffprobe/Blender diagnostics raised inside
  *error* paths, replacing the real tool error with a Python traceback.
"""

from __future__ import annotations

import sys

from brandly_cli.io import proc_output, run_capture

PY = sys.executable


class TestProcOutput:
    """``proc_output`` coerces captured bytes to text without ever raising."""

    def test_decodes_utf8_bytes(self) -> None:
        assert proc_output("héllo → ✓".encode()) == "héllo → ✓"

    def test_replaces_undecodable_bytes(self) -> None:
        out = proc_output(b"\xff\xfe broken")  # must not raise

        assert isinstance(out, str)
        assert "\ufffd" in out

    def test_passes_through_text(self) -> None:
        assert proc_output("already text") == "already text"

    def test_none_is_empty(self) -> None:
        assert proc_output(None) == ""


class TestRunCapture:
    """``run_capture`` captures stdout/stderr as UTF-8 text, never locale text."""

    def test_captures_utf8_output_as_text(self) -> None:
        script = (
            "import sys; sys.stdout.reconfigure(encoding='utf-8'); print('\\u2192 ok')"
        )

        proc = run_capture([PY, "-c", script], timeout=60)

        assert proc.returncode == 0, proc.stderr
        assert isinstance(proc.stdout, str)
        assert "→ ok" in proc.stdout

    def test_stderr_is_text_too(self) -> None:
        script = (
            "import sys; sys.stderr.reconfigure(encoding='utf-8'); "
            "sys.stderr.write('✓ done')"
        )

        proc = run_capture([PY, "-c", script], timeout=60)

        assert isinstance(proc.stderr, str)
        assert "✓ done" in proc.stderr
