"""Project listing and detail routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from brandly_cli import layout
from brandly_cli.project_manager import ProjectManager
from brandly_cli.web.models import ProjectSummary

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=dict)
async def list_projects(request: Request) -> dict:
    """List all projects in .brandly/."""
    root_path = request.app.state.root
    brandly_dir = layout.brandly_dir(root_path)
    if not brandly_dir.exists():
        return {"projects": []}

    projects = []
    for proj_dir in sorted(brandly_dir.iterdir()):
        if not proj_dir.is_dir() or proj_dir.name.startswith("."):
            continue
        proj_json = proj_dir / "project.json"
        if not proj_json.exists():
            continue

        # Check for timeline
        timeline_path = layout.docs_dir(proj_dir, "tmp") / "timeline.json"
        has_timeline = timeline_path.exists()

        # Try to read project metadata
        try:
            import json as _json
            data = _json.loads(proj_json.read_text(encoding="utf-8"))
            summary = ProjectSummary(
                id=data.get("id", proj_dir.name),
                name=data.get("name"),
                slug=data.get("slug"),
                status=data.get("status", "pending"),
                style=data.get("style", "cinematic"),
                shot_count=data.get("shot_count", 0),
                current_phase=data.get("current_phase", "init"),
                has_timeline=has_timeline,
            )
        except Exception:
            summary = ProjectSummary(id=proj_dir.name, has_timeline=has_timeline)
        projects.append(summary)

    return {"projects": projects}


@router.get("/{project_id}", response_model=dict)
async def get_project(project_id: str, request: Request) -> dict:
    """Get project details."""
    root_path = request.app.state.root
    pm = ProjectManager(root_path)
    proj = await pm.read(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    proj_dir = layout.project_dir(root_path, project_id)
    timeline_path = layout.docs_dir(proj_dir, "tmp") / "timeline.json"

    return {
        "id": proj.id,
        "name": proj.name,
        "slug": proj.slug,
        "status": proj.status,
        "style": proj.style,
        "shot_count": proj.shot_count,
        "budget": proj.budget,
        "spent": proj.spent,
        "current_phase": proj.current_phase,
        "description": proj.description,
        "target_platforms": getattr(proj, "target_platforms", []),
        "created_at": proj.created_at,
        "updated_at": proj.updated_at,
        "has_timeline": timeline_path.exists(),
    }
