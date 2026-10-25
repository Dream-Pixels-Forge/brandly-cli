"""Project Docs routes (design: dev-notes/DESIGN-CASTING-DOCS-PANELS.md).

Read-only serving of every generated document under
``.brandly/<id>/docs/**`` (plan, bible, storyboard, screenplay, general,
tmp — all categories, tmp labelled "Working" in the UI) so the web Docs
panel can display all documents generated for a project.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from brandly_cli import layout
from brandly_cli.web import deps, security

router = APIRouter(prefix="/api/projects/{project_id}/docs", tags=["docs"])

#: Design §3 — UTF-8 text is served capped at 1 MiB with an honest flag.
MAX_CONTENT_BYTES = 1024 * 1024


def _doc_entry(docs_base: Path, path: Path) -> dict:
    stat = path.stat()
    return {
        "path": path.relative_to(docs_base).as_posix(),
        "category": path.relative_to(docs_base).parts[0],
        "filename": path.name,
        "size_bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(
            timespec="seconds"
        ),
    }


@router.get("", response_model=dict)
async def list_docs(project_id: str, request: Request) -> dict:
    """Every generated document, all categories, sorted category then path."""
    root = request.app.state.root
    proj_dir = deps.require_project_dir(root, project_id)
    docs_base = proj_dir / "docs"
    items = [
        _doc_entry(docs_base, path)
        for path in layout.discover_docs(proj_dir)
        if path.is_file()
    ]
    items.sort(key=lambda item: (item["category"], item["path"]))
    return {"project_id": project_id, "items": items}


@router.get("/content", response_model=dict)
async def doc_content(project_id: str, request: Request, path: str) -> dict:
    """Serve one document's UTF-8 text, capped at 1 MiB (honest truncation)."""
    root = request.app.state.root
    proj_dir = deps.require_project_dir(root, project_id)
    docs_base = proj_dir / "docs"
    if not path or path.startswith("/") or "\\" in path or ".." in Path(path).parts:
        raise HTTPException(status_code=404, detail="Document not found")
    candidate = security.safe_join(docs_base, path)
    if candidate is None or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Document not found")
    raw = candidate.read_bytes()
    truncated = len(raw) > MAX_CONTENT_BYTES
    if truncated:
        raw = raw[:MAX_CONTENT_BYTES]
    rel = candidate.relative_to(docs_base)
    return {
        "path": rel.as_posix(),
        "category": rel.parts[0],
        "filename": candidate.name,
        "size_bytes": len(raw),
        "truncated": truncated,
        "content": raw.decode("utf-8", errors="replace"),
    }
