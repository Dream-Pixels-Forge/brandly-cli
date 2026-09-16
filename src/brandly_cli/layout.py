"""Central definition of the ``.brandly`` on-disk folder layout.

This module is the **single source of truth** for every path brandly-cli
creates under ``.brandly/``. All other modules (``project_manager``,
``cost_tracker``, ``cli``, ``utils``) import from here so the layout is
defined in exactly one place and stays consistent.

Layout — one folder per project, keyed by the readable project id (slug):

.. code-block:: text

    .brandly/
        {project}/
            docs/
                plan/        pre-generation plans
                bible/       production bibles
                storyboard/  storyboards / shot lists
                tmp/         transient working docs (gen records, fail docs)
            refs/            primary reference images (identity locking)
            images/
                prop/  location/  character/  vehicle/  mecha/  animal/  plant/  general/
            videos/
                scenes/  insert/  transition/  general/
            audio/
                soundtrack/  sfx/  foley/  voiceover/  general/
            project.json
            cost.json
            export/

Back-compat: existing trees stored under the legacy
``.brandly/projects/{id}/`` layout are still readable via
:func:`resolve_project_dir`; new projects are always created in the
top-level ``.brandly/{id}/`` layout.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Category taxonomy (created eagerly so the tree is always fully navigable)
# ---------------------------------------------------------------------------

#: ``docs/`` sub-folders. All documents live here, never duplicated.
DOC_CATEGORIES: tuple[str, ...] = ("plan", "bible", "storyboard", "tmp")

#: ``images/`` sub-folders, grouped by subject category.
IMAGE_CATEGORIES: tuple[str, ...] = (
    "prop",
    "location",
    "character",
    "vehicle",
    "mecha",
    "animal",
    "plant",
    "general",
)

#: ``videos/`` sub-folders, grouped by shot role.
VIDEO_CATEGORIES: tuple[str, ...] = ("scenes", "insert", "transition", "general")

#: ``audio/`` sub-folders, grouped by content type.
AUDIO_CATEGORIES: tuple[str, ...] = (
    "soundtrack",
    "sfx",
    "foley",
    "voiceover",
    "general",
)

#: Map a reference ``subject_type`` to an ``images/`` category.
SUBJECT_TO_IMAGE_CATEGORY: dict[str, str] = {
    "object": "prop",
    "location": "location",
    "character": "character",
    "vehicle": "vehicle",
    "animal": "animal",
    "plant": "plant",
    "mecha": "mecha",
}

#: Every category across all media folders, for eager creation.
ALL_MEDIA_CATEGORIES: tuple[str, ...] = (
    IMAGE_CATEGORIES + VIDEO_CATEGORIES + AUDIO_CATEGORIES
)


def _check(category: str, allowed: tuple[str, ...], default: str = "general") -> str:
    """Return ``category`` if it is in ``allowed`` else ``default``."""
    return category if category in allowed else default


# ---------------------------------------------------------------------------
# Top-level paths
# ---------------------------------------------------------------------------


def brandly_dir(root: str | Path) -> Path:
    """Return ``<root>/.brandly``."""
    return Path(root) / ".brandly"


def project_dir(root: str | Path, project_id: str) -> Path:
    """Return the **new** canonical project dir: ``.brandly/{project_id}/``."""
    return brandly_dir(root) / project_id


def legacy_project_dir(root: str | Path, project_id: str) -> Path:
    """Return the **legacy** project dir: ``.brandly/projects/{project_id}/``."""
    return brandly_dir(root) / "projects" / project_id


def resolve_project_dir(root: str | Path, project_id: str) -> Path:
    """Return the project dir to *read* from, preferring the new layout.

    Order: new ``.brandly/{id}/`` (if it holds a ``project.json``) →
    legacy ``.brandly/projects/{id}/`` (if it holds a ``project.json``) →
    new dir (created on demand).
    """
    new_dir = project_dir(root, project_id)
    if (new_dir / "project.json").exists():
        return new_dir
    legacy_dir = legacy_project_dir(root, project_id)
    if (legacy_dir / "project.json").exists():
        return legacy_dir
    return new_dir


# ---------------------------------------------------------------------------
# Sub-folder helpers (relative to a resolved project dir)
# ---------------------------------------------------------------------------


def docs_dir(proj_dir: Path, category: str = "tmp") -> Path:
    """Return ``<proj>/docs/{category}`` (unknown category → 'tmp')."""
    return proj_dir / "docs" / _check(category, DOC_CATEGORIES, "tmp")


def refs_dir(proj_dir: Path) -> Path:
    """Return ``<proj>/refs/`` for primary reference images."""
    return proj_dir / "refs"


def media_dir(proj_dir: Path, top: str, category: str = "general") -> Path:
    """Return ``<proj>/{images|videos|audio}/{category}``.

    ``top`` is one of ``images`` / ``videos`` / ``audio``; ``category`` is
    coerced into the known set for that top folder (unknown → 'general').
    """
    if top == "images":
        allowed, default = IMAGE_CATEGORIES, "general"
    elif top == "videos":
        allowed, default = VIDEO_CATEGORIES, "general"
    elif top == "audio":
        allowed, default = AUDIO_CATEGORIES, "general"
    else:
        raise ValueError(f"Unknown media top folder: {top!r}")
    return proj_dir / top / _check(category, allowed, default)


def image_category_for_subject(subject_type: str) -> str:
    """Map a reference subject type to an ``images/`` category."""
    return SUBJECT_TO_IMAGE_CATEGORY.get(subject_type, "general")


# ---------------------------------------------------------------------------
# Generated-image naming convention
#
# Sheet images are named by a type prefix + a slug of the subject:
#   character sheet -> char_<name>_<ts>.png
#   location sheet  -> loc_<name>_<ts>.png
#   object/prop     -> prop_<name>_<ts>.png
# Other subject types keep a readable ``<subject_type>_`` prefix.
# ---------------------------------------------------------------------------

#: Prefix used for the three primary sheet types.
IMAGE_NAME_PREFIXES: dict[str, str] = {
    "character": "char",
    "location": "loc",
    "object": "prop",
    "prop": "prop",
}


def image_name_prefix(subject_type: str | None) -> str | None:
    """Return the filename prefix for a subject type.

    'character' -> 'char', 'location' -> 'loc', 'object'/'prop' -> 'prop'.
    Unknown types fall back to the lowercased subject type itself; empty -> None.
    """
    if not subject_type:
        return None
    key = subject_type.lower()
    if key in IMAGE_NAME_PREFIXES:
        return IMAGE_NAME_PREFIXES[key]
    return key or None


def image_name_token(name: str, max_len: int = 40) -> str:
    """Slug a subject/sheet name into a filesystem-safe token."""
    import re

    token = name.strip().lower()
    token = re.sub(r"[\s\-]+", "_", token)
    token = re.sub(r"[^a-z0-9_]", "", token)
    token = re.sub(r"_+", "_", token).strip("_")
    return token[:max_len] or "image"


def build_sheet_filename(
    subject_type: str | None,
    name: str,
    timestamp: str,
    ext: str = ".png",
) -> str:
    """Build a conventional sheet-image filename.

    e.g. ('character', 'Maya', '2026-01-01_000000') -> 'char_maya_2026-01-01_000000.png'
    """
    prefix = image_name_prefix(subject_type)
    token = image_name_token(name)
    if prefix:
        return f"{prefix}_{token}_{timestamp}{ext}"
    return f"{token}_{timestamp}{ext}"


def ensure_project_dirs(proj_dir: Path) -> None:
    """Create the full sub-folder tree for a project (idempotent)."""
    for cat in DOC_CATEGORIES:
        (proj_dir / "docs" / cat).mkdir(parents=True, exist_ok=True)
    refs_dir(proj_dir).mkdir(parents=True, exist_ok=True)
    for cat in IMAGE_CATEGORIES:
        (proj_dir / "images" / cat).mkdir(parents=True, exist_ok=True)
    for cat in VIDEO_CATEGORIES:
        (proj_dir / "videos" / cat).mkdir(parents=True, exist_ok=True)
    for cat in AUDIO_CATEGORIES:
        (proj_dir / "audio" / cat).mkdir(parents=True, exist_ok=True)
    (proj_dir / "export").mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Media discovery (for auto-detecting references + export scanning)
# ---------------------------------------------------------------------------

_IMAGE_EXTS = ("*.png", "*.jpg", "*.jpeg", "*.webp")


def discover_images(proj_dir: Path) -> list[Path]:
    """Return every image under ``refs/`` and ``images/`` (sorted, stable)."""
    found: list[Path] = []
    for base in (refs_dir(proj_dir), proj_dir / "images"):
        if base.exists():
            for ext in _IMAGE_EXTS:
                found.extend(base.rglob(ext))
    # Stable, de-duplicated ordering.
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in sorted(found):
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def discover_docs(proj_dir: Path) -> list[Path]:
    """Return every document under ``docs/`` (all categories)."""
    base = proj_dir / "docs"
    if not base.exists():
        return []
    files: list[Path] = []
    for p in sorted(base.rglob("*")):
        if p.is_file():
            files.append(p)
    return files
