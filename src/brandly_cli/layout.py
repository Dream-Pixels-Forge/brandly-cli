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
            images/
                prop/  location/  character/  vehicle/  mecha/  animal/  plant/  general/
                keyframe/ (start/end frame images used for video keyframe mode,
                          e.g. start_frame_kitchen.png, end_frame_exterior_house.png)
                (reference images live in the matching sub-folder —
                 e.g. an object reference goes to images/prop/)
            videos/
                scenes/  insert/  transition/  general/
            audio/
                soundtrack/  sfx/  foley/  voiceover/  general/
            3d-spatial/
                cameras/  keyframes/  depthmaps/  general/
            project.json
            cost.json
            export/
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
    "keyframe",
    "storyboard",
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

#: ``3d-spatial/`` sub-folders, grouped by spatial reference type.
SPATIAL_CATEGORIES: tuple[str, ...] = (
    "cameras",      # Camera position/angle reference frames
    "keyframes",    # First/last frame for animated shots
    "depthmaps",    # Depth map renders from Blender
    "general",      # Other spatial references
)

#: Map a reference ``subject_type`` to the ``images/`` sub-folder where its
#: reference images are stored (all references live under images/).
SUBJECT_TO_IMAGE_CATEGORY: dict[str, str] = {
    "object": "prop",
    "location": "location",
    "character": "character",
    "vehicle": "vehicle",
    "animal": "animal",
    "plant": "plant",
    "mecha": "mecha",
    "keyframe": "keyframe",
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
    """Return the canonical project dir: ``.brandly/{project_id}/``."""
    return brandly_dir(root) / project_id


def resolve_project_dir(root: str | Path, project_id: str) -> Path:
    """Return the canonical project dir: ``.brandly/{project_id}/``."""
    return project_dir(root, project_id)


# ---------------------------------------------------------------------------
# Sub-folder helpers (relative to a resolved project dir)
# ---------------------------------------------------------------------------


def docs_dir(proj_dir: Path, category: str = "tmp") -> Path:
    """Return ``<proj>/docs/{category}`` (unknown category → 'tmp')."""
    return proj_dir / "docs" / _check(category, DOC_CATEGORIES, "tmp")


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


def media_root(proj_dir: str | Path, top: str) -> Path:
    """Return ``<proj>/{images|videos|audio}`` — the un-categorised top folder.

    Use this when a caller scans every category at once (e.g. resolving bare
    reference plate stems across ``images/<category>/``); ``media_dir`` is for
    a single known category.
    """
    if top not in ("images", "videos", "audio"):
        raise ValueError(f"Unknown media top folder: {top!r}")
    return Path(proj_dir) / top


# ---------------------------------------------------------------------------
# v2 layout (issue #43 — .brandly docs | pre-production assets | production
# outputs), enabled by ``brandly migrate`` (or ``brandly init --layout v2``)
# ---------------------------------------------------------------------------

def v2_media_root(root: str | Path, project_id: str, top: str) -> Path:
    """v2 media root: assets live NEXT TO ``.brandly/<project>`` in the
    project workspace, separated by pipeline stage:

    * ``images``  → ``pre-production/<project>/`` (character/, location/,
      prop/, …/storyboard/)
    * ``videos``  → ``production/<project>/videos/``
    * ``audio``   → ``production/<project>/audio/``

    Documents and project state (``project.json``, plans, bibles) stay in
    ``.brandly/<project>/`` — that folder is config, the others are assets.
    """
    base = Path(root)
    if top == "images":
        return base / "pre-production" / project_id
    if top == "videos":
        return base / "production" / project_id / "videos"
    if top == "audio":
        return base / "production" / project_id / "audio"
    raise ValueError(f"Unknown media top folder: {top!r}")


def resolve_media_root(root: str | Path, project_id: str, top: str) -> Path:
    """Return the v2 media root for a project."""
    return v2_media_root(root, project_id, top)


def image_category_for_subject(subject_type: str) -> str:
    """Map a reference subject type to an ``images/`` category."""
    return SUBJECT_TO_IMAGE_CATEGORY.get(subject_type, "general")


def spatial_dir(proj_dir: Path, category: str = "general") -> Path:
    """Return ``<proj>/3d-spatial/{category}`` for spatial reference frames.

    Categories: cameras, keyframes, depthmaps, general.
    These are Blender renders used as composition guides for Agnes.
    """
    return proj_dir / "3d-spatial" / _check(category, SPATIAL_CATEGORIES, "general")


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


def ensure_project_dirs(proj_dir: str | Path) -> None:
    """Create the full sub-folder tree for a project (idempotent)."""
    proj_dir = Path(proj_dir)
    for cat in DOC_CATEGORIES:
        (proj_dir / "docs" / cat).mkdir(parents=True, exist_ok=True)
    for cat in IMAGE_CATEGORIES:
        (proj_dir / "images" / cat).mkdir(parents=True, exist_ok=True)
    for cat in VIDEO_CATEGORIES:
        (proj_dir / "videos" / cat).mkdir(parents=True, exist_ok=True)
    for cat in AUDIO_CATEGORIES:
        (proj_dir / "audio" / cat).mkdir(parents=True, exist_ok=True)
    for cat in SPATIAL_CATEGORIES:
        (proj_dir / "3d-spatial" / cat).mkdir(parents=True, exist_ok=True)
    (proj_dir / "export").mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Media discovery (for auto-detecting references + export scanning)
# ---------------------------------------------------------------------------

_IMAGE_EXTS = ("*.png", "*.jpg", "*.jpeg", "*.webp")


def discover_images(proj_dir: Path) -> list[Path]:
    """Return every image under ``images/`` (all sub-folders, sorted, stable).

    Reference images live in the matching ``images/`` sub-folder, so no
    separate refs tree is scanned.
    """
    found: list[Path] = []
    base = proj_dir / "images"
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


def discover_spatial(proj_dir: str | Path) -> list[Path]:
    """Return every spatial reference under ``3d-spatial/`` (all categories)."""
    proj_dir = Path(proj_dir)
    base = proj_dir / "3d-spatial"
    if not base.exists():
        return []
    found: list[Path] = []
    for ext in _IMAGE_EXTS:
        found.extend(base.rglob(ext))
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in sorted(found):
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique
