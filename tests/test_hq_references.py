"""Tests for the HQ reference split.

When a large reference image is found in a project's reference directory,
brandly writes a small down-scaled JPG in place and archives the high-quality
original under ``pre-production/<project>/hq/``. The split is idempotent and
non-destructive (masters are only ever copied into ``hq/``, never deleted),
and can be disabled with ``BRANDLY_HQ_REFS=off``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner
from PIL import Image

from brandly_cli import image_convert, layout


def _big_png(
    root: Path,
    project: str = "p1",
    category: str = "character",
    name: str = "char_master.png",
) -> Path:
    """A large reference plate (bigger than ``HQ_MAX_DIM`` on the long side).

    Built as a smooth vertical gradient so its PNG stays small on disk, making
    the image "large" by *dimension* (not bytes). The down-scaled JPG that the
    split produces is therefore guaranteed to fall under ``HQ_MIN_BYTES``,
    which keeps the idempotency test deterministic.
    """
    cat = root / "pre-production" / project / category
    cat.mkdir(parents=True, exist_ok=True)
    p = cat / name
    w, h = 3000, 2000
    data = b"".join(bytes((0, y % 256, 255 - y % 256)) * w for y in range(h))
    Image.frombytes("RGB", (w, h), data).save(p, "PNG")
    with Image.open(p) as im:
        assert max(im.size) > image_convert.HQ_MAX_DIM
    return p


class TestEnsureHqSplit:
    def test_big_image_becomes_small_jpg_plus_hq_master(self, tmp_path: Path) -> None:
        big = _big_png(tmp_path)
        images_root = layout.resolve_media_root(tmp_path, "p1", "images")
        hq_root = layout.hq_dir(tmp_path, "p1")
        res = image_convert.ensure_hq_split(big, hq_root, images_root)
        assert res is not None
        master = hq_root / "character" / "char_master.png"
        small = images_root / "character" / "char_master.jpg"
        assert master.is_file(), "the high-quality original must be archived under hq/"
        assert small.is_file(), "a small JPG must be written in place"
        assert not big.exists(), "the large original moves out of the category folder"
        with Image.open(small) as im:
            assert im.format == "JPEG"
            assert max(im.size) <= image_convert.HQ_MAX_DIM

    def test_small_image_is_left_alone(self, tmp_path: Path) -> None:
        cat = tmp_path / "pre-production" / "p1" / "location"
        cat.mkdir(parents=True, exist_ok=True)
        tiny = cat / "loc.jpg"
        Image.new("RGB", (200, 120), (10, 20, 30)).save(tiny, "JPEG", quality=60)
        images_root = layout.resolve_media_root(tmp_path, "p1", "images")
        hq_root = layout.hq_dir(tmp_path, "p1")
        assert image_convert.ensure_hq_split(tiny, hq_root, images_root) is None
        assert tiny.exists()
        assert not hq_root.exists()

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        images_root = layout.resolve_media_root(tmp_path, "p1", "images")
        hq_root = layout.hq_dir(tmp_path, "p1")
        missing = images_root / "character" / "nope.png"
        assert image_convert.ensure_hq_split(missing, hq_root, images_root) is None


class TestOptimizeReferences:
    def test_walks_directory_and_splits_large_refs(self, tmp_path: Path) -> None:
        _big_png(tmp_path, category="character", name="char_a.png")
        _big_png(tmp_path, category="prop", name="prop_b.png")
        # dry run: report only, nothing written to hq/
        dry = image_convert.optimize_references(tmp_path, "p1", dry_run=True)
        assert {Path(r["image"]).name for r in dry} == {"char_a.png", "prop_b.png"}
        assert not (tmp_path / "pre-production" / "p1" / "hq").exists()
        # real run: hq masters are written
        res = image_convert.optimize_references(tmp_path, "p1")
        assert len(res) == 2
        hq = tmp_path / "pre-production" / "p1" / "hq"
        assert (hq / "character" / "char_a.png").is_file()
        assert (hq / "prop" / "prop_b.png").is_file()

    def test_is_idempotent(self, tmp_path: Path) -> None:
        _big_png(tmp_path, category="character", name="char_a.png")
        assert len(image_convert.optimize_references(tmp_path, "p1")) == 1
        # only the small JPG remains in the category -> nothing large left to split
        assert image_convert.optimize_references(tmp_path, "p1") == []

    def test_skips_hq_masters_from_discovery(self, tmp_path: Path) -> None:
        _big_png(tmp_path, category="character", name="char_a.png")
        image_convert.optimize_references(tmp_path, "p1")
        found = {p.name for p in layout.discover_project_plates(tmp_path, "p1")}
        assert "char_a.jpg" in found, "the small working reference stays discoverable"
        assert "char_a.png" not in found, "the hq master must not be re-injected"

    def test_disabled_by_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _big_png(tmp_path, category="character", name="char_a.png")
        monkeypatch.setenv("BRANDLY_HQ_REFS", "off")
        assert image_convert.optimize_references(tmp_path, "p1") == []
        assert not (tmp_path / "pre-production" / "p1" / "hq").exists()


class TestOptimizeRefsCommand:
    def test_command_is_registered_and_runs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from brandly_cli.cli import cli

        _big_png(tmp_path, category="character", name="char_master.png")
        monkeypatch.setenv("ROOT", str(tmp_path))
        res = CliRunner().invoke(cli, ["optimize-refs", "p1", "--dry-run"])
        assert res.exit_code == 0, res.output
        assert "char_master.png" in res.output


class TestResamplingApiContract:
    """Guard the Pillow resampling API against the removed bare alias.

    The module-level ``Image.LANCZOS`` alias was dropped from the Pillow>=10
    type stubs and fails ``mypy`` (the CI ``quality`` "Type check" step), which
    is not part of the local gate set. The supported form is
    ``Image.Resampling.LANCZOS`` (already used in ``thumbnails.py``). This
    source-contract test keeps it pinned so the regression is caught by the
    standard pytest run, not only by CI.
    """

    def test_uses_modern_resampling_api(self) -> None:
        import brandly_cli.image_convert as mod

        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "Image.Resampling.LANCZOS" in src, "use the modern Resampling API"
        assert "Image.LANCZOS" not in src, "the removed bare alias must not be used"

