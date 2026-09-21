r"""Packaging tests for the bundled Agent Skills (``skills/``).

Every skill shipped inside brandly-cli must conform to the agentskills.io
spec (folder name == frontmatter ``name``, ``description`` present) and must
only reference documentation files that actually exist, so agents following
a skill never hit a dead link.
"""

from __future__ import annotations

import re
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

# Relative markdown references inside a SKILL.md body, e.g.
#   references/video-styles.md   ../brandly-camera/SKILL.md
_REF_RE = re.compile(r"(?:references/|\.\./)[A-Za-z0-9_\-./]+\.md")


def _skills() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())


def _frontmatter(skill: Path) -> str:
    lines = (skill / "SKILL.md").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    end = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if end is None:
        return ""
    return "\n".join(lines[1:end])


def test_every_skill_folder_has_a_skill_md() -> None:
    for skill in _skills():
        assert (skill / "SKILL.md").is_file(), f"missing SKILL.md: {skill.name}"


def test_frontmatter_name_matches_folder() -> None:
    for skill in _skills():
        fm = _frontmatter(skill)
        match = re.search(r"^name:\s*\"?([a-z0-9-]+)\"?\s*$", fm, re.MULTILINE)
        assert match, f"{skill.name}: frontmatter has no lowercase name field"
        assert match.group(1) == skill.name, (
            f"{skill.name}: frontmatter name is {match.group(1)!r}"
        )


def test_frontmatter_has_description() -> None:
    for skill in _skills():
        assert re.search(r"^description:", _frontmatter(skill), re.MULTILINE), (
            f"{skill.name}: frontmatter has no description (activation trigger)"
        )


def test_every_referenced_doc_exists() -> None:
    broken: list[str] = []
    for skill in _skills():
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        for ref in _REF_RE.findall(text):
            target = (skill / ref).resolve()
            if not target.is_file():
                broken.append(f"{skill.name}/SKILL.md -> {ref}")
    assert not broken, "dead documentation links:\n  " + "\n  ".join(broken)


def test_every_skill_mentions_the_cli() -> None:
    """Skills ship inside brandly-cli — each must drive some CLI surface."""
    for skill in _skills():
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        assert re.search(r"brandly\b", text, re.IGNORECASE), (
            f"{skill.name}: never mentions the brandly CLI it ships with"
        )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(__import__("pytest").main([__file__, "-v"]))
