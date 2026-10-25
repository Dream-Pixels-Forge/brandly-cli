"""The single, agent-callable tool surface for brandly-cli (Goal 1).

Why this module exists
----------------------
`agent_tools` exposes handlers to the *Agnes* model loop only, and there was no
machine-readable way for an external agent (opencode, Claude Code, Codex, pi) to
discover or call brandly at all — so agents invented their own ffmpeg/HTTP tools
and bypassed the pipeline (audit F1/F2).

This module is the one dispatch layer:

* ``tool_manifest()`` — the discoverable capability set (name, description,
  JSON-Schema parameters, read-only class, backing command).
* ``build_command()`` — pure mapping from a tool call to real CLI argv, so the
  tool surface IS the CLI surface (no parallel implementation).
* ``dispatch()`` — executes a call: library tools run the existing
  ``agent_tools`` handlers in-process; pipeline tools run the real CLI command
  through an injectable runner (subprocess by default).

Nothing here re-implements pipeline logic; adding a tool means mapping a command
that already exists.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from brandly_cli import agent_tools
from brandly_cli.io import run_capture

# (exit_code, stdout, stderr)
ToolRunner = Callable[[list[str]], tuple[int, str, str]]

MANIFEST_VERSION = 1

#: Read-only tools — delegated to the agent_tools package which owns the set.
READ_ONLY_TOOLS = agent_tools.is_read_only

#: Skill enforcement map — tool name -> owning Agent Skill slug.
SKILL_MAP = agent_tools.SKILL_MAP

#: MCP annotations per tool domain — signals to clients about side effects.
TOOL_ANNOTATIONS: dict[str, dict[str, Any]] = {
    # Read-only / project discovery
    "list_projects":      {"readOnlyHint": True,  "destructiveHint": False, "idempotentHint": True},
    "get_project":        {"readOnlyHint": True,  "destructiveHint": False, "idempotentHint": True},
    "list_jobs":          {"readOnlyHint": True,  "destructiveHint": False, "idempotentHint": True},
    "list_models":        {"readOnlyHint": True,  "destructiveHint": False, "idempotentHint": True},
    "get_timeline":       {"readOnlyHint": True,  "destructiveHint": False, "idempotentHint": True},
    "run_gate":           {"readOnlyHint": True,  "destructiveHint": False, "idempotentHint": True},
    "plan":               {"readOnlyHint": True,  "destructiveHint": False, "idempotentHint": True},
    "status":             {"readOnlyHint": True,  "destructiveHint": False, "idempotentHint": True},
    "progress":           {"readOnlyHint": True,  "destructiveHint": False, "idempotentHint": True},
    "estimate":           {"readOnlyHint": True,  "destructiveHint": False, "idempotentHint": True},
    "read_bible":         {"readOnlyHint": True,  "destructiveHint": False, "idempotentHint": True},
    "read_screenplay":    {"readOnlyHint": True,  "destructiveHint": False, "idempotentHint": True},
    # .brandly documents — write (create foundation artifacts)
    "write_bible":        {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "write_screenplay":   {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    # Generation / media (spend credits, create resources)
    "generate_image":     {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "generate_image_cli": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    # Pre-production (spend credits, create reference assets)
    "cast_characters":    {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "try_wardrobe":       {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "animate_cast_15sec": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "generate_sheet":     {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "location_architect": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "sound_design":       {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "spatial_blocking":   {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    # Pipeline / write (spend credits, mutate state)
    "produce":            {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "stitch":             {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "export_platforms":   {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "job_poll":           {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "init":               {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "approve":            {"readOnlyHint": False, "destructiveHint": True,  "idempotentHint": False},
    "record_cost":        {"readOnlyHint": False, "destructiveHint": True,  "idempotentHint": False},
    "memory":             {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "update_clip":        {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "reorder_timeline":   {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    # Production (spend credits, create production assets)
    "director":           {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "cascade":            {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "fight_choreography": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "director_of_photography": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
    "editor":             {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False},
}


def python_executable() -> str:
    """Interpreter used to invoke the CLI in a subprocess (patched in tests)."""
    return sys.executable


# ---------------------------------------------------------------------------
# Pure command builders (one per pipeline tool)
# ---------------------------------------------------------------------------


def _require(args: dict[str, Any], key: str) -> Any:
    if key not in args or args[key] in (None, "", [], ()):
        raise ValueError(f"missing required argument: {key}")
    return args[key]


def _opt(args: dict[str, Any], key: str, flag: str) -> list[str]:
    value = args.get(key)
    return [flag, str(value)] if value is not None else []


def _flag(args: dict[str, Any], key: str, flag: str) -> list[str]:
    return [flag] if args.get(key) else []


def _build_produce(args: dict[str, Any]) -> list[str]:
    argv = ["produce", str(_require(args, "project_id")), "--shots", str(_require(args, "shots"))]
    argv += _opt(args, "interval", "--interval")
    argv += _opt(args, "character", "--character")
    argv += _flag(args, "no_auto_refs", "--no-auto-refs")
    argv += _flag(args, "allow_referenceless", "--allow-referenceless")
    return argv


def _build_plan(args: dict[str, Any]) -> list[str]:
    argv = ["plan", str(_require(args, "project_id"))]
    argv += _flag(args, "json", "--json")
    return argv


def _build_stitch(args: dict[str, Any]) -> list[str]:
    clips = [str(c) for c in _require(args, "clips")]
    argv = ["stitch", *clips, "--output", str(_require(args, "output"))]
    argv += _opt(args, "transition", "--transition")
    argv += _opt(args, "transition_duration", "--transition-duration")
    argv += _opt(args, "color_grade", "--color-grade")
    return argv


def _build_export_platforms(args: dict[str, Any]) -> list[str]:
    argv = ["export-platforms", str(_require(args, "project_id"))]
    for platform in args.get("platforms") or []:
        argv += ["--platforms", str(platform)]
    argv += _opt(args, "output", "--output")
    return argv


def _build_job_poll(args: dict[str, Any]) -> list[str]:
    # --json is not optional: the tool must return a machine-readable status.
    argv = ["job-poll", str(_require(args, "job_id")), "--json"]
    argv += _opt(args, "max_age", "--max-age")
    argv += _opt(args, "output", "--output")
    return argv


def _build_init(args: dict[str, Any]) -> list[str]:
    """P5 (#256): map a project-init tool call to `brandly init` argv."""
    argv = ["init"]
    if args.get("name"):
        argv += ["--name", str(args["name"])]
    if args.get("idea"):
        argv += ["--idea", str(args["idea"])]
    if args.get("style"):
        argv += ["--style", str(args["style"])]
    if args.get("budget") is not None:
        argv += ["--budget", str(args["budget"])]
    if args.get("shots") is not None:
        argv += ["--shots", str(args["shots"])]
    return argv


def _build_status(args: dict[str, Any]) -> list[str]:
    """P5 (#256): map a status tool call to `brandly status <project_id>`."""
    return ["status", _require(args, "project_id")]


def _build_progress(args: dict[str, Any]) -> list[str]:
    """P5 (#256): map a progress tool call to `brandly progress <project_id>`."""
    return ["progress", _require(args, "project_id")]


def _build_approve(args: dict[str, Any]) -> list[str]:
    """P5 (#256): map an approve tool call to `brandly approve <id> <phase>`."""
    return ["approve", _require(args, "project_id"), _require(args, "phase")]


def _build_estimate(args: dict[str, Any]) -> list[str]:
    """P5 (#256): map an estimate tool call to `brandly estimate` argv."""
    argv = ["estimate"]
    if args.get("style"):
        argv += ["--style", str(args["style"])]
    if args.get("shots") is not None:
        argv += ["--shots", str(args["shots"])]
    if args.get("target_duration") is not None:
        argv += ["--target-duration", str(args["target_duration"])]
    return argv


def _build_record_cost(args: dict[str, Any]) -> list[str]:
    """P5 (#256): map a record-cost tool call to `brandly record-cost` argv."""
    return [
        "record-cost",
        _require(args, "project_id"),
        _require(args, "phase"),
        _require(args, "action"),
        str(_require(args, "credits")),
    ]


def _build_memory(args: dict[str, Any]) -> list[str]:
    """P5 (#256): map a memory tool call to `brandly memory <action> [hook]`."""
    argv = ["memory", _require(args, "action")]
    if args.get("hook"):
        argv.append(str(args["hook"]))
    return argv


def _build_image(args: dict[str, Any]) -> list[str]:
    argv = ["image", "--prompt", str(_require(args, "prompt")), "--json"]
    argv += _opt(args, "model", "--model")
    argv += _opt(args, "size", "--size")
    argv += _opt(args, "ratio", "--ratio")
    argv += _opt(args, "output", "--output")
    argv += _opt(args, "project_id", "--project-id")
    return argv


# ---------------------------------------------------------------------------
# CLI-backed tool table (name -> command, schema, builder)
# ---------------------------------------------------------------------------

CLI_TOOLS: dict[str, dict[str, Any]] = {
    "produce": {
        "command": "produce",
        "builder": _build_produce,
        "description": (
            "Generate a multi-shot film shot by shot from a shot list (the real "
            "production path: scene naming, references, retries, production plan)."
        ),
        "parameters": {
            "type": "object",
            "title": "Produce",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "shots": {"type": "string", "description": "Path to the shot-list JSON file."},
                "interval": {"type": "number", "minimum": 1, "description": "Seconds between shots (Agnes: 60)."},
                "character": {"type": "string", "description": "Identity anchor override."},
                "no_auto_refs": {"type": "boolean", "description": "Disable auto-injected refs."},
                "allow_referenceless": {"type": "boolean", "description": "Allow shots w/o refs."},
            },
            "required": ["project_id", "shots"],
        },
    },
    "stitch": {
        "command": "stitch",
        "builder": _build_stitch,
        "description": "Assemble clips into one video (transitions + color grade) — post-production.",
        "parameters": {
            "type": "object",
            "title": "Stitch",
            "properties": {
                "clips": {"type": "array", "items": {"type": "string"}, "description": "Clip paths."},
                "output": {"type": "string", "description": "Output video path."},
                "transition": {"type": "string", "description": "fade|wipe|dissolve|none."},
                "transition_duration": {"type": "number", "minimum": 0, "description": "Transition seconds."},
                "color_grade": {"type": "string", "description": "cinematic|warm|cool|none."},
            },
            "required": ["clips", "output"],
        },
    },
    "export_platforms": {
        "command": "export-platforms",
        "builder": _build_export_platforms,
        "description": "Export platform-optimized deliverables (tiktok, instagram_reel, youtube_standard).",
        "parameters": {
            "type": "object",
            "title": "Export Platforms",
            "properties": {
                "project_id": {"type": "string"},
                "platforms": {"type": "array", "items": {"type": "string"}},
                "output": {"type": "string", "description": "Output directory."},
            },
            "required": ["project_id"],
        },
    },
    "job_poll": {
        "command": "job-poll",
        "builder": _build_job_poll,
        "description": (
            "Read a durable image-job record and recover its result. Never "
            "submits a new generation (safe to call after a timeout)."
        ),
        "parameters": {
            "type": "object",
            "title": "Job Poll",
            "properties": {
                "job_id": {"type": "string", "description": "Job id from brandly image --json."},
                "max_age": {"type": "integer", "minimum": 1, "description": "Expiry seconds for running jobs."},
                "output": {"type": "string", "description": "Copy the result image here."},
            },
            "required": ["job_id"],
        },
    },
    "generate_image_cli": {
        "command": "image",
        "builder": _build_image,
        "description": (
            "Generate an image via the CLI (structured JSON result, atomic "
            "--output, durable job id). Use for one-off assets."
        ),
        "parameters": {
            "type": "object",
            "title": "Generate Image CLI",
            "properties": {
                "prompt": {"type": "string"},
                "model": {"type": "string"},
                "size": {"type": "string", "enum": ["1K", "2K", "3K", "4K"]},
                "ratio": {"type": "string", "enum": ["1:1", "3:4", "4:3", "16:9", "9:16", "2:3", "3:2", "21:9"]},
                "output": {"type": "string", "description": "Explicit destination file."},
                "project_id": {"type": "string", "description": "Record under this project."},
            },
            "required": ["prompt"],
        },
    },
    "plan": {
        "command": "plan",
        "builder": _build_plan,
        "description": (
            "Read the per-phase handoff contracts for a project (inputs, outputs, "
            "gate, next command, cost estimate) — the dispatch source of truth "
            "for orchestrator/subagent workflows. Read-only, writes nothing."
        ),
        "parameters": {
            "type": "object",
            "title": "Plan",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "json": {"type": "boolean", "description": "Emit the machine-readable handoff document."},
            },
            "required": ["project_id"],
        },
    },
    "init": {
        "command": "init",
        "builder": _build_init,
        "description": (
            "Start a new Brandly video project (writes project.json + AGENTS.md "
            "at the project root). Writes state — confirm first."
        ),
        "parameters": {
            "type": "object",
            "title": "Init",
            "properties": {
                "name": {"type": "string", "description": "Product name."},
                "idea": {"type": "string", "description": "Product idea / brief."},
                "style": {"type": "string", "description": "Video style (default cinematic)."},
                "budget": {"type": "integer", "minimum": 1, "description": "Max credits (default 500)."},
                "shots": {"type": "integer", "minimum": 3, "maximum": 10, "description": "Shot count (default 5)."},
            },
            "required": ["name", "idea"],
        },
    },
    "status": {
        "command": "status",
        "builder": _build_status,
        "description": (
            "Read project status and phase progress (read-only; supports the "
            "global --root)."
        ),
        "parameters": {
            "type": "object",
            "title": "Status",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
            },
            "required": ["project_id"],
        },
    },
    "progress": {
        "command": "progress",
        "builder": _build_progress,
        "description": "Read detailed pipeline progress for a project (read-only).",
        "parameters": {
            "type": "object",
            "title": "Progress",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
            },
            "required": ["project_id"],
        },
    },
    "approve": {
        "command": "approve",
        "builder": _build_approve,
        "description": (
            "Approve a phase and advance the pipeline — the human gate (NOT "
            "read-only; requires explicit approval)."
        ),
        "parameters": {
            "type": "object",
            "title": "Approve",
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "phase": {"type": "string", "description": "Phase to approve."},
            },
            "required": ["project_id", "phase"],
        },
    },
    "estimate": {
        "command": "estimate",
        "builder": _build_estimate,
        "description": (
            "Estimate credit cost before starting (read-only; one formula, "
            "shared with the plan handoffs)."
        ),
        "parameters": {
            "type": "object",
            "title": "Estimate",
            "properties": {
                "style": {"type": "string", "description": "Video style."},
                "shots": {"type": "integer", "minimum": 1, "description": "Shot count."},
                "target_duration": {"type": "integer", "minimum": 1, "description": "Target total seconds (quota-aware)."},
            },
        },
    },
    "record_cost": {
        "command": "record-cost",
        "builder": _build_record_cost,
        "description": (
            "Record actual credit spend for a phase operation (writes the cost "
            "ledger — never fabricate telemetry)."
        ),
        "parameters": {
            "type": "object",
            "title": "Record Cost",
            "properties": {
                "project_id": {"type": "string"},
                "phase": {"type": "string"},
                "action": {"type": "string"},
                "credits": {"type": "integer"},
            },
            "required": ["project_id", "phase", "action", "credits"],
        },
    },
    "memory": {
        "command": "memory",
        "builder": _build_memory,
        "description": (
            "Read or set the agent memory hook (list/show/set; writes state "
            "on set)."
        ),
        "parameters": {
            "type": "object",
            "title": "Memory",
            "properties": {
                "action": {"type": "string", "enum": ["list", "show", "set"], "description": "list|show|set"},
                "hook": {"type": "string", "description": "Hook value for set."},
            },
            "required": ["action"],
        },
    },
}


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

#: Tool domain groupings for MCP clients (helps clients surface related tools).
TOOL_DOMAINS: dict[str, list[str]] = {
    "project":  ["list_projects", "get_project", "init", "status", "progress", "plan"],
    "documents": ["write_bible", "read_bible", "write_screenplay", "read_screenplay"],
    "media":    ["generate_image", "generate_image_cli", "list_models"],
    "pre_production": [
        "cast_characters", "try_wardrobe", "animate_cast_15sec",
        "generate_sheet", "location_architect", "sound_design", "spatial_blocking",
    ],
    "generation": ["produce", "job_poll"],
    "production": [
        "director", "cascade", "fight_choreography", "director_of_photography", "editor",
        "stitch", "export_platforms", "update_clip", "reorder_timeline", "run_gate",
        "approve", "record_cost", "memory",
    ],
}

def tool_manifest() -> dict[str, Any]:
    """Return the full agent-callable capability set (JSON-serializable).

    Each tool entry carries MCP ``annotations`` (readOnlyHint,
    destructiveHint, idempotentHint) and ``skill`` (the owning Agent Skill
    slug) so clients can route to the right skill documentation.
    """
    tools: list[dict[str, Any]] = []

    for name, spec in agent_tools.BUILTIN_TOOLS.items():
        tools.append(
            {
                "name": name,
                "description": spec["description"],
                "parameters": spec["schema"],
                "read_only": READ_ONLY_TOOLS(name),
                "skill": agent_tools.skill_for(name),
                "annotations": TOOL_ANNOTATIONS.get(
                    name, {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
                ),
                "kind": "library",
                "command": None,
            }
        )

    for name, spec in CLI_TOOLS.items():
        tools.append(
            {
                "name": name,
                "description": spec["description"],
                "parameters": spec["parameters"],
                "read_only": READ_ONLY_TOOLS(name),
                "skill": agent_tools.skill_for(name),
                "annotations": TOOL_ANNOTATIONS.get(
                    name, {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False}
                ),
                "kind": "cli",
                "command": spec["command"],
            }
        )

    return {"version": MANIFEST_VERSION, "tools": tools, "domains": TOOL_DOMAINS}


def get_tool(name: str) -> dict[str, Any] | None:
    """Return one manifest entry, or None when the tool does not exist."""
    for entry in tool_manifest()["tools"]:
        if entry["name"] == name:
            return entry
    return None


def tool_names() -> list[str]:
    return [entry["name"] for entry in tool_manifest()["tools"]]


# ---------------------------------------------------------------------------
# AGENTS.md onboarding (init) — teach agents the tool surface, not raw HTTP
# ---------------------------------------------------------------------------


def render_agents_md() -> str:
    """Render the ``AGENTS.md`` that ``brandly init`` writes at the project root."""
    lines: list[str] = [
        "# Brandly — instructions for AI agents",
        "",
        "This project is produced by **brandly-cli**. Drive it through brandly's own",
        "tools — do not call AI providers directly and do not hand-roll ffmpeg pipelines.",
        "",
        "## Discover the tool surface (do not guess)",
        "",
        "- `brandly tools --json` — full manifest: name, description, JSON-Schema",
        "  parameters, read-only class, and the CLI command behind each tool.",
        "- `brandly mcp serve` — MCP server over stdio (JSON-RPC 2.0). Config:",
        "  `command: brandly`, `args: [\"mcp\", \"serve\"]`.",
        "",
        "## Read-only tools (safe to call without asking)",
        "",
    ]
    for entry in tool_manifest()["tools"]:
        if entry["read_only"]:
            lines.append(f"- `{entry['name']}` — {entry['description']}")

    lines += ["", "## Pipeline tools (write state or spend credits — confirm first)", ""]
    for entry in tool_manifest()["tools"]:
        if not entry["read_only"]:
            back = f" → `brandly {entry['command']}`" if entry["command"] else ""
            lines.append(f"- `{entry['name']}` — {entry['description']}{back}")

    lines += [
        "",
        "## Subagents (orchestrator → phase workers)",
        "",
        "For multi-step work, dispatch one phase-scoped worker subagent per",
        "phase (trends → concept → bible → casting → screenplay → script →",
        "asset → audio → re_edit → validate → publish) instead of doing everything in one context.",
        "Every worker gets five items: scope (its one phase), inputs, outputs,",
        "boundaries (what it must NOT touch), and verification (the gate that",
        "screens its result).",
        "- Dispatch source of truth: `brandly plan <project_id> --json` —",
        "  per-phase inputs/outputs/gate/next-command/cost estimate.",
        "- Parallel (safe): prompt crafting, trend research, gate runs,",
        "  status reads. Serialized (mandatory): generation API calls",
        "  (~1 req/min; `produce` enforces a 60s shot-by-shot queue).",
        "- The orchestrator holds the gates: `brandly gate <id> --all-scenes`",
        "  for asset/validate; `brandly status <id>` + artifact check otherwise.",
        "  Non-pass → re-dispatch with the failure report (max 3 attempts),",
        "  then escalate via `brandly approve <id> <phase>`.",
        "",
        "## Layout contract — where every document lives (never improvise)",
        "",
        "The tree is declared in `brandly_cli/layout.py`; writers route through",
        "`layout.docs_dir` — never hardcode a docs sub-folder:",
        "",
        "- `docs/plan/` — pre-generation plans (`production_plan.md`) ONLY.",
        "- `docs/bible/` — the production bible (`production_bible.md`, Section 4:",
        "  Characters feeds casting verbatim).",
        "- `docs/screenplay/` — the screenplay (`screenplay.md`).",
        "- `docs/storyboard/` — storyboards / shot lists.",
        "- `docs/general/` — research + creative + manifests (`trends.md`,",
        "  `concept.md`, `scenes.json`).",
        "- `docs/tmp/` — transient docs: gate reports, fail records,",
        "  `storyboard_progress.txt`, and RUN TRANSCRIPTS (`run_<ts>.log` —",
        "  `brandly run --execute` writes one itself; never redirect run output",
        "  to the project root).",
        "- `.brandly/<id>/shots.json` — the director shot list (the timeline",
        "  editor's path, load-bearing — documented exception).",
        "- Media trees: `pre-production/<id>/` and `production/<id>/` — NEVER drop",
        "  scratch/debug files here: every image is auto-injected as a video",
        "  reference and can displace real keyframes at the 5-ref cap (#295).",
        "",
        "## Production flow (the phase chain — do not reorder ad hoc)",
        "",
        "trends → concept → bible → casting → screenplay → script → asset",
        "→ audio → re_edit → validate → publish. The storyboard deliverable is",
        "the MANDATORY 4x4 graphite contact sheet",
        "(`skills/brandly-storyboard/references/grid-style-lock.md` — the pass",
        "tiles it in code). Casting reads the bible's Section 4 verbatim.",
        "",
        "## Rules",
        "",
        "1. Read the manifest before calling: `brandly tools --json`.",
        "2. Read `brandly plan <project_id> --json` before dispatching a worker.",
        "3. Keep provider credentials inside brandly; never copy secrets into scripts",
        "   or tool config files.",
        "4. Generate media with `produce` (scene naming, references, retries, production",
        "   plan) — not with raw provider HTTP calls.",
        "5. On a timeout, recover with `brandly job-poll <job-id>` — polling never",
        "   resubmits a generation.",
        "6. Assemble with `stitch`, then deliver with `export-platforms`.",
        "7. Transient provider failures (503 video_queue_full / ReadTimeout) mean",
        "   WAIT and re-run the phase — not a shot fix; the run transcript in",
        "   `docs/tmp/` records what happened.",
        "",
    ]
    return "\n".join(lines)


def ensure_agents_md(root: Path | str) -> tuple[Path, bool]:
    """Create ``<root>/AGENTS.md`` if absent. Never overwrite an existing file.

    Returns ``(path, created)``.
    """
    path = Path(root) / "AGENTS.md"
    if path.exists():
        return path, False
    path.write_text(render_agents_md(), encoding="utf-8")
    return path, True



# ---------------------------------------------------------------------------
# Build + dispatch
# ---------------------------------------------------------------------------


def _program_prefix(root: str | None = None) -> list[str]:
    prefix = [python_executable(), "-m", "brandly_cli"]
    if root:
        prefix += ["--root", str(root)]
    return prefix


def build_command(name: str, args: dict[str, Any], root: str | None = None) -> list[str]:
    """Map a tool call to the real CLI argv (pure function — nothing executes).

    Raises:
        KeyError: unknown tool, or a library tool (use :func:`dispatch`).
        ValueError: a required argument is missing.
    """
    spec = CLI_TOOLS.get(name)
    if spec is None:
        if name in agent_tools.BUILTIN_TOOLS:
            raise KeyError(f"{name} is a library tool — dispatch it, do not build a command")
        raise KeyError(f"unknown tool: {name}")
    return _program_prefix(root) + spec["builder"](args)


def _subprocess_runner(argv: list[str]) -> tuple[int, str, str]:
    """Default runner: the tool surface is the CLI, so shell out to it.

    Decoded as UTF-8 explicitly (via :func:`run_capture`): the CLI emits
    non-ASCII glyphs (→, ✓, —) and reconfigures its streams to UTF-8, which the
    platform locale codec (cp1252 on Windows) cannot decode — the decode error
    surfaced as a ``None`` stdout, silently losing the tool result.
    """
    proc = run_capture(argv)
    return proc.returncode, proc.stdout, proc.stderr


def _parse_json(stdout: str) -> Any | None:
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def dispatch(
    name: str,
    args: dict[str, Any] | None = None,
    *,
    root: str | None = None,
    runner: ToolRunner | None = None,
) -> dict[str, Any]:
    """Execute a tool call and return a machine-readable envelope.

    Envelope: ``{tool, ok, kind, exit_code, command, data, stdout, stderr, error}``.
    Failures are reported in the envelope, never raised at the caller.
    """
    call_args: dict[str, Any] = dict(args or {})
    envelope: dict[str, Any] = {
        "tool": name,
        "ok": False,
        "kind": None,
        "exit_code": None,
        "command": None,
        "data": None,
        "stdout": "",
        "stderr": "",
        "error": "",
    }

    if name in agent_tools.BUILTIN_TOOLS:
        envelope["kind"] = "library"
        envelope["read_only"] = READ_ONLY_TOOLS(name)
        schema = agent_tools.BUILTIN_TOOLS[name]["schema"]
        if root and "root" in schema.get("properties", {}) and "root" not in call_args:
            call_args["root"] = str(root)
        try:
            data = agent_tools.invoke_tool(name, **call_args)
        except Exception as e:  # surfaced, never raised
            envelope["error"] = f"{name}: {e}"
            return envelope
        envelope["data"] = data
        envelope["ok"] = not (isinstance(data, dict) and "error" in data)
        envelope["exit_code"] = 0 if envelope["ok"] else 1
        if not envelope["ok"] and isinstance(data, dict):
            envelope["error"] = str(data.get("error", ""))
        return envelope

    if name not in CLI_TOOLS:
        envelope["error"] = f"unknown tool: {name}. Available: {', '.join(tool_names())}"
        return envelope

    envelope["kind"] = "cli"
    envelope["read_only"] = READ_ONLY_TOOLS(name)
    try:
        argv = build_command(name, call_args, root=root)
    except (KeyError, ValueError) as e:
        envelope["error"] = str(e)
        return envelope

    envelope["command"] = argv
    run = runner or _subprocess_runner
    exit_code, stdout, stderr = run(argv)
    envelope["exit_code"] = exit_code
    envelope["stdout"] = stdout or ""
    envelope["stderr"] = stderr or ""
    envelope["data"] = _parse_json(stdout or "")
    envelope["ok"] = exit_code == 0
    if not envelope["ok"]:
        envelope["error"] = (
            (stderr or "").strip() or (stdout or "").strip() or f"exit code {exit_code}"
        )
    return envelope


