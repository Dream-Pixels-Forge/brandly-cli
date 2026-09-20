"""Tests for the .brandly folder layout (single source of truth: layout.py)."""

from __future__ import annotations

from pathlib import Path

from brandly_cli import layout


class TestLayoutStructure:
    def test_project_dir_is_top_level(self, tmp_path: Path) -> None:
        """Projects are stored directly under .brandly/, not .brandly/projects/."""
        d = layout.project_dir(tmp_path, "my-project")
        assert d == tmp_path / ".brandly" / "my-project"

    def test_ensure_project_dirs_creates_full_tree(self, tmp_path: Path) -> None:
        proj = layout.project_dir(tmp_path, "p1")
        layout.ensure_project_dirs(proj)

        # docs categories
        for cat in ("plan", "bible", "storyboard", "tmp"):
            assert (proj / "docs" / cat).is_dir()
        # no duplicate refs folder — references live under images/
        assert not (proj / "refs").exists()
        # image categories
        for cat in (
            "prop", "location", "character", "vehicle",
            "mecha", "animal", "plant", "keyframe", "general",
        ):
            assert (proj / "images" / cat).is_dir()
        # video categories
        for cat in ("scenes", "insert", "transition", "general"):
            assert (proj / "videos" / cat).is_dir()
        # audio categories
        for cat in ("soundtrack", "sfx", "foley", "voiceover", "general"):
            assert (proj / "audio" / cat).is_dir()
        # 3d-spatial categories
        for cat in ("cameras", "keyframes", "depthmaps", "general"):
            assert (proj / "3d-spatial" / cat).is_dir()
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
        assert layout.image_category_for_subject("keyframe") == "keyframe"
        assert layout.image_category_for_subject("unknown_type") == "general"

    def test_discover_images_scans_images_tree(self, tmp_path: Path) -> None:
        """All reference images live under images/ (no separate refs tree)."""
        proj = layout.project_dir(tmp_path, "p1")
        layout.ensure_project_dirs(proj)
        (proj / "images" / "prop" / "reference_object_1.png").write_bytes(b"x")
        (proj / "images" / "character" / "char_1.png").write_bytes(b"x")
        found = {p.name for p in layout.discover_images(proj)}
        assert "reference_object_1.png" in found
        assert "char_1.png" in found


    def test_image_name_prefix_mapping(self) -> None:
        assert layout.image_name_prefix("character") == "char"
        assert layout.image_name_prefix("location") == "loc"
        assert layout.image_name_prefix("object") == "prop"
        assert layout.image_name_prefix("prop") == "prop"
        # other subject types fall back to their lowercased name
        assert layout.image_name_prefix("vehicle") == "vehicle"
        assert layout.image_name_prefix("mecha") == "mecha"
        assert layout.image_name_prefix(None) is None
        assert layout.image_name_prefix("") is None

    def test_build_sheet_filename_convention(self) -> None:
        # character -> char_<name>
        assert layout.build_sheet_filename(
            "character", "Maya Lin", "2026-01-01_000000"
        ) == "char_maya_lin_2026-01-01_000000.png"
        # location -> loc_<name>
        assert layout.build_sheet_filename(
            "location", "Modern Loft", "2026-01-01_000000"
        ) == "loc_modern_loft_2026-01-01_000000.png"
        # object -> prop_<name>
        assert layout.build_sheet_filename(
            "object", "Nike Air Max 1", "2026-01-01_000000"
        ) == "prop_nike_air_max_1_2026-01-01_000000.png"
        # unknown type keeps a readable prefix
        assert layout.build_sheet_filename(
            "vehicle", "Porsche 911", "2026-01-01_000000"
        ) == "vehicle_porsche_911_2026-01-01_000000.png"
        # custom extension
        assert layout.build_sheet_filename(
            "character", "Maya", "ts", ext=".jpg"
        ) == "char_maya_ts.jpg"

    def test_image_name_token_slugifies(self) -> None:
        assert layout.image_name_token("Nike Air Max 1") == "nike_air_max_1"
        assert layout.image_name_token("A--B  C") == "a_b_c"
        assert layout.image_name_token("!!!") == "image"  # no valid chars -> fallback
    def test_resolve_project_dir_returns_new_layout(
        self, tmp_path: Path
    ) -> None:
        # resolve is a plain alias for project_dir now (no legacy fallback)
        assert layout.resolve_project_dir(tmp_path, "p1") == layout.project_dir(
            tmp_path, "p1"
        )

        # a stale .brandly/projects/<id>/ dir is ignored
        legacy = tmp_path / ".brandly" / "projects" / "legacy-only"
        legacy.mkdir(parents=True, exist_ok=True)
        (legacy / "project.json").write_text("{}")
        assert layout.resolve_project_dir(tmp_path, "legacy-only") == (
            tmp_path / ".brandly" / "legacy-only"
        )

        # neither exists -> the canonical dir is returned
        assert layout.resolve_project_dir(tmp_path, "new-only") == (
            tmp_path / ".brandly" / "new-only"
        )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(__import__("pytest").main([__file__, "-v"]))
