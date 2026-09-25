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
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from brandly_cli import agent_tools

# (exit_code, stdout, stderr)
ToolRunner = Callable[[list[str]], tuple[int, str, str]]

MANIFEST_VERSION = 1

#: Handlers that only read state — safe for an agent to call unprompted.
READ_ONLY_TOOLS = frozenset(
    {"list_projects", "get_project", "list_jobs", "list_models", "get_timeline", "run_gate", "plan"}
)


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
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "shots": {"type": "string", "description": "Path to the shot-list JSON file."},
                "interval": {"type": "number", "description": "Seconds between shots (Agnes: 60)."},
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
            "properties": {
                "clips": {"type": "array", "items": {"type": "string"}, "description": "Clip paths."},
                "output": {"type": "string", "description": "Output video path."},
                "transition": {"type": "string", "description": "fade|wipe|dissolve|none."},
                "transition_duration": {"type": "number", "description": "Transition seconds."},
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
            "properties": {
                "job_id": {"type": "string", "description": "Job id from brandly image --json."},
                "max_age": {"type": "integer", "description": "Expiry seconds for running jobs."},
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
            "properties": {
                "prompt": {"type": "string"},
                "model": {"type": "string"},
                "size": {"type": "string"},
                "ratio": {"type": "string"},
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
            "properties": {
                "project_id": {"type": "string", "description": "Project id."},
                "json": {"type": "boolean", "description": "Emit the machine-readable handoff document."},
            },
            "required": ["project_id"],
        },
    },
}


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def tool_manifest() -> dict[str, Any]:
    """Return the full agent-callable capability set (JSON-serializable)."""
    tools: list[dict[str, Any]] = []

    for name, spec in agent_tools.BUILTIN_TOOLS.items():
        tools.append(
            {
                "name": name,
                "description": spec["description"],
                "parameters": spec["schema"],
                "read_only": name in READ_ONLY_TOOLS,
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
                "read_only": name in READ_ONLY_TOOLS,
                "kind": "cli",
                "command": spec["command"],
            }
        )

    return {"version": MANIFEST_VERSION, "tools": tools}


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
        "phase (trends → concept → script → asset → audio → re_edit →",
        "validate → publish) instead of doing everything in one context.",
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

    Decoded as UTF-8 explicitly: the CLI emits non-ASCII glyphs (→, ✓, —) and
    reconfigures its streams to UTF-8, which the platform locale codec (cp1252
    on Windows) cannot decode — the decode error surfaced as a ``None`` stdout,
    silently losing the tool result.
    """
    proc = subprocess.run(
        argv, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
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
        envelope["read_only"] = name in READ_ONLY_TOOLS
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
    envelope["read_only"] = name in READ_ONLY_TOOLS
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


