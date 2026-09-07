"""Project state manager — CRUD for .brandly/projects/{id}/project.json."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from brandly_cli.types import ProjectData
from brandly_cli.utils import read_json, write_json


class ProjectManager:
    """File-based project state manager."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root = Path(root_dir)
        self.projects_dir = self.root / ".brandly" / "projects"
        self.images_dir = self.root / ".brandly" / "images"
        self.artifacts_dir = self.root / ".brandly" / "artifacts"

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _project_path(self, project_id: str) -> Path:
        # Guard against path traversal attacks
        from brandly_cli.utils import is_valid_project_id

        if not is_valid_project_id(project_id):
            raise ValueError(f"Invalid project ID: {project_id!r}")
        safe_id = Path(project_id).name
        if safe_id != project_id:
            raise ValueError(f"Invalid project ID (contains path separators): {project_id}")
        return self.projects_dir / safe_id / "project.json"

    def _project_dir(self, project_id: str) -> Path:
        from brandly_cli.utils import is_valid_project_id

        if not is_valid_project_id(project_id):
            raise ValueError(f"Invalid project ID: {project_id!r}")
        safe_id = Path(project_id).name
        if safe_id != project_id:
            raise ValueError(f"Invalid project ID (contains path separators): {project_id}")
        return self.projects_dir / safe_id

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, data: ProjectData) -> str:
        """Create a new project and persist it. Returns project ID."""
        project_dir = self._project_dir(data.id)
        project_dir.mkdir(parents=True, exist_ok=True)
        # Create artifact subdirectories eagerly to avoid empty dirs
        for subdir in ("images", "videos", "audio", "docs"):
            (project_dir / "artifacts" / subdir).mkdir(parents=True, exist_ok=True)
        write_json(self._project_path(data.id), data.to_dict())
        return data.id

    async def read(self, project_id: str) -> ProjectData | None:
        """Load a project by ID, or return None if not found."""
        path = self._project_path(project_id)
        if not path.exists():
            return None
        raw = read_json(path)
        return ProjectData.model_validate(raw)

    async def update(self, project_id: str, updates: dict[str, Any]) -> ProjectData | None:
        """Partially update a project in-place.

        If the project does not exist yet, it is auto-created with ``project_id``
        as the ID and the supplied ``updates`` as the initial state. This
        allows callers like ``brandly record-cost`` or ``brandly reference``
        to update state without first requiring a separate ``brandly init`` step.

        For declared fields, setattr is used. For extra fields (allowed by
        ``model_config = {"extra": "allow"}``), the data is re-validated via
        ``model_validate`` so the model can hold the new extras correctly.
        """
        proj = await self.read(project_id)
        if proj is None:
            # Auto-create with the updates as initial state
            initial: dict[str, Any] = {"id": project_id}
            initial.update(updates)
            initial.setdefault("created_at", _now_iso())
            initial["updated_at"] = _now_iso()
            new_proj = ProjectData.model_validate(initial)
            await self.create(new_proj)
            return new_proj
        merged = proj.to_dict()
        for key, value in updates.items():
            merged[key] = value
        merged["updated_at"] = _now_iso()
        updated = ProjectData.model_validate(merged)
        write_json(self._project_path(project_id), updated.to_dict())
        return updated

    async def delete(self, project_id: str) -> bool:
        """Delete a project directory. Returns True if removed."""
        import shutil

        proj_dir = self._project_dir(project_id)
        if proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)
            return True
        return False

    async def list_all(self) -> list[str]:
        """Return list of project IDs."""
        if not self.projects_dir.exists():
            return []
        return [
            d.name
            for d in self.projects_dir.iterdir()
            if d.is_dir() and (d / "project.json").exists()
        ]

    async def list_with_status(self) -> list[dict[str, Any]]:
        """Return summary info for all projects."""
        ids = await self.list_all()
        results = []
        for pid in ids:
            proj = await self.read(pid)
            if proj:
                results.append(
                    {
                        "id": proj.id,
                        "slug": proj.slug,
                        "name": proj.name,
                        "status": proj.status,
                        "current_phase": proj.current_phase,
                        "budget": proj.budget,
                        "spent": proj.spent,
                        "remaining": proj.budget - proj.spent,
                        "updated_at": proj.updated_at,
                    }
                )
        return results


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
