r"""Issue #197: a plate auto-injectable by ``discover_project_plates`` must be
resolvable by bare stem on the shot side.

``layout.discover_project_plates`` (the auto-ref injection source behind
``planning.get_reference_image_urls``) reaches every sub-folder of the images
root — ``general``, ``vehicle``, ``mecha``, ``animal``, ``plant``,
``keyframe``, ``storyboard`` and arbitrary nested dirs — plus the legacy
``.brandly/<id>/images/`` tree, while ``shot_runner.resolve_plate`` only
searched the four ``REF_CATEGORIES`` roots. A plate in any other location was
happily auto-injected by ``brandly video`` yet raised ``FileNotFoundError``
the moment a shot list named it by bare stem — the split-brain this issue
tracks.

Run under ``.venv\\Scripts\\python`` (editable install points at ``src/``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from brandly_cli import layout, shot_runner


def _plate(root: Path, pid: str, category: str, name: str) -> Path:
    """Create a tiny PNG plate at ``pre-production/<pid>/<category>/<name>``."""
    p = root / "pre-production" / pid / category / name
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (0, 0, 0)).save(p, "PNG")
    return p


class TestAutoInjectedPlatesResolve:
    def test_general_category_plate_resolves(self, tmp_path: Path) -> None:
        # `general` is a real IMAGE_CATEGORIES folder but not a REF_CATEGORIES
        # root: discover_project_plates reaches it, so resolve_plate must too.
        pid = "gp"
        _plate(tmp_path, pid, "general", "mood_board.opt.jpg")
        got = shot_runner.resolve_plate(
            "mood_board", tmp_path / "pre-production" / pid
        )
        assert got.parent.name == "general"
        assert got.name == "mood_board.opt.jpg"

    def test_vehicle_category_plate_resolves(self, tmp_path: Path) -> None:
        # Same split-brain for every other non-REF_CATEGORIES folder.
        pid = "vp"
        _plate(tmp_path, pid, "vehicle", "rover.jpg")
        got = shot_runner.resolve_plate(
            "rover", tmp_path / "pre-production" / pid
        )
        assert got.parent.name == "vehicle"

    def test_nested_sub_folder_plate_resolves(self, tmp_path: Path) -> None:
        # A plate in a non-category nested sub-folder reached via rglob.
        pid = "np"
        nested = tmp_path / "pre-production" / pid / "location" / "exterior"
        nested.mkdir(parents=True, exist_ok=True)
        p = nested / "docks.opt.jpg"
        Image.new("RGB", (8, 8), (0, 0, 0)).save(p, "PNG")
        got = shot_runner.resolve_plate(
            "docks", tmp_path / "pre-production" / pid
        )
        assert got.name == "docks.opt.jpg"

    def test_legacy_tree_plate_resolves(self, tmp_path: Path) -> None:
        # A v1 project: the plate lives only in the legacy
        # .brandly/<id>/images/ tree, discover_project_plates' second base.
        pid = "lp"
        legacy = tmp_path / ".brandly" / pid / "images" / "character"
        legacy.mkdir(parents=True, exist_ok=True)
        p = legacy / "char_old.jpg"
        Image.new("RGB", (8, 8), (0, 0, 0)).save(p, "PNG")
        # Auto-ref injection finds it...
        plates = layout.discover_project_plates(tmp_path, pid)
        assert p.resolve() in [q.resolve() for q in plates]
        # ...so the shot side must resolve it by bare stem too.
        got = shot_runner.resolve_plate(
            "char_old", tmp_path / "pre-production" / pid
        )
        assert got.name == "char_old.jpg"

    def test_injection_resolution_parity(self, tmp_path: Path) -> None:
        # The alignment invariant: every plate discover_project_plates finds
        # (outside hq/) must resolve by bare stem on the shot side.
        pid = "pp"
        for category, name in (
            ("character", "char_a.jpg"),
            ("prop", "prop_b.jpg"),
            ("general", "mood_c.jpg"),
            ("vehicle", "rover_d.jpg"),
        ):
            _plate(tmp_path, pid, category, name)
        plates = layout.discover_project_plates(tmp_path, pid)
        assert len(plates) == 4
        for plate in plates:
            resolved = shot_runner.resolve_plate(
                plate.stem, tmp_path / "pre-production" / pid
            )
            assert resolved.exists()

    def test_hq_master_still_never_resolves(self, tmp_path: Path) -> None:
        # Guard: the rglob fallback must keep skipping hq/ segments — an
        # archived master is never a live reference (issue #117 contract).
        pid = "hp"
        master = (
            tmp_path / "pre-production" / pid / "character" / "hq" / "char_x.jpg"
        )
        master.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 8), (0, 0, 0)).save(master, "JPEG")
        with pytest.raises(FileNotFoundError):
            shot_runner.resolve_plate(
                "char_x", tmp_path / "pre-production" / pid
            )

    def test_missing_stem_still_raises(self, tmp_path: Path) -> None:
        # Guard: a genuinely absent stem still fails loudly.
        pid = "mp"
        _plate(tmp_path, pid, "character", "char_a.opt.jpg")
        with pytest.raises(FileNotFoundError):
            shot_runner.resolve_plate(
                "nope", tmp_path / "pre-production" / pid
            )
