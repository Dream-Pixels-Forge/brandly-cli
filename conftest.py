"""Pytest configuration for brandly-cli.

Rich's ``Console`` honors the ``FORCE_COLOR`` environment variable, which forces
ANSI escape codes even in non-TTY contexts (pytest / CI output capture). That
leaks color codes into captured CLI output and breaks tests that assert on plain
text. Normalize the environment here so tests run color-free; interactive
production use is unaffected (production consoles are constructed at runtime,
not under pytest).
"""

from __future__ import annotations

import os

os.environ.pop("FORCE_COLOR", None)
os.environ.setdefault("NO_COLOR", "1")
