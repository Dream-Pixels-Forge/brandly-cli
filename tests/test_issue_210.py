r"""Issue #210: ``image_convert.ensure_hq_split`` documents "No-op (returns
None) when ... already lives under ``hq/``", but its implementation only
checked the *top-level* folder (``rel.parts[0] == layout.HQ_DIRNAME``). An
image nested deeper — ``pre-production/<id>/character/hq/x.png`` — was
re-split: the master copied to the top-level ``hq/character/`` (a duplicate of
an already-archived master) and a small JPG written *inside* ``character/hq/``.
#208 fixed the walker path (``optimize_references`` -> ``discover_project_plates``
now skips any ``hq/`` segment); this pins the direct-call path to the same
documented contract.

Run under ``.venv\\Scripts\\python`` (editable install points at ``src/``).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from brandly_cli import image_convert, layout


def _big_png(path: Path) -> Path:
    """A large *valid* PNG (bigger than ``HQ_MAX_DIM`` on the long side).

    Built as a smooth vertical gradient so the PNG stays small on disk while
    being "large" by dimension — the shape ``ensure_hq_split`` looks for.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    w, h = 3000, 2000
    data = b"".join(bytes((0, y % 256, 255 - y % 256)) * w for y in range(h))
    Image.frombytes("RGB", (w, h), data).save(path, "PNG")
    return path


class TestEnsureHqSplitNestedGuard:
    def test_nested_hq_image_is_a_noop(self, tmp_path: Path) -> None:
        # An image under a CATEGORY's hq/ segment is an archived master, not
        # a splittable live reference (the documented contract).
        pid = "p1"
        nested = _big_png(
            tmp_path / "pre-production" / pid / "character" / "hq" / "char_x.png"
        )
        images_root = layout.resolve_media_root(tmp_path, pid, "images")
        hq_root = layout.hq_dir(tmp_path, pid)
        res = image_convert.ensure_hq_split(nested, hq_root, images_root)
        assert res is None, "a nested hq image must not be re-split"
        # Nothing was written or deleted: the master stays where it is.
        assert nested.is_file()
        assert not (hq_root / "character" / "char_x.png").exists()
        assert not (nested.parent / "char_x.jpg").exists()

    def test_nested_hq_image_in_legacy_tree_is_a_noop(self, tmp_path: Path) -> None:
        # A nested master in the legacy tree is not under the v2 images_root
        # at all, so it is already a no-op — pin that too.
        pid = "lp"
        nested = _big_png(
            tmp_path / ".brandly" / pid / "images" / "character" / "hq" / "old.png"
        )
        images_root = layout.resolve_media_root(tmp_path, pid, "images")
        hq_root = layout.hq_dir(tmp_path, pid)
        assert image_convert.ensure_hq_split(nested, hq_root, images_root) is None
        assert nested.is_file()

    def test_top_level_hq_image_still_a_noop(self, tmp_path: Path) -> None:
        # Guard: the existing contract (already under the top-level hq/) is
        # unchanged.
        pid = "tp"
        master = _big_png(
            tmp_path / "pre-production" / pid / "hq" / "character" / "m.png"
        )
        images_root = layout.resolve_media_root(tmp_path, pid, "images")
        hq_root = layout.hq_dir(tmp_path, pid)
        assert image_convert.ensure_hq_split(master, hq_root, images_root) is None
        assert master.is_file()

    def test_category_root_image_still_splits(self, tmp_path: Path) -> None:
        # Guard: the normal split path is unaffected by the deeper guard.
        pid = "cp"
        big = _big_png(tmp_path / "pre-production" / pid / "character" / "char.png")
        images_root = layout.resolve_media_root(tmp_path, pid, "images")
        hq_root = layout.hq_dir(tmp_path, pid)
        res = image_convert.ensure_hq_split(big, hq_root, images_root)
        assert res is not None
        assert (hq_root / "character" / "char.png").is_file()
        assert (images_root / "character" / "char.jpg").is_file()
        assert not big.exists()
