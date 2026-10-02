"""Guard project and GitHub Actions against reintroduced deprecations."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_version_is_single_sourced() -> None:
    """The package version has exactly ONE source of truth.

    ``src/brandly_cli/__about__.py`` is that source. ``pyproject.toml`` must
    derive the build version from it via PEP 621 dynamic versioning
    (``dynamic = ["version"]`` + hatch reading ``__about__.py``), so a bump in
    ``__about__.py`` flows to the wheel metadata, ``brandly --version``, the
    MCP server, and the web config API with no second literal to keep in sync.
    """
    about = (ROOT / "src" / "brandly_cli" / "__about__.py").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    # The single source exists and is a PEP 440 X.Y.Z.
    version = re.search(r'^__version__\s*=\s*"([^"]+)"$', about, re.MULTILINE)
    assert version is not None, "__about__.py must define __version__ (the single source)"
    assert re.fullmatch(r"\d+\.\d+\.\d+", version.group(1)), (
        f"__about__.__version__ must be a PEP 440 X.Y.Z, got {version.group(1)!r}"
    )

    # pyproject declares the version dynamic (hatch reads __about__.py) …
    assert re.search(
        r'(?m)^\s*dynamic\s*=\s*\[\s*"version"\s*\]', pyproject
    ), "pyproject.toml must list `version` in `dynamic = [...]`"
    assert "[tool.hatch.version]" in pyproject, "pyproject.toml must define [tool.hatch.version]"
    assert re.search(
        r'(?m)^\s*path\s*=\s*"src/brandly_cli/__about__.py"\s*$', pyproject
    ), "[tool.hatch.version] must read the version from __about__.py"
    # … and no longer hardcodes a second literal.
    assert not re.search(
        r'(?m)^version\s*=\s*"', pyproject
    ), "pyproject.toml must not hardcode `version = \"...\"` (it is the dynamic source)"


def test_version_gate_is_wired_into_builds() -> None:
    """Makefile, CI, and release all delegate to the shared gate script."""
    assert (ROOT / "scripts" / "version_check.py").is_file()
    make = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "scripts/version_check.py" in make
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "python scripts/version_check.py" in ci
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "scripts/version_check.py --tag" in release


def test_version_check_script_gates_single_source() -> None:
    """The shared gate passes on the real tree and fails on a tag mismatch.

    Reads the current version from the single source so this test never needs
    a manual literal bump (the whole point of the dynamic-versioning change).
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("version_check", ROOT / "scripts" / "version_check.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    about = (ROOT / "src" / "brandly_cli" / "__about__.py").read_text(encoding="utf-8")
    current = re.search(r'^__version__\s*=\s*"([^"]+)"$', about, re.M).group(1)

    assert mod.main([]) == 0, "version_check should pass on the current tree"
    assert mod.main(["--tag", current]) == 0
    other = "0.0.1" if current != "0.0.1" else "0.0.2"
    assert mod.main(["--tag", other]) == 1, "a mismatched tag must fail the gate"


def test_starlette_major_is_bounded() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'starlette>=1.7,<2.0' in pyproject


def test_official_actions_use_node24_majors() -> None:
    deprecated = {
        "actions/checkout@v4",
        "actions/setup-node@v4",
        "actions/setup-python@v5",
        "actions/upload-artifact@v4",
    }
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        workflow = path.read_text(encoding="utf-8")
        assert deprecated.isdisjoint(set(workflow.splitlines()))
