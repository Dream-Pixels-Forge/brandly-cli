"""Version single-source gate (shared by the Makefile, CI, and release).

The package version lives in exactly ONE place: ``src/brandly_cli/__about__.py``.
Hatch derives the build metadata from it via PEP 621 dynamic versioning
(``pyproject.toml`` sets ``dynamic = ["version"]`` and
``[tool.hatch.version]`` points at ``__about__.py``), so bumping
``__about__.py`` flows to the wheel/sdist, ``brandly --version``, the MCP
server, and the web config API with no second literal to keep in sync.

This script is a fast, platform-safe check that the invariant still holds:

1. the single source defines a PEP 440 ``X.Y.Z`` version, and
2. ``pyproject.toml`` no longer hardcodes a second ``version = "..."``.

Pass ``--tag vX.Y.Z`` (release gate) to additionally require the tag to match
the single source. The same invariant is asserted in
``tests/test_warning_free_stack.py::test_version_is_single_sourced``.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ABOUT = ROOT / "src" / "brandly_cli" / "__about__.py"
PYPROJECT = ROOT / "pyproject.toml"

# Matches the `__version__ = "X.Y.Z"` line in __about__.py (not the docstring).
SOURCE_RE = re.compile(r'(?m)^__version__\s*=\s*"([^"]+)"\s*$')
# A hardcoded `[project] version = "..."` in pyproject.toml is the anti-pattern.
LITERAL_RE = re.compile(r'(?m)^version\s*=\s*"')


def fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--tag",
        default=None,
        metavar="VX.Y.Z",
        help="optional git tag to match against the single source (release gate)",
    )
    args = parser.parse_args(argv)

    about = ABOUT.read_text(encoding="utf-8")
    pyproject = PYPROJECT.read_text(encoding="utf-8")

    source = SOURCE_RE.search(about)
    if not source:
        return fail("version single source __about__.py is missing __version__")
    version = source.group(1)
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        return fail(f"__about__.__version__ must be a PEP 440 X.Y.Z, got {version!r}")

    if LITERAL_RE.search(pyproject):
        return fail(
            "pyproject.toml must not hardcode `version = ...` "
            "(declare dynamic = [\"version\"] and point [tool.hatch.version] at __about__.py)"
        )
    if 'dynamic = ["version"]' not in pyproject or "[tool.hatch.version]" not in pyproject:
        return fail(
            "pyproject.toml must declare dynamic = [\"version\"] and [tool.hatch.version] "
            "pointing at __about__.py"
        )

    if args.tag:
        tag_ver = args.tag.lstrip("v")
        if tag_ver != version:
            return fail(f"tag={tag_ver} does not match single source __about__={version} (bump __about__.py and re-tag)")
        print(f"tag OK: {args.tag} matches single source {version}")

    print(f"version-check OK: {version} (single source: __about__.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
