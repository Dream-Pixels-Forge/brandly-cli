"""Project folder restructure — legacy layout to v2 (issue #43).

The legacy layout keeps everything under ``.brandly/<project>/``; the v2
layout separates the three concerns named in the issue:

* **Documents / config** stay in ``.brandly/<project>/`` (plans, bibles,
  ``project.json``, cost tracking) — it is the project's config.
* **Pre-production assets** (character / location / prop reference plates
  and generated storyboards) move to ``pre-production/<project>/``.
* **Production outputs** (scene clips, transitions, inserts, audio,
  assembly) move to ``production/<project>/``.

``brandly migrate`` is move-only: no files are copied or deleted in place.
Every move is previewed (dry-run is the default); ``--apply`` executes and
stamps ``layout_version: 2`` on ``project.json`` so all layout-aware
callers (``layout.resolve_media_root``) resolve the new roots.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from brandly_cli import layout

#: ``.brandly/<p>/images/<cat>`` → ``pre-production/<p>/<cat>``
_IMAGE_TO_PREPRODUCTION = True

#: legacy ``videos/<cat>`` → v2 ``production/<p>/videos/<cat>`` with the
#: issue's folder names (transition → transitions, insert → inserts).
_VIDEO_CATEGORY_RENAME: dict[str, str] = {
    "transition": "transitions",
    "insert": "inserts",
}

AUDIO_TOP = "audio"


def _top_dest(root: Path, project_id: str, top: str, category: str) -> Path:
    if top == "images":
        return root / "pre-production" / project_id / category
    if top == "videos":
        return (
            root
            / "production"
            / project_id
            / "videos"
            / _VIDEO_CATEGORY_RENAME.get(category, category)
        )
    return root / "production" / project_id / AUDIO_TOP / category


@dataclass
class MigrationPlan:
    """One concrete file/dir move (source, destination)."""

    source: Path
    dest: Path


@dataclass
class MigrationResult:
    moves: list[MigrationPlan] = field(default_factory=list)
    skipped: list[MigrationPlan] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.skipped


def plan_migration(root: str | Path, project_id: str) -> list[MigrationPlan]:
    """Compute the move list for a project (no side effects).

    Empty-category folders are not moved (a fresh v2 skeleton recreates
    them); only non-empty media folders become moves, and when the v2
    destination already exists each source entry is merged into it.
    """
    root = Path(root)
    proj = layout.project_dir(root, project_id)
    if not proj.is_dir():
        return []
    plans: list[MigrationPlan] = []
    for top in ("images", "videos", "audio"):
        base = layout.media_root(proj, top)
        if not base.is_dir():
            continue
        for category_dir in sorted(base.iterdir()):
            if not category_dir.is_dir():
                continue
            has_content = any(category_dir.iterdir())
            if not has_content:
                continue
            dest = _top_dest(root, project_id, top, category_dir.name)
            plans.append(MigrationPlan(source=category_dir, dest=dest))
    return plans


def apply_migration(root: str | Path, project_id: str, apply: bool = False) -> MigrationResult:
    """Execute the migration.

    Without ``apply`` this is a dry run: the plan is computed and returned
    with every entry in ``moves``. With ``apply`` each move is performed
    (folders merge into an existing destination) and
    ``project.json`` is stamped with ``layout_version: 2``.
    """
    root = Path(root)
    plans = plan_migration(root, project_id)
    result = MigrationResult(moves=plans)
    if not apply:
        return result
    import shutil

    for plan in plans:
        target = plan.dest
        if target.is_dir():
            # Merge: move the source folder into the existing destination.
            target = target / plan.source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            result.skipped.append(plan)
            continue
        shutil.move(str(plan.source), str(target))
        # A now-empty legacy media root is removed when nothing is left in it.
    _stamp_v2(root, project_id)
    # Prune legacy media roots that lost all content.
    proj = layout.project_dir(root, project_id)
    for top in ("images", "videos", "audio"):
        base = layout.media_root(proj, top)
        if base.is_dir() and not any(base.iterdir()):
            base.rmdir()
    return result


def _stamp_v2(root: Path, project_id: str) -> None:
    """Record ``layout_version: 2`` in ``project.json`` (or create it)."""
    proj_json = layout.project_dir(root, project_id) / "project.json"
    data: dict = {}
    if proj_json.is_file():
        try:
            data = json.loads(proj_json.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["layout_version"] = 2
    proj_json.parent.mkdir(parents=True, exist_ok=True)
    proj_json.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_v2_skeleton(root: str | Path, project_id: str) -> None:
    """Create empty v2 category folders (used by ``brandly init --layout v2``)."""
    root = Path(root)
    for top in ("images", "videos", "audio"):
        for category in layout.ALL_MEDIA_CATEGORIES:
            if top == "images" and category not in layout.IMAGE_CATEGORIES:
                continue
            if top == "videos" and category not in layout.VIDEO_CATEGORIES:
                continue
            if top == "audio" and category not in layout.AUDIO_CATEGORIES:
                continue
            _top_dest(root, project_id, top, category).mkdir(parents=True, exist_ok=True)
    _stamp_v2(root, project_id)
