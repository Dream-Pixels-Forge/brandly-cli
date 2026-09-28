"""Shared route dependencies: project/clip lookup with containment enforced.

Every route resolves projects and clips through here so a crafted id or
``clip_path`` can never reach a file outside the project directory.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from brandly_cli import layout
from brandly_cli.io import is_valid_project_id
from brandly_cli.web.models import Clip
from brandly_cli.web.security import safe_join
from brandly_cli.web.state import TimelineState, resolve_media_file


def require_project_dir(root: Path, project_id: str) -> Path:
    """Return ``.brandly/<project_id>`` or raise 404.

    Unsafe ids (``..``, separators, drive letters, reserved names) are rejected
    before any filesystem access, so unknown ids can never create directories.
    """
    if is_valid_project_id(project_id):
        proj_dir = safe_join(layout.brandly_dir(root), project_id)
        if proj_dir is not None and proj_dir.is_dir():
            return proj_dir
    raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


def require_clip(root: Path, project_id: str, clip_id: str) -> tuple[Path, Clip]:
    """Return ``(project_dir, clip)`` for a timeline clip, or raise 404."""
    proj_dir = require_project_dir(root, project_id)
    clip = TimelineState(project_id, root).get_clip(clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail=f"Clip not found: {clip_id}")
    return proj_dir, clip


def clip_media_path(root: Path, project_id: str, clip: Clip) -> Path | None:
    """Resolve a clip's media file, v2 media root first, else ``None``.

    Issue #125: delegates to :func:`state.resolve_media_file` so stored
    relative paths resolve against ``production/<id>/`` (where produce
    writes) before the legacy ``.brandly/<id>/`` tree. Containment is
    enforced on every candidate.
    """
    return resolve_media_file(root, project_id, clip.clip_path or "")


def require_clip_media(root: Path, project_id: str, clip_id: str) -> tuple[Path, Path]:
    """Return ``(project_dir, media_file)`` or raise 404."""
    proj_dir, clip = require_clip(root, project_id, clip_id)
    media = clip_media_path(root, project_id, clip)
    if media is None:
        raise HTTPException(status_code=404, detail=f"Clip file not found: {clip_id}")
    return proj_dir, media


def require_clip_media_file(root: Path, project_id: str, clip_id: str) -> Path:
    """Return just the clip's media file, or raise 404."""
    return require_clip_media(root, project_id, clip_id)[1]
