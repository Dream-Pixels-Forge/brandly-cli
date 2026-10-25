"""Casting routes (design: dev-notes/DESIGN-CASTING-DOCS-PANELS.md).

Read-only serving of the cast reference plates (character + wardrobe
categories) so the web Casting panel can display cast images and sheets.
v2 media root first (``pre-production/<id>/<category>/``), legacy
``.brandly/<id>/images/<category>/`` fallback. ``hq/`` masters are never
listed or served.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from brandly_cli import layout
from brandly_cli.web import deps, security

router = APIRouter(prefix="/api/projects/{project_id}/cast", tags=["cast"])

#: The only categories the Casting panel serves (design §3 whitelist).
CAST_CATEGORIES: tuple[str, ...] = ("character", "wardrobe")

#: Design §3: no separators, no leading dot/slash.
_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _cast_roots(root: Path, project_id: str) -> list[tuple[str, Path]]:
    """(category, dir) scan roots — v2 media root first, legacy fallback."""
    proj_dir = deps.require_project_dir(root, project_id)
    roots: list[tuple[str, Path]] = []
    for category in CAST_CATEGORIES:
        roots.append(
            (category, layout.resolve_media_root(root, project_id, "images") / category)
        )
        roots.append((category, proj_dir / "images" / category))
    return roots


def _list_category(root: Path, project_id: str, category: str) -> list[dict]:
    items: list[dict] = []
    for cat, base in _cast_roots(root, project_id):
        if cat != category or not base.is_dir():
            continue
        for ext in layout._IMAGE_EXTS:
            for path in base.glob(ext):
                rel = path.relative_to(base)
                if layout.HQ_DIRNAME in rel.parts:
                    continue
                stat = path.stat()
                items.append(
                    {
                        "category": cat,
                        "filename": path.name,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(timespec="seconds"),
                    }
                )
    return items


@router.get("", response_model=dict)
async def list_cast(project_id: str, request: Request) -> dict:
    """All cast plates, sorted by category then filename, hq/ excluded."""
    root = request.app.state.root
    items: list[dict] = []
    for category in CAST_CATEGORIES:
        items.extend(_list_category(root, project_id, category))
    items.sort(key=lambda item: (item["category"], item["filename"]))
    return {"project_id": project_id, "items": items}


def _resolve_media(
    root: Path, project_id: str, category: str, filename: str
) -> Path:
    """Resolve a cast image safely, or raise 404."""
    if category not in CAST_CATEGORIES or not _FILENAME_RE.match(filename):
        raise HTTPException(status_code=404, detail="Cast media not found")
    deps.require_project_dir(root, project_id)
    for base in (
        layout.resolve_media_root(root, project_id, "images") / category,
        layout.project_dir(root, project_id) / "images" / category,
    ):
        candidate = security.safe_join(base, filename)
        if candidate is not None and candidate.is_file():
            return candidate
    raise HTTPException(status_code=404, detail="Cast media not found")


@router.get("/media/{category}/{filename}")
async def cast_media(
    project_id: str, category: str, filename: str, request: Request
) -> FileResponse:
    """Stream one cast image (token-guarded like the review media route)."""
    root = request.app.state.root
    media = _resolve_media(root, project_id, category, filename)
    return FileResponse(str(media))
