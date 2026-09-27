"""Issue #125: the timeline editor is empty for v2-layout projects.

produce writes clips to the v2 media root (production/<id>/videos/scenes)
via layout.resolve_media_root, but web/state.py scanned only the legacy
.brandly/<id>/videos tree, and every clip-path consumer joined the stored
relative path against the legacy project dir. Both the scan and the
resolution must be media-root aware (v2 first, legacy fallback for v1
projects).
"""

from __future__ import annotations

from pathlib import Path

from brandly_cli.web import deps
from brandly_cli.web.state import TimelineState, resolve_media_file

PROJECT = "test-proj"


def _setup_project(root: Path) -> None:
    (root / ".brandly" / PROJECT / "docs" / "tmp").mkdir(parents=True, exist_ok=True)


def _write_clip(root: Path, rel: str, name: str) -> Path:
    """Write a dummy mp4 at root/rel/name."""
    path = root / rel / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00\x00\x00\x18ftypmp42")  # mp4 header-ish; path-only checks
    return path


V2_SCENES = f"production/{PROJECT}/videos/scenes"
LEGACY_SCENES = f".brandly/{PROJECT}/videos/scenes"


def test_timeline_builds_from_v2_media_root(tmp_path: Path) -> None:
    _setup_project(tmp_path)
    _write_clip(tmp_path, V2_SCENES, "Scene-01-Shot-1-1.mp4")
    timeline = TimelineState(PROJECT, tmp_path).load()
    assert [c.id for c in timeline.clips] == ["Scene-01-Shot-1-1"]
    assert timeline.clips[0].clip_path == "videos/scenes/Scene-01-Shot-1-1.mp4"


def test_timeline_still_builds_from_legacy_root(tmp_path: Path) -> None:
    _setup_project(tmp_path)
    _write_clip(tmp_path, LEGACY_SCENES, "Scene-01-Shot-1-1.mp4")
    timeline = TimelineState(PROJECT, tmp_path).load()
    assert [c.id for c in timeline.clips] == ["Scene-01-Shot-1-1"]


def test_v2_clip_wins_when_both_trees_exist(tmp_path: Path) -> None:
    _setup_project(tmp_path)
    _write_clip(tmp_path, V2_SCENES, "Scene-01-Shot-1-1.mp4")
    _write_clip(tmp_path, LEGACY_SCENES, "Scene-01-Shot-1-1.mp4")
    timeline = TimelineState(PROJECT, tmp_path).load()
    assert [c.id for c in timeline.clips] == ["Scene-01-Shot-1-1"]


def test_transition_clips_scanned_from_v2_root(tmp_path: Path) -> None:
    _setup_project(tmp_path)
    _write_clip(tmp_path, f"production/{PROJECT}/videos/transition", "Scene-01-Shot-1-2.mp4")
    timeline = TimelineState(PROJECT, tmp_path).load()
    assert [c.id for c in timeline.clips] == ["Scene-01-Shot-1-2"]


def test_resolve_media_file_prefers_v2(tmp_path: Path) -> None:
    _setup_project(tmp_path)
    v2 = _write_clip(tmp_path, V2_SCENES, "Scene-01-Shot-1-1.mp4")
    legacy = _write_clip(tmp_path, LEGACY_SCENES, "Scene-01-Shot-1-1.mp4")
    resolved = resolve_media_file(tmp_path, PROJECT, "videos/scenes/Scene-01-Shot-1-1.mp4")
    assert resolved == v2
    assert resolved != legacy


def test_resolve_media_file_falls_back_to_legacy(tmp_path: Path) -> None:
    _setup_project(tmp_path)
    legacy = _write_clip(tmp_path, LEGACY_SCENES, "Scene-01-Shot-1-1.mp4")
    resolved = resolve_media_file(tmp_path, PROJECT, "videos/scenes/Scene-01-Shot-1-1.mp4")
    assert resolved == legacy


def test_clip_media_path_resolves_v2(tmp_path: Path) -> None:
    from brandly_cli.web.models import Clip

    _setup_project(tmp_path)
    v2 = _write_clip(tmp_path, V2_SCENES, "Scene-01-Shot-1-1.mp4")
    clip = Clip(
        id="Scene-01-Shot-1-1",
        shot_id="shot-1-1",
        clip_path="videos/scenes/Scene-01-Shot-1-1.mp4",
        prompt="p",
    )
    assert deps.clip_media_path(tmp_path, PROJECT, clip) == v2
