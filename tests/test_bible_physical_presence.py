"""Bible physical-presence spec — the director's source for downstream skills.

The production bible is the single source of truth the director hands to
every downstream skill (character-sheet, casting, storyboard, video). If a
character's physique (height/weight/build) plus actor, location, and element
notes live ONLY in a sheet skill, the director never sees them and every
downstream prompt renders a generic body. This contract pins the bible's
Section 4 character block as the carrier: every character entry declares
height, weight, build, and actor notes, each location entry declares its
physical characteristics, and each product entry declares its physical
characteristics — so the director can fan them out verbatim.
"""

from __future__ import annotations

from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"
BIBLE = SKILLS_ROOT / "brandly-production-bible"

#: Fields every bible character entry must declare (case-insensitive).
CHARACTER_FIELDS = ("height", "weight", "build", "actor")


def _read(rel: str) -> str:
    return (BIBLE / rel).read_text(encoding="utf-8", errors="ignore")


class TestBibleCharacterPhysicalPresence:
    def test_skill_section_4_declares_physique_fields(self) -> None:
        """SKILL.md Section 4 names height/weight/build/actor per character."""
        text = _read("SKILL.md").lower()
        for field in CHARACTER_FIELDS:
            assert field in text, (
                f"brandly-production-bible/SKILL.md must declare a "
                f"'{field}' field for every character (Section 4)"
            )

    def test_template_has_physique_slots(self) -> None:
        """The fill-in template has slots so authors cannot skip them."""
        text = _read("references/bible-template.md").lower()
        for field in CHARACTER_FIELDS:
            assert field in text, (
                f"bible-template.md must include a '{field}' slot "
                f"in the character block"
            )

    def test_example_shows_a_filled_physique(self) -> None:
        """The worked example fills every physique slot (Lina: 151cm/50kg)."""
        text = _read("references/example-bible.md")
        lowered = text.lower()
        for field in CHARACTER_FIELDS:
            assert field in lowered, (
                f"example-bible.md must show a filled '{field}' line"
            )
        assert "151" in text and "50" in text, (
            "example-bible.md must show the concrete Lina physique "
            "(151cm / 50kg) so authors see the expected format"
        )

    def test_locations_and_products_declare_physical_characteristics(
        self,
    ) -> None:
        """Location + product blocks carry physical characteristics too."""
        skill = _read("SKILL.md").lower()
        assert "physical characteristics" in skill or (
            "characteristics" in skill and "dimensions" in skill
        ), (
            "SKILL.md must ask for physical characteristics "
            "(dimensions/materials/lighting-state) on locations and products"
        )


class TestBibleDirectsDownstreamPropagation:
    def test_skill_tells_director_to_fan_out_physique(self) -> None:
        """SKILL.md states physique flows bible → director → sheet skills."""
        text = _read("SKILL.md").lower()
        assert "downstream" in text and "physique" in text, (
            "SKILL.md must state the character physique flows from the bible "
            "through the director into downstream sheet/video prompts verbatim"
        )
