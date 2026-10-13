"""Issue #314: docs/skills must document the ACTUAL v2 media layout.

v0.14.0 writes generated media to the v2 media tree
(``pre-production/<project_id>/<category>/`` — issue #117), but 10 skill
files still told agents the images live under
``.brandly/<project_id>/images/<category>/`` — real time was lost locating
character sheets / storyboard keyframes / prop plates during a live run.

Ruling: every shipped skill + skills/README.md documents the v2 layout; this
contract test greps the skills tree and fails on any legacy claim.
"""

from __future__ import annotations

import re
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"

#: The legacy claim: `.brandly/<id>/images/` as the media home.
LEGACY_RE = re.compile(r"\.brandly/<[^>]+>/images/")


def _skill_files() -> list[Path]:
    return sorted(SKILLS_ROOT.rglob("*.md"))


class TestNoLegacyMediaLayoutClaims:
    def test_no_skill_documents_the_legacy_images_tree(self) -> None:
        offenders: list[str] = []
        for path in _skill_files():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if LEGACY_RE.search(text):
                offenders.append(str(path.relative_to(SKILLS_ROOT)))
        assert not offenders, (
            "skills must document the v2 media tree "
            "(pre-production/<id>/<category>/), not .brandly/<id>/images/ "
            f"(#314): {offenders}"
        )

    def test_sheet_skills_mention_pre_production(self) -> None:
        """Each sheet skill points at the tree the CLI actually writes."""
        for name in (
            "brandly-character-sheet", "brandly-object-sheet",
            "brandly-location-sheet", "brandly-vehicle-sheet",
            "brandly-animal-sheet", "brandly-plant-sheet",
            "brandly-mecha-sheet",
        ):
            text = (SKILLS_ROOT / name / "SKILL.md").read_text(
                encoding="utf-8", errors="ignore"
            )
            assert "pre-production/" in text, (
                f"{name}/SKILL.md must document the v2 media tree (#314)"
            )
