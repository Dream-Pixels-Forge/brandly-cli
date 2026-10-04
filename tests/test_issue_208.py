r"""Issue #208: ``discover_project_plates`` skips only the *top-level* ``hq/``
folder, so a master nested deeper (``pre-production/<id>/character/hq/x.jpg``)
is still auto-injected as a live reference — violating the documented contract
(``hq_dir``'s docstring: "masters are never re-injected as live references")
and re-creating the split-brain against the shot-side resolver, which correctly
refuses any ``hq/`` segment (issue #117 contract, pinned by
``test_hq_master_is_never_a_live_reference``).

Run under ``.venv\\Scripts\\python`` (editable install points at ``src/``).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from brandly_cli import layout, planning


def _png(path: Path) -> Path:
    """A stub plate file (discovery only checks the name, never the bytes)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG")
    return path


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


class TestNestedHqMasterNotInjected:
    def test_nested_hq_master_is_not_discovered(self, tmp_path: Path) -> None:
        # A master nested under a CATEGORY's hq/ segment: parts[0] is the
        # category, so the top-level-only skip missed it.
        pid = "p1"
        working = _png(tmp_path / "pre-production" / pid / "character" / "char.png")
        nested_master = _png(
            tmp_path / "pre-production" / pid / "character" / "hq" / "char_x.png"
        )
        found = {p.name for p in layout.discover_project_plates(tmp_path, pid)}
        assert working.name in found, "the live working reference stays discoverable"
        assert (
            nested_master.name not in found
        ), "a nested hq master must not be re-injected"

    def test_nested_hq_master_is_not_auto_injected(self, tmp_path: Path) -> None:
        # The auto-ref injection path must not hand a nested master to the model.
        pid = "ai"
        nested_master = _png(
            tmp_path / "pre-production" / pid / "character" / "hq" / "char_y.png"
        )
        urls = planning.get_reference_image_urls(pid, root=tmp_path)
        assert nested_master.name not in [Path(u).name for u in urls]

    def test_legacy_tree_nested_hq_master_skipped(self, tmp_path: Path) -> None:
        # The legacy base scans the same rule: any hq/ segment is skipped.
        pid = "lp"
        _png(tmp_path / ".brandly" / pid / "images" / "character" / "char_old.png")
        _png(
            tmp_path
            / ".brandly"
            / pid
            / "images"
            / "character"
            / "hq"
            / "old_master.png"
        )
        found = {p.name for p in layout.discover_project_plates(tmp_path, pid)}
        assert "char_old.png" in found
        assert "old_master.png" not in found

    def test_optimize_references_never_re_splits_a_nested_master(
        self, tmp_path: Path
    ) -> None:
        # optimize_references walks via discover_project_plates: a nested
        # master is already archived, so it must not be re-split.
        from brandly_cli import image_convert

        pid = "or"
        _big_png(tmp_path / "pre-production" / pid / "character" / "hq" / "char_z.png")
        res = image_convert.optimize_references(tmp_path, pid)
        assert res == [], "a nested hq master must not be re-split"

    def test_top_level_hq_master_still_skipped(self, tmp_path: Path) -> None:
        # Guard: the existing contract (issue #117) is unchanged.
        pid = "tp"
        _png(tmp_path / "pre-production" / pid / "character" / "char.png")
        _png(
            tmp_path / "pre-production" / pid / "hq" / "character" / "char_master.png"
        )
        found = {p.name for p in layout.discover_project_plates(tmp_path, pid)}
        assert "char.png" in found
        assert "char_master.png" not in found
