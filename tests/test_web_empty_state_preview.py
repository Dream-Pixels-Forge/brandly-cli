"""Contract test: the web UI shows a still plate when there is no footage yet.

RED test for the empty-state increment. ``PreviewPanel`` previously rendered a
bare ``videocam_off`` glyph for *every* case with no video, which conflated two
different states:

* **no clips at all** — the project has no generated footage yet; and
* **clips exist, none selected** — a normal "pick a clip" affordance.

The first deserves the still plate (``web/public/preview.jpg``); the second must
keep its existing hint. This suite pins that distinction, and pins the
data-honesty rule: the plate is a **placeholder**, never presented as generated
footage, so it must carry a visible label.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLATE = REPO_ROOT / "web" / "public" / "preview.jpg"
PANEL = REPO_ROOT / "web" / "src" / "components" / "panels" / "PreviewPanel.tsx"


class TestEmptyStatePlate:
    def test_plate_ships_in_web_public(self) -> None:
        """The plate must live in ``web/public`` — Vite's ``emptyOutDir: true``
        wipes ``src/brandly_cli/web/static`` on every build, so an asset kept
        only in the built output would not survive the next build."""
        assert PLATE.is_file(), (
            "web/public/preview.jpg missing — the empty-state plate must be a "
            "committed source under web/public/ (vite emptyOutDir wipes the build)"
        )

    def test_plate_is_a_real_jpeg(self) -> None:
        from PIL import Image

        with Image.open(PLATE) as img:
            assert img.format == "JPEG", f"expected JPEG, got {img.format}"
            w, h = img.size
            assert w >= 1280 and h >= 720, f"plate too small to read as a stage: {img.size}"
            assert abs((w / h) - (16 / 9)) < 0.05, f"plate must be 16:9, got {img.size}"

    def test_plate_is_not_gitignored(self) -> None:
        """It is a shipped UI asset, not design scratch. The design-scratch
        rules cover ``preview.png``; this file is a different extension and a
        different purpose, so it must stay trackable."""
        ignore = REPO_ROOT / ".gitignore"
        patterns = [
            ln.strip()
            for ln in ignore.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")
        ]
        assert not any(p == "preview.jpg" for p in patterns), (
            ".gitignore ignores preview.jpg — it is a shipped web asset, not scratch"
        )

    def test_panel_references_the_plate(self) -> None:
        body = PANEL.read_text(encoding="utf-8")
        assert "preview.jpg" in body, "PreviewPanel must reference preview.jpg"
        # Vite base is '/static/', so the built asset is served from there.
        assert "/static/preview.jpg" in body, (
            "plate must be addressed as /static/preview.jpg (vite base is /static/)"
        )

    def test_plate_is_gated_on_no_clips_not_no_selection(self) -> None:
        """The plate is for 'no footage yet'. A project that has clips but no
        selection must keep the 'Select a clip to preview' hint instead."""
        body = PANEL.read_text(encoding="utf-8")
        assert "clips.length === 0" in body, (
            "plate must be gated on an empty clip list, not merely a null selection"
        )
        assert "Select a clip to preview" in body, (
            "the has-clips/none-selected hint must be preserved"
        )

    def test_plate_is_labelled_as_placeholder(self) -> None:
        """Data honesty (AGENTS.md): a still must never read as generated
        footage. The empty state must name what it is."""
        body = PANEL.read_text(encoding="utf-8")
        assert "NO FOOTAGE YET" in body, (
            "placeholder must be labelled so it is not mistaken for a real clip"
        )
