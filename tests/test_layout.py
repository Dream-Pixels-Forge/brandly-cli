"""Tests for the .brandly folder layout (single source of truth: layout.py)."""

from __future__ import annotations

from pathlib import Path

from brandly_cli import layout


class TestLayoutStructure:
    def test_project_dir_is_top_level(self, tmp_path: Path) -> None:
        """New layout stores projects directly under .brandly/, not .brandly/projects/."""
        d = layout.project_dir(tmp_path, "my-project")
        assert d == tmp_path / ".brandly" / "my-project"
        assert layout.legacy_project_dir(tmp_path, "my-project") == (
            tmp_path / ".brandly" / "projects" / "my-project"
        )

    def test_ensure_project_dirs_creates_full_tree(self, tmp_path: Path) -> None:
        proj = layout.project_dir(tmp_path, "p1")
        layout.ensure_project_dirs(proj)

        # docs categories
        for cat in ("plan", "bible", "storyboard", "tmp"):
            assert (proj / "docs" / cat).is_dir()
        # refs
        assert (proj / "refs").is_dir()
        # image categories
        for cat in (
            "prop", "location", "character", "vehicle",
            "mecha", "animal", "plant", "general",
        ):
            assert (proj / "images" / cat).is_dir()
        # video categories
        for cat in ("scenes", "insert", "transition", "general"):
            assert (proj / "videos" / cat).is_dir()
        # audio categories
        for cat in ("soundtrack", "sfx", "foley", "voiceover", "general"):
            assert (proj / "audio" / cat).is_dir()
        # export
        assert (proj / "export").is_dir()

    def test_media_dir_routes_to_category(self, tmp_path: Path) -> None:
        proj = layout.project_dir(tmp_path, "p1")
        assert layout.media_dir(proj, "images", "location") == proj / "images" / "location"
        assert layout.media_dir(proj, "videos", "scenes") == proj / "videos" / "scenes"
        assert layout.media_dir(proj, "audio", "sfx") == proj / "audio" / "sfx"
        # unknown category falls back to general
        assert layout.media_dir(proj, "images", "nonsense") == proj / "images" / "general"
        # default category is general
        assert layout.media_dir(proj, "videos") == proj / "videos" / "general"

    def test_media_dir_rejects_unknown_top(self, tmp_path: Path) -> None:
        proj = layout.project_dir(tmp_path, "p1")
        try:
            layout.media_dir(proj, "documents", "general")
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for unknown top folder")

    def test_docs_dir_coerces_unknown_to_tmp(self, tmp_path: Path) -> None:
        proj = layout.project_dir(tmp_path, "p1")
        assert layout.docs_dir(proj, "plan") == proj / "docs" / "plan"
        assert layout.docs_dir(proj, "bible") == proj / "docs" / "bible"
        assert layout.docs_dir(proj, "storyboard") == proj / "docs" / "storyboard"
        assert layout.docs_dir(proj, "tmp") == proj / "docs" / "tmp"
        assert layout.docs_dir(proj, "weird") == proj / "docs" / "tmp"

    def test_image_category_for_subject(self) -> None:
        assert layout.image_category_for_subject("object") == "prop"
        assert layout.image_category_for_subject("character") == "character"
        assert layout.image_category_for_subject("location") == "location"
        assert layout.image_category_for_subject("mecha") == "mecha"
        assert layout.image_category_for_subject("unknown_type") == "general"

    def test_discover_images_finds_refs_and_images(self, tmp_path: Path) -> None:
        proj = layout.project_dir(tmp_path, "p1")
        layout.ensure_project_dirs(proj)
        (proj / "refs" / "reference_object_1.png").write_bytes(b"x")
        (proj / "images" / "character" / "char_1.png").write_bytes(b"x")
        found = {p.name for p in layout.discover_images(proj)}
        assert "reference_object_1.png" in found
        assert "char_1.png" in found

    def test_resolve_prefers_new_layout_and_falls_back_to_legacy(
        self, tmp_path: Path
    ) -> None:
        # legacy-only project
        legacy = layout.legacy_project_dir(tmp_path, "legacy-only")
        legacy.mkdir(parents=True, exist_ok=True)
        (legacy / "project.json").write_text("{}")
        assert layout.resolve_project_dir(tmp_path, "legacy-only") == legacy

        # new layout wins when both exist
        new = layout.project_dir(tmp_path, "both")
        new.mkdir(parents=True, exist_ok=True)
        (new / "project.json").write_text("{}")
        legacy2 = layout.legacy_project_dir(tmp_path, "both")
        legacy2.mkdir(parents=True, exist_ok=True)
        (legacy2 / "project.json").write_text("{}")
        assert layout.resolve_project_dir(tmp_path, "both") == new

        # neither exists -> new dir returned (created on demand)
        assert layout.resolve_project_dir(tmp_path, "new-only") == layout.project_dir(
            tmp_path, "new-only"
        )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(__import__("pytest").main([__file__, "-v"]))
