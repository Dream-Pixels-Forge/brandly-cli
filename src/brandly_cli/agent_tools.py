"""Built-in tool handlers for the Agnes AI agent loop.

Each tool is a Python callable that takes only JSON-serializable arguments
and returns a JSON-serializable result. The tool *descriptor* (name + JSON
schema) is exposed to the Agnes model via the OpenAI-compatible
``tools`` field, and this module provides the handler that actually
executes it on the client side.

Tools are intentionally small and read-only: they mirror the state the
brandly CLI already exposes (project data, Agnes jobs, model catalog)
so an agent can answer questions like "which projects have failed
videos?" without any new user input.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# Tool handler type
#
# A handler is a function (sync or async) that takes keyword arguments and
# returns a JSON-serializable value.  ``agent_tool_loop`` will await the
# result if it's a coroutine, and stringify non-strings with ``json.dumps``.
# ---------------------------------------------------------------------------

ToolHandler = Callable[..., Any] | Callable[..., Awaitable[Any]]


# ---------------------------------------------------------------------------
# Tool: list_projects
# ---------------------------------------------------------------------------

def _list_projects(
    status: str | None = None,
    limit: int = 20,
    root: str | None = None,
) -> dict[str, Any]:
    """List brandly projects on disk, optionally filtered by status."""
    import asyncio

    try:
        from brandly_cli.project_manager import ProjectManager

        pm = ProjectManager(Path(root or "."))
        projects = asyncio.run(pm.list_with_status())
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
    import asyncio

    try:
        from brandly_cli.project_manager import ProjectManager

        pm = ProjectManager(Path(root or "."))
        data = asyncio.run(pm.read(project_id))
        if not data:
            return {"error": f"project {project_id} not found"}
        model_dump = getattr(data, "model_dump", None)
        return model_dump() if callable(model_dump) else {"id": project_id}
    except Exception as e:
        return {"error": f"get_project: {e}"}


# ---------------------------------------------------------------------------
# Tool: list_jobs (Agnes video jobs)
# ---------------------------------------------------------------------------

def _list_jobs(
    status: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """List recent Agnes video-generation jobs (read-only)."""
    import asyncio

    try:
        from brandly_cli.agnes_client import list_jobs

        return {"jobs": asyncio.run(list_jobs(status=status, limit=limit))}
    except Exception as e:
        return {"error": f"list_jobs: {e}"}


# ---------------------------------------------------------------------------
# Tool: generate_image
# ---------------------------------------------------------------------------

def _generate_image(
    prompt: str,
    model: str = "agnes-image-2.5-flash",
    size: str = "2K",
    ratio: str = "16:9",
) -> dict[str, Any]:
    """Generate a single Agnes image.  Synchronous wrapper over async."""
    import asyncio

    try:
        from brandly_cli.agnes_client import generate_image

        return asyncio.run(
            generate_image(prompt, model=model, size=size, ratio=ratio)
        )
    except Exception as e:
        return {"error": f"generate_image: {e}"}


# ---------------------------------------------------------------------------
# Tool: list_models
# ---------------------------------------------------------------------------

def _list_models(category: str | None = None) -> dict[str, Any]:
    """List available model IDs across image / video / audio / text."""
    try:
        from brandly_cli.constants import get_all_models

        all_models = get_all_models()
        if category and category in all_models:
            return {"category": category, "models": all_models[category]}
        return all_models
    except Exception as e:
        return {"error": f"list_models: {e}"}


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

BUILTIN_TOOLS: dict[str, dict[str, Any]] = {
    "list_projects": {
        "handler": _list_projects,
        "schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": (
                        "Optional status filter (e.g. pending, running, failed)."
                    ) ,
                },
                "limit": {
                    "type": "integer",
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
    "list_jobs": {
        "handler": _list_jobs,
        "schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Optional status filter.",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                },
            },
        },
        "description": "List recent Agnes video-generation jobs (read-only).",
    },
    "generate_image": {
        "handler": _generate_image,
        "schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Text description of the image to generate.",
                },
                "model": {
                    "type": "string",
                    "default": "agnes-image-2.5-flash",
                    "description": "Agnes image model ID.",
                },
                "size": {
                    "type": "string",
                    "default": "2K",
                    "description": "Image size tier (1K/2K/3K/4K).",
                },
                "ratio": {
                    "type": "string",
                    "default": "16:9",
                    "description": "Aspect ratio (16:9, 9:16, 1:1, 4:3, 4:5).",
                },
            },
            "required": ["prompt"],
        },
        "description": "Generate a single Agnes image from a text prompt.",
    },
    "list_models": {
        "handler": _list_models,
        "schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["image", "video", "audio"],
                    "description": "Optional category filter.",
                },
            },
        },
        "description": "List available model IDs and metadata across image/video/audio.",
    },
}


def get_builtin_tools() -> list[tuple[str, ToolHandler, dict[str, Any], str]]:
    """Return the list of (name, handler, json_schema, description) tuples
    expected by ``agent_tool_loop`` in ``agnes_client``.

    The OpenAI-compatible ``tools`` payload requires:
        {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}
    so each entry is pre-shaped to drop in as-is.
    """
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
        }
        for name, spec in BUILTIN_TOOLS.items()
    }


def invoke_tool(name: str, **kwargs: Any) -> Any:
    """Invoke a named built-in tool with keyword args.

    Returns the raw handler result (dict, list, str, …). Callers in
    ``agent_tool_loop`` will JSON-stringify non-string results.
    """
    if name not in BUILTIN_TOOLS:
        raise KeyError(f"Unknown tool: {name}. Available: {list(BUILTIN_TOOLS)}")
    handler = BUILTIN_TOOLS[name]["handler"]
    return handler(**kwargs)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def to_json(value: Any) -> str:
    """Stringify a tool result for feeding back to the LLM."""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)
