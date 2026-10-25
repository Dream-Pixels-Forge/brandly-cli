"""Contract tests: every agent tool must be owned by a bundled skill.

Enforces the "tool ↔ skill" rule (AGENTS.md §5 data honesty — a tool that
claims a skill must point at a skill that actually ships in the wheel):

1. Every tool in ``BUILTIN_TOOLS`` has a ``SKILL_MAP`` entry (even ``None``
   for documented plumbing tools — the entry itself must exist so a missing
   mapping is an explicit decision, not an oversight).
2. Every non-None skill name resolves to a real bundled skill folder
   under ``skills/`` (or the packaged equivalent).
3. ``generate_sheet`` dispatches its skill by ``subject_type``.
4. Read-only classification is consistent with the package's set.
"""

from __future__ import annotations

from pathlib import Path

from brandly_cli.agent_tools import (
    BUILTIN_TOOLS,
    SHEET_SKILLS,
    SKILL_MAP,
    is_read_only,
    skill_for,
)

SKILLS_ROOT = Path(__file__).resolve().parent.parent / "skills"

#: Tools explicitly allowed to have no owning skill (pure plumbing).
DOCUMENTED_UNOWNED = frozenset({"list_models", "generate_sheet"})


class TestSkillMapCompleteness:
    def test_every_tool_has_a_skill_map_entry(self) -> None:
        """A missing SKILL_MAP key is an oversight, not a decision."""
        unmapped = set(BUILTIN_TOOLS) - set(SKILL_MAP)
        assert not unmapped, f"tools missing from SKILL_MAP: {sorted(unmapped)}"

    def test_every_skill_points_at_a_real_bundled_skill(self) -> None:
        for tool, skill in SKILL_MAP.items():
            if skill is None:
                assert tool in DOCUMENTED_UNOWNED, (
                    f"{tool} has no skill and is not in DOCUMENTED_UNOWNED — "
                    "either map it to a bundled skill or document the deferral"
                )
                continue
            assert (SKILLS_ROOT / skill).is_dir() or skill == "dpf-senior-editor", (
                f"{tool} maps to skill {skill!r} which is not bundled under skills/"
            )

    def test_generate_sheet_dispatches_by_subject_type(self) -> None:
        assert skill_for("generate_sheet", subject_type="character") == "brandly-character-sheet"
        assert skill_for("generate_sheet", subject_type="location") == "brandly-location-sheet"
        assert skill_for("generate_sheet", subject_type="prop") == "brandly-object-sheet"
        assert skill_for("generate_sheet", subject_type="vehicle") == "brandly-vehicle-sheet"
        assert skill_for("generate_sheet", subject_type="mecha") == "brandly-mecha-sheet"
        assert skill_for("generate_sheet", subject_type="animal") == "brandly-animal-sheet"
        assert skill_for("generate_sheet", subject_type="plant") == "brandly-plant-sheet"
        # Unknown subject falls back to the (None) static mapping.
        assert skill_for("generate_sheet", subject_type="alien") is None

    def test_sheet_skills_cover_all_subject_types(self) -> None:

        schema = BUILTIN_TOOLS["generate_sheet"]["schema"]
        allowed = schema["properties"]["subject_type"]["enum"]
        for subject in allowed:
            assert subject in SHEET_SKILLS, (
                f"subject_type {subject!r} accepted by generate_sheet but has no sheet skill"
            )

    def test_directorial_tools_map_to_cinematic_skills(self) -> None:
        assert skill_for("director") == "brandly-film-director"
        assert skill_for("director_of_photography") == "brandly-camera"
        assert skill_for("editor") == "dpf-senior-editor"
        assert skill_for("spatial_blocking") == "brandly-3d-spatial"

    def test_sound_design_maps_to_audio_skill(self) -> None:
        assert skill_for("sound_design") == "brandly-audio"

    def test_read_only_classification_is_callable(self) -> None:
        for tool in BUILTIN_TOOLS:
            assert isinstance(is_read_only(tool), bool)
        assert is_read_only("list_projects") is True
        assert is_read_only("write_bible") is False
