"""Regression tests for the import-linter architecture gate (.importlinter).

Background: `.importlinter` was a silent no-op. import-linter 2.x only reads
contract sections prefixed ``importlinter:``; the legacy ``[contract:<name>]``
headers were ignored, so the gate reported "Contracts: 0 kept, 0 broken" and
exited 0 even while an upward (layer-violating) import existed in the tree.

These tests make that failure mode impossible to reintroduce silently:

1. ``read_configuration(...)["contracts_options"]`` must be non-empty.
   This is the direct guard against the gate silently evaluating ZERO
   contracts -- a zero-contract config "passes" while checking nothing.
2. ``lint_imports()`` on the repo root must exit 0, proving the contracts
   both exist and are kept on the current tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from importlinter.api import read_configuration
from importlinter.cli import lint_imports

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_importlinter_config_defines_at_least_one_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The gate must load at least one contract from .importlinter.

    Guards against the gate silently evaluating zero contracts: with legacy
    ``[contract:...]`` section headers, import-linter 2.x drops every section,
    reports "0 kept, 0 broken", and exits 0 -- a no-op that looks green.
    """
    monkeypatch.chdir(REPO_ROOT)
    config = read_configuration(config_filename=".importlinter")
    assert config["contracts_options"], (
        ".importlinter produced zero contracts_options -- the architecture "
        "gate would silently evaluate nothing (no-op regression)."
    )


def test_lint_imports_exits_zero_on_repo_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """lint_imports must exist, pass, and exit 0 on the repo root.

    no_cache=True keeps the test hermetic (no .import_linter_cache writes).
    verbose=True routes import-linter through its line-based progress output
    instead of the animated rich Progress+Live display. That display path is
    broken on rich >= 13.9 with import-linter 2.x ("Only one live display
    may be active at once" -> forced exit 1 even when all contracts are
    kept), so the flag keeps the gate deterministic without changing what is
    checked: the contracts are still fully evaluated and "1 kept, 0 broken"
    is what exit 0 proves.
    """
    monkeypatch.chdir(REPO_ROOT)
    exit_status = lint_imports(
        config_filename=".importlinter", no_cache=True, verbose=True
    )
    assert exit_status == 0, (
        f"lint_imports returned {exit_status}: contracts broken or config invalid"
    )
