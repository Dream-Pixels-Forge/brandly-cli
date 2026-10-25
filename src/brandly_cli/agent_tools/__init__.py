"""Built-in tool handlers for the Agnes AI agent loop.

This package splits the former monolithic ``agent_tools.py`` into
concern-based modules:

* :mod:`brandly_cli.agent_tools.project` — project lifecycle
* :mod:`brandly_cli.agent_tools.documents` — bible / screenplay
* :mod:`brandly_cli.agent_tools.media` — image / model catalog
* :mod:`brandly_cli.agent_tools.pre_production` — cast / wardrobe / sheet / location / sound / spatial
* :mod:`brandly_cli.agent_tools.production` — director / cascade / DoP / editor
* :mod:`brandly_cli.agent_tools.pipeline` — produce / stitch / export / gate / timeline / cost

All modules re-export their handlers and ``BUILTIN_TOOLS`` entries here so the
rest of the codebase (``agent_surface``, ``providers``, tests) keeps working
with a single import: ``from brandly_cli.agent_tools import BUILTIN_TOOLS``.

Each tool spec carries a ``skill`` field naming the bundled Agent Skill that
owns that tool's domain (see :data:`SKILL_MAP`).  The manifest builder in
``agent_surface`` surfaces ``skill`` so MCP clients can route calls to the
right skill documentation.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from brandly_cli.agent_tools.documents import BUILTIN_TOOLS as _DOCS_TOOLS
from brandly_cli.agent_tools.documents import (
    _read_bible,
    _read_screenplay,
    _write_bible,
    _write_screenplay,
)
from brandly_cli.agent_tools.media import BUILTIN_TOOLS as _MEDIA_TOOLS
from brandly_cli.agent_tools.media import _generate_image, _list_models
from brandly_cli.agent_tools.pipeline import BUILTIN_TOOLS as _PIPELINE_TOOLS
from brandly_cli.agent_tools.pipeline import (
    _get_timeline,
    _list_jobs,
    _reorder_timeline,
    _run_gate,
    _update_clip,
)
from brandly_cli.agent_tools.pre_production import BUILTIN_TOOLS as _PREPROD_TOOLS
from brandly_cli.agent_tools.pre_production import (
    _animate_cast_15sec,
    _cast_characters,
    _generate_sheet,
    _location_architect,
    _sound_design,
    _spatial_blocking,
    _try_wardrobe,
)
from brandly_cli.agent_tools.production import BUILTIN_TOOLS as _PROD_TOOLS
from brandly_cli.agent_tools.production import (
    _cascade,
    _director,
    _director_of_photography,
    _editor,
)
from brandly_cli.agent_tools.project import BUILTIN_TOOLS as _PROJECT_TOOLS
from brandly_cli.agent_tools.project import _get_project, _list_projects

__all__ = [
    "BUILTIN_TOOLS",
    "SKILL_MAP",
    "SHEET_SKILLS",
    "ToolHandler",
    "_animate_cast_15sec",
    "_cascade",
    "_cast_characters",
    "_director",
    "_director_of_photography",
    "_editor",
    "_generate_image",
    "_generate_sheet",
    "_get_project",
    "_get_timeline",
    "_list_jobs",
    "_list_models",
    "_list_projects",
    "_location_architect",
    "_read_bible",
    "_read_screenplay",
    "_reorder_timeline",
    "_run_gate",
    "_sound_design",
    "_spatial_blocking",
    "_try_wardrobe",
    "_update_clip",
    "_write_bible",
    "_write_screenplay",
    "describe_tools",
    "get_builtin_tools",
    "invoke_tool",
    "is_read_only",
    "skill_for",
]

# ---------------------------------------------------------------------------
# Tool handler type
#
# A handler is a function (sync or async) that takes keyword arguments and
# returns a JSON-serializable value.  ``agent_tool_loop`` will await the
# result if it's a coroutine, and stringify non-strings with ``json.dumps``.
# ---------------------------------------------------------------------------

ToolHandler = Callable[..., Any] | Callable[..., Awaitable[Any]]

# ---------------------------------------------------------------------------
# Aggregated tool registry — every concern's tools merged into one dict.
# ---------------------------------------------------------------------------

BUILTIN_TOOLS: dict[str, dict[str, Any]] = {}
BUILTIN_TOOLS.update(_PROJECT_TOOLS)
BUILTIN_TOOLS.update(_DOCS_TOOLS)
BUILTIN_TOOLS.update(_MEDIA_TOOLS)
BUILTIN_TOOLS.update(_PREPROD_TOOLS)
BUILTIN_TOOLS.update(_PROD_TOOLS)
BUILTIN_TOOLS.update(_PIPELINE_TOOLS)

# ---------------------------------------------------------------------------
# Skill enforcement map — tool name -> owning Agent Skill slug.
#
# Every tool must map to a bundled skill so MCP clients can route to the
# right skill documentation and so auditors can verify no tool is orphaned.
# Utility tools with no dedicated skill map to ``"brandly-init"`` (the
# project bootstrap skill) or ``None`` (pure plumbing).
# ---------------------------------------------------------------------------

SKILL_MAP: dict[str, str | None] = {
    # --- project (brandly-init) ---
    "list_projects": "brandly-init",
    "get_project": "brandly-init",
    "init": "brandly-init",
    "status": "brandly-init",
    "progress": "brandly-init",
    "plan": "brandly-init",
    "estimate": "brandly-init",
    "record_cost": "brandly-init",
    "memory": "brandly-init",
    # --- documents (brandly-production-bible / brandly-screenplay-architect) ---
    "write_bible": "brandly-production-bible",
    "read_bible": "brandly-production-bible",
    "write_screenplay": "brandly-screenplay-architect",
    "read_screenplay": "brandly-screenplay-architect",
    # --- media (brandly-video-generation) ---
    "generate_image": "brandly-video-generation",
    "generate_image_cli": "brandly-video-generation",
    "list_models": None,             # pure catalog utility
    "list_jobs": "brandly-video-generation",
    # --- pre_production ---
    "cast_characters": "brandly-casting",
    "try_wardrobe": "brandly-casting",
    "animate_cast_15sec": "brandly-video-generation",
    "generate_sheet": None,          # dispatches by subject_type — see skill_for()
    "location_architect": "brandly-location-sheet",
    "sound_design": "brandly-audio",          # audio generation (TTS + music)
    "spatial_blocking": "brandly-3d-spatial",
    # --- production ---
    "director": "brandly-film-director",
    "cascade": "brandly-storyboard",
    "fight_choreography": "brandly-storyboard",
    "director_of_photography": "brandly-camera",
    "editor": "dpf-senior-editor",
    # --- pipeline ---
    "produce": "brandly-video-generation",
    "stitch": "dpf-senior-editor",
    "export_platforms": "brandly-film-collaborator",
    "job_poll": "brandly-video-generation",
    "update_clip": "dpf-senior-editor",
    "reorder_timeline": "dpf-senior-editor",
    "get_timeline": "dpf-senior-editor",
    "run_gate": "brandly-film-critic-scorer",
    "approve": "brandly-film-collaborator",
}

#: Subject-type → sheet-skill dispatch for ``generate_sheet``.
SHEET_SKILLS: dict[str, str] = {
    "character": "brandly-character-sheet",
    "location": "brandly-location-sheet",
    "prop": "brandly-object-sheet",
    "object": "brandly-object-sheet",
    "vehicle": "brandly-vehicle-sheet",
    "mecha": "brandly-mecha-sheet",
    "animal": "brandly-animal-sheet",
    "plant": "brandly-plant-sheet",
}


def get_builtin_tools() -> list[tuple[str, ToolHandler, dict[str, Any], str]]:
    """Return the list of (name, handler, json_schema, description) tuples
    expected by ``agent_tool_loop`` in ``agnes_client``."""
    out: list[tuple[str, ToolHandler, dict[str, Any], str]] = []
    for name, spec in BUILTIN_TOOLS.items():
        out.append((name, spec["handler"], spec["schema"], spec["description"]))
    return out


def describe_tools() -> dict[str, Any]:
    """Human-readable summary of the built-in tool set, for CLI help."""
    return {
        name: {
            "description": spec["description"],
            "parameters": spec["schema"],
            "skill": SKILL_MAP.get(name),
            "read_only": name in _READ_ONLY_TOOLS,
        }
        for name, spec in BUILTIN_TOOLS.items()
    }


def invoke_tool(tool_name: str, **kwargs: Any) -> Any:
    """Invoke a named built-in tool with keyword args.

    Returns the raw handler result. Raises ``KeyError`` for unknown tools.
    """
    if tool_name not in BUILTIN_TOOLS:
        raise KeyError(f"Unknown tool: {tool_name}. Available: {list(BUILTIN_TOOLS)}")
    handler = BUILTIN_TOOLS[tool_name]["handler"]
    return handler(**kwargs)


# ---------------------------------------------------------------------------
# Read-only tool set (safe to call unprompted).
# ---------------------------------------------------------------------------

_READ_ONLY_TOOLS: frozenset[str] = frozenset(
    {
        "list_projects",
        "get_project",
        "list_jobs",
        "list_models",
        "get_timeline",
        "run_gate",
        "plan",
        "status",
        "progress",
        "estimate",
        "read_bible",
        "read_screenplay",
    }
)


def is_read_only(name: str) -> bool:
    """Return True if the tool is read-only (safe to call unprompted)."""
    return name in _READ_ONLY_TOOLS


def skill_for(tool_name: str, **params: Any) -> str | None:
    """Return the owning Agent Skill slug for a tool, or None if unowned.

    ``generate_sheet`` dispatches by ``subject_type``: a character sheet is
    owned by ``brandly-character-sheet``, a location sheet by
    ``brandly-location-sheet``, and so on.
    """
    if tool_name == "generate_sheet":
        subject = str(params.get("subject_type") or "").lower()
        if subject in SHEET_SKILLS:
            return SHEET_SKILLS[subject]
    return SKILL_MAP.get(tool_name)
