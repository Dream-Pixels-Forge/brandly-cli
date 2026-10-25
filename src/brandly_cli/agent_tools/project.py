"""Project lifecycle tools — init, status, progress, plan, estimate,
record_cost, memory, list_projects, get_project.

Owned by the ``brandly-init`` skill (project bootstrap & orchestration).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from brandly_cli.async_compat import run_async

# ---------------------------------------------------------------------------
# Tool: list_projects
# ---------------------------------------------------------------------------

def _list_projects(
    status: str | None = None,
    limit: int = 20,
    root: str | None = None,
) -> dict[str, Any]:
    """List brandly projects on disk, optionally filtered by status."""
    try:
        from brandly_cli.project_manager import ProjectManager

        pm = ProjectManager(Path(root or "."))
        projects = run_async(pm.list_with_status())
        if status:
            projects = [p for p in projects if p.get("status") == status]
        projects = projects[:limit]
        return {
            "count": len(projects),
            "projects": [
                {
                    "id": p.get("id", ""),
                    "name": p.get("name", ""),
                    "status": p.get("status", ""),
                    "updated_at": p.get("updated_at", ""),
                }
                for p in projects
            ],
        }
    except Exception as e:  # pragma: no cover - safety net
        return {"error": f"list_projects: {e}"}


# ---------------------------------------------------------------------------
# Tool: get_project
# ---------------------------------------------------------------------------

def _get_project(project_id: str, root: str | None = None) -> dict[str, Any]:
    """Fetch a single project by ID from the project manager."""
    try:
        from brandly_cli.project_manager import ProjectManager

        pm = ProjectManager(Path(root or "."))
        data = run_async(pm.read(project_id))
        if not data:
            return {"error": f"project {project_id} not found"}
        model_dump = getattr(data, "model_dump", None)
        return model_dump() if callable(model_dump) else {"id": project_id}
    except Exception as e:
        return {"error": f"get_project: {e}"}


# ---------------------------------------------------------------------------
# Tool registry — project domain
# ---------------------------------------------------------------------------

BUILTIN_TOOLS: dict[str, dict[str, Any]] = {
    "list_projects": {
        "handler": _list_projects,
        "schema": {
            "type": "object",
            "title": "List Projects",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "running", "completed", "failed", "paused", "cancelled"],
                    "description": "Optional status filter.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20,
                    "description": "Max projects to return.",
                },
                "root": {
                    "type": "string",
                    "description": "Project root directory (defaults to cwd).",
                },
            },
        },
        "description": "List brandly projects on disk, optionally filtered by status.",
    },
    "get_project": {
        "handler": _get_project,
        "schema": {
            "type": "object",
            "title": "Get Project",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "UUID or slug of the project to fetch.",
                },
                "root": {
                    "type": "string",
                    "description": "Project root directory.",
                },
            },
            "required": ["project_id"],
        },
        "description": "Fetch a single project by ID, including phases and cost tracking.",
    },
}
