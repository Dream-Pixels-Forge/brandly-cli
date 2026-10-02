"""Contract test for the Studio preview PNG (v0.9 docs increment).

RED test: the README Demos section must link a **generated** studio preview
PNG. This file starts missing, so this suite fails until
``scripts/make_studio_preview.py`` runs. The PNG is built only from committed
sources (no localhost, no browser) so the README image always mirrors the
actual web bundle.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PNG = REPO_ROOT / "assets" / "studio-preview.png"
GENERATOR = REPO_ROOT / "scripts" / "make_studio_preview.py"

EXPECTED_SIZE = (1440, 900)
GENERATOR_SOURCES = [
    "web/src/panelLabels.ts",
    "web/index.html",
    "web/src/components/panels/ShotListPanel.tsx",
    "web/src/components/panels/TransportControls.tsx",
]


class TestStudioPreviewPng:
    def test_preview_png_exists(self) -> None:
        assert PNG.is_file(), (
            "assets/studio-preview.png missing — run "
            "python scripts/make_studio_preview.py (issue: README Demos needs it)"
        )

    def test_preview_png_is_real_1440x900(self) -> None:
        from PIL import Image

        with Image.open(PNG) as img:
            assert img.format == "PNG"
            assert img.size == EXPECTED_SIZE, f"expected 1440x900, got {img.size}"
            assert img.mode in ("RGB", "RGBA")

    def test_preview_png_is_dark_studio_not_blank(self) -> None:
        from PIL import Image, ImageStat

        with Image.open(PNG).convert("RGB") as img:
            assert img.getpixel((720, 450)) != img.getpixel((5, 5)), (
                "render is flat — expected distinct stage vs chrome regions"
            )
            mean = ImageStat.Stat(img).mean
            assert sum(mean) / 3 < 110, f"mean too bright for dark UI: {mean}"

    def test_generator_maps_committed_sources_only(self) -> None:
        assert GENERATOR.is_file(), "scripts/make_studio_preview.py missing"
        body = GENERATOR.read_text(encoding="utf-8")
        for src in GENERATOR_SOURCES:
            assert src in body, f"generator must read {src} (no invented layout)"



    def test_readme_demos_links_producer_videos_and_preview(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "## Demos" in readme
        assert "F1tr08UeHLs" in readme
        assert "7lNt1Y8tAzo" in readme
        assert "assets/studio-preview.png" in readme
