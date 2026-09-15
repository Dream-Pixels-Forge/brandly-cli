"""Project state manager — CRUD for ``.brandly/{id}/project.json``.

The canonical layout (v0.3.5+) stores each project directly under
``.brandly/{project_id}/`` with eagerly created sub-folders for
``docs/`` (plan, bible, storyboard, tmp), ``refs/``, ``images/``,
``videos/``, ``audio/``.

Projects created by older releases under the legacy
``.brandly/projects/{id}/`` layout are still readable; new writes always
go to the new layout. See :mod:`brandly_cli.layout` for the single source
of truth on paths.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from brandly_cli import layout
from brandly_cli.types import ProjectData
from brandly_cli.utils import read_json, write_json


class ProjectManager:
    """File-based project state manager."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root = Path(root_dir)
        # Legacy base dirs (kept for back-compat reads).
        self.legacy_projects_dir = self.root / ".brandly" / "projects"
        # New layout: .brandly/{id}/ with per-category subfolders.

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _validate_id(self, project_id: str) -> str:
        """Reject path-traversal ids. Returns the safe id verbatim."""
        from brandly_cli.utils import is_valid_project_id

        if not is_valid_project_id(project_id):
            raise ValueError(f"Invalid project ID: {project_id!r}")
        safe_id = Path(project_id).name
        if safe_id != project_id:
            raise ValueError(
                f"Invalid project ID (contains path separators): {project_id}"
            )
        return safe_id

    def _project_path(self, project_id: str) -> Path:
        """Return the canonical (new-layout) ``project.json`` path.

        Writes always target the new layout; reads use
        :meth:`_resolve_project_dir` so legacy trees still resolve.
        """
        return layout.project_dir(self.root, self._validate_id(project_id)) / "project.json"

    def _resolve_project_dir(self, project_id: str) -> Path:
        """Return the dir to *read* from, preferring the new layout."""
        return layout.resolve_project_dir(self.root, self._validate_id(project_id))

    def _new_project_dir(self, project_id: str) -> Path:
        """Return the new-layout project dir (used for writes)."""
        return layout.project_dir(self.root, self._validate_id(project_id))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, data: ProjectData) -> str:
        """Create a new project and persist it. Returns project ID."""
        proj_dir = self._new_project_dir(data.id)
        proj_dir.mkdir(parents=True, exist_ok=True)
        layout.ensure_project_dirs(proj_dir)
        write_json(proj_dir / "project.json", data.to_dict())
        return data.id

    async def read(self, project_id: str) -> ProjectData | None:
        """Load a project by ID, or return None if not found.

        Reads the new layout first; falls back to the legacy
        ``.brandly/projects/{id}/`` tree so older installs keep working.
        """
        path = self._resolve_project_dir(project_id) / "project.json"
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
        # Writes always go to the new layout; legacy files are left in place.
        write_json(self._project_path(project_id), updated.to_dict())
        return updated

    async def delete(self, project_id: str) -> bool:
        """Delete both new-layout and legacy project dirs. Returns True if removed."""
        import shutil

        safe_id = self._validate_id(project_id)
        removed = False
        for d in (
            layout.project_dir(self.root, safe_id),
            layout.legacy_project_dir(self.root, safe_id),
        ):
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
                removed = True
        return removed

    async def list_all(self) -> list[str]:
        """Return list of project IDs across new + legacy layouts."""
        seen: set[str] = set()
        results: list[str] = []
        candidates: list[Path] = []
        new_base = layout.brandly_dir(self.root)
        if new_base.exists():
            for d in new_base.iterdir():
                # Skip legacy 'projects', global files, and dot-folders.
                if d.is_dir() and not d.name.startswith(".") and d.name != "projects":
                    candidates.append(d)
        legacy_base = self.legacy_projects_dir
        if legacy_base.exists():
            for d in legacy_base.iterdir():
                if d.is_dir() and not d.name.startswith("."):
                    candidates.append(d)
        for d in candidates:
            if (d / "project.json").exists() and d.name not in seen:
                seen.add(d.name)
                results.append(d.name)
        return results

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
