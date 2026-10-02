"""Issue #117: init creates a legacy .brandly/<id>/images|videos|audio tree
that resolve_media_root never reads, and plate discovery scans only that
tree - so v2 plates placed (or generated) under pre-production/<id>/ are
invisible to auto-refs.

Fixes:
- ensure_project_tree(): v2-aware creation (docs + export under .brandly/<id>/;
  image categories under pre-production/<id>/; videos+audio under
  production/<id>/). The misleading legacy media tree is no longer created.
- discover_project_plates(): v2 media root first, legacy tree fallback.
- detect_project_artifacts() uses the plate discovery.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from brandly_cli import layout, planning
from brandly_cli.project_manager import ProjectData, ProjectManager

PID = "tree-proj"


def test_ensure_project_tree_creates_v2_layout(tmp_path: Path) -> None:
    layout.ensure_project_tree(tmp_path, PID)
    assert (tmp_path / ".brandly" / PID / "docs" / "plan").is_dir()
    assert (tmp_path / ".brandly" / PID / "docs" / "tmp").is_dir()
    # Exports are production outputs (v2 layout) — not project state.
    assert (tmp_path / "production" / PID / "export").is_dir()
    assert not (tmp_path / ".brandly" / PID / "export").exists()
    # media trees live in the v2 roots
    assert (tmp_path / "pre-production" / PID / "character").is_dir()
    assert (tmp_path / "pre-production" / PID / "prop").is_dir()
    assert (tmp_path / "pre-production" / PID / "storyboard").is_dir()
    assert (tmp_path / "production" / PID / "videos" / "scenes").is_dir()
    assert (tmp_path / "production" / PID / "audio" / "soundtrack").is_dir()


def test_ensure_project_tree_does_not_create_legacy_media_tree(tmp_path: Path) -> None:
    layout.ensure_project_tree(tmp_path, PID)
    assert not (tmp_path / ".brandly" / PID / "images").exists()
    assert not (tmp_path / ".brandly" / PID / "videos").exists()
    assert not (tmp_path / ".brandly" / PID / "audio").exists()


def test_project_create_uses_v2_tree(tmp_path: Path) -> None:
    pm = ProjectManager(tmp_path)
    data = ProjectData(id=PID, name="T", description="d")
    asyncio.run(pm.create(data))
    assert (tmp_path / "pre-production" / PID / "character").is_dir()
    assert (tmp_path / "production" / PID / "videos" / "scenes").is_dir()
    assert not (tmp_path / ".brandly" / PID / "images").exists()
    assert (tmp_path / ".brandly" / PID / "docs" / "plan").is_dir()


def test_discover_plates_v2_first(tmp_path: Path) -> None:
    v2 = tmp_path / "pre-production" / PID / "character" / "char_a.png"
    v2.parent.mkdir(parents=True)
    v2.write_bytes(b"png")
    plates = layout.discover_project_plates(tmp_path, PID)
    assert str(v2) in [str(p) for p in plates]


def test_discover_plates_legacy_fallback(tmp_path: Path) -> None:
    legacy = tmp_path / ".brandly" / PID / "images" / "character" / "char_old.png"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"png")
    plates = layout.discover_project_plates(tmp_path, PID)
    assert str(legacy) in [str(p) for p in plates]


def test_detect_project_artifacts_finds_v2_plates(tmp_path: Path) -> None:
    plate = tmp_path / "pre-production" / PID / "prop" / "prop_thing.jpg"
    plate.parent.mkdir(parents=True)
    plate.write_bytes(b"jpg")
    urls = planning.get_reference_image_urls(PID, root=tmp_path)
    assert str(plate) in urls
