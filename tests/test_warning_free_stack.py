"""Guard project and GitHub Actions against reintroduced deprecations."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
