"""Packaging tests: bundled skills must be importable from an installed wheel.

`utils.find_skills_directory()` must find the skills shipped inside the
brandly-cli package (pip installs carry no repo-level ``skills/`` folder), and
the hatch build config must actually include them in the wheel.
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # Python 3.10
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None

from brandly_cli import utils

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"


def test_wheel_force_includes_skills(tmp_path: Path) -> None:
    """`skills/` must be force-included into the wheel under brandly_cli/."""
    if tomllib is None:
        pytest.skip("tomllib/tomli unavailable on this interpreter")
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    force_include = (
        config.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("force-include", {})
    )
    assert force_include.get("skills") == "brandly_cli/skills"
    assert (REPO_ROOT / "skills").is_dir()


def test_find_skills_directory_checks_the_installed_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pip-installed copy (skills under brandly_cli/) must be discovered."""
    # Simulate an installed package: <site-packages>/brandly_cli/skills/...
    pkg_dir = tmp_path / "site-packages" / "brandly_cli"
    (pkg_dir / "skills" / "brandly-object-sheet").mkdir(parents=True)
    (pkg_dir / "skills" / "brandly-object-sheet" / "SKILL.md").write_text(
        "---\nname: brandly-object-sheet\ndescription: x\n---\n", encoding="utf-8"
    )
    # No project-local ./skills and no user-level dirs exist (home is faked).
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.setattr(utils, "__package_dir__", pkg_dir)

    found = utils.find_skills_directory(root=tmp_path)
    assert found == pkg_dir / "skills"


def test_find_skills_directory_prefers_project_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A project-local skills tree wins over the packaged one."""
    pkg_dir = tmp_path / "site-packages" / "brandly_cli"
    (pkg_dir / "skills" / "packaged").mkdir(parents=True)
    local = tmp_path / "local-project" / "skills"
    (local / "local").mkdir(parents=True)
    monkeypatch.chdir(tmp_path / "local-project")
    monkeypatch.setattr(utils, "__package_dir__", pkg_dir)

    assert utils.find_skills_directory(root=None) == (tmp_path / "local-project" / "skills").resolve()


def test_load_sheet_reference_from_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sheet references load from the packaged skills tree."""
    pkg_dir = tmp_path / "site-packages" / "brandly_cli"
    skill = pkg_dir / "skills" / "brandly-vehicle-sheet"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n", encoding="utf-8")
    (skill / "references" / "vehicle-types.md").write_text(
        "# Vehicle types\n", encoding="utf-8"
    )
    monkeypatch.setattr(utils, "__package_dir__", pkg_dir)

    data = utils.load_sheet_reference("brandly-vehicle-sheet", root=tmp_path)
    assert data is not None
    assert "structure" in data["sheet_data"]
    assert "vehicle-types" in data["references"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(__import__("pytest").main([__file__, "-v"]))
