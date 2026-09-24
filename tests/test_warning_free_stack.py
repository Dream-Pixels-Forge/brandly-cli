"""Guard project and GitHub Actions against reintroduced deprecations."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_version_sources_match() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    about = (ROOT / "src" / "brandly_cli" / "__about__.py").read_text(encoding="utf-8")
    project_version = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    runtime_version = re.search(r'^__version__ = "([^"]+)"$', about, re.MULTILINE)
    assert project_version is not None
    assert runtime_version is not None
    assert project_version.group(1) == runtime_version.group(1)


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
