"""G5: single source of truth for what brandly-cli can do today.

This module is the machine-readable capability matrix that the README's
"What is Brandly?" section and the CI guard (``tests/test_capabilities.py``)
are checked against. Rules:

* Every ``supported`` row must name a real command in the CLI surface.
* ``absent``/``partial`` rows carry ``banned_claims``: README phrases that
  would over-claim the capability. The guard test fails when such a phrase
  appears in the README outside a planned/roadmap context (a line carrying
  a planning marker such as "planned", "gap" or "G6" is allowed).
* Statuses: ``supported | partial | planned | absent``.

Nothing here is prose — the renderer (``cmd/capabilities.py``) and the guard
both read from this list.
"""

from __future__ import annotations

from typing import Any

#: Personas the capability matrix reports for (audit F9).
PERSONAS: tuple[str, ...] = ("filmmaker", "creator", "marketer")

#: Valid capability statuses.
STATUSES: tuple[str, ...] = ("supported", "partial", "planned", "absent")

#: Planning markers that make a banned phrase acceptable in the README
#: (roadmap content is honest; aspirational claims are not).
PLANNING_MARKERS: tuple[str, ...] = (
    "planned",
    "gap",
    "absent",
    "roadmap",
    "not available",
    "g6",
    "f9",
    "issue",
)

CAPABILITIES: tuple[dict[str, Any], ...] = (
    # --- filmmaker: the generation half is real (audit F9 ✅ rows) ----------
    {
        "id": "shot_generation",
        "persona": "filmmaker",
        "status": "supported",
        "command": "produce",
        "note": "shot-by-shot generation with retries, resume, canonical Scene-XX-Shot-X-Y naming",
        "banned_claims": (),
    },
    {
        "id": "storyboard_references",
        "persona": "filmmaker",
        "status": "supported",
        "command": "storyboard",
        "note": "storyboard, reference sheets, blocking; bundled skills",
        "banned_claims": (),
    },
    {
        "id": "assembly_post",
        "persona": "filmmaker",
        "status": "supported",
        "command": "stitch",
        "note": "stitch, captions, dubbing, beat-sync, thumbnails, platform export",
        "banned_claims": (),
    },
    {
        "id": "scene_model",
        "persona": "filmmaker",
        "status": "supported",
        "command": "scenes",
        "finding": "F6",
        "note": "explicit scene model (scenes.json manifest written at produce time) — G3",
        "banned_claims": (),
    },
    {
        "id": "scene_gate",
        "persona": "filmmaker",
        "status": "supported",
        "command": "gate",
        "finding": "F7",
        "note": "scene/shot completeness gate (`brandly gate --scene/--all-scenes`) — G3",
        "banned_claims": (),
    },
    {
        "id": "director_orchestration",
        "persona": "filmmaker",
        "status": "supported",
        "command": "run",
        "finding": "F3/F4",
        "note": "`brandly run <id> --execute` advances real phases with "
        "per-phase gates — G2. Agent/human-driven, not autonomous.",
        "banned_claims": (
            "autonomous pipeline",
            "autonomous agent",
            "autonomous video production",
        ),
    },
    {
        "id": "agent_tool_surface",
        "persona": "filmmaker",
        "status": "supported",
        "command": "mcp",
        "finding": "F1/F2",
        "note": "agent-callable tool manifest + MCP server; `brandly sync` "
        "no longer injects raw provider keys — G1",
        "banned_claims": (),
    },
    {
        "id": "ratio_policy",
        "persona": "filmmaker",
        "status": "supported",
        "command": "stitch",
        "finding": "F8",
        "note": "production keeps source aspect; the ratio crop/pad happens "
        "once in assembly/export (`stitch --ratio --fit`) — G4",
        "banned_claims": (),
    },
    # --- creator -----------------------------------------------------------
    {
        "id": "credit_budgeting",
        "persona": "creator",
        "status": "supported",
        "command": "status",
        "note": "credit spend tracked per phase against the project budget; budget gate",
        "banned_claims": (),
    },
    {
        "id": "style_presets",
        "persona": "creator",
        "status": "supported",
        "command": "image",
        "note": "photoreal/cinematic/editorial/commercial/documentary presets",
        "banned_claims": (),
    },
    {
        "id": "campaign_ab",
        "persona": "creator",
        "status": "partial",
        "command": "batch",
        "finding": "F9",
        "note": "`brandly batch` submits variants one at a time; no variant "
        "matrix or scoring loop yet",
        "banned_claims": ("variant matrix", "A/B at scale"),
    },
    # --- marketer ----------------------------------------------------------
    {
        "id": "publish_schedule",
        "persona": "marketer",
        "status": "partial",
        "command": "publish",
        "finding": "F9",
        "planned": "live YouTube upload (credentials) + TikTok/IG adapters (DEV-G6-001)",
        "note": "`brandly publish <id> --platform youtube [--schedule ISO] "
        "[--dry-run]` — dry-run renders the exact payload, never posts; live "
        "posting requires a stored credential (decision DEV-G6-001). "
        "TikTok/Instagram adapters are follow-ups",
        "banned_claims": (
            "publishes to",
            "publish to",
            "schedules to",
            "auto-publish",
            "automated workflow",
        ),
    },
    {
        "id": "brand_kit",
        "persona": "marketer",
        "status": "supported",
        "command": "brand",
        "finding": "F9",
        "note": (
            "G7: `brandly brand init/verify/show` + prompt-layer palette/claim "
            "lock (PR 1); gate-layer claim check hard-fails `brandly gate` and "
            "`export-platforms --brand` composites the kit's logo via ffmpeg "
            "overlay (PR 2)"
        ),
    },
    {
        "id": "metrics_ingest",
        "persona": "marketer",
        "status": "supported",
        "command": "metrics",
        "finding": "F9",
        "note": (
            "`brandly metrics import` (CSV/JSON, project-local snapshots) + "
            "`analyze` ingested-vs-heuristic source labelling (G8 PR 1); "
            "YouTube Analytics API next step planned (G8 PR 2)"
        ),
    },
)


def capability_matrix() -> dict[str, Any]:
    """The machine-readable matrix (``brandly capabilities --json`` payload)."""
    return {
        "personas": list(PERSONAS),
        "statuses": list(STATUSES),
        "capabilities": [dict(c) for c in CAPABILITIES],
    }


def capabilities_by_status() -> dict[str, list[dict[str, Any]]]:
    """Rows grouped by status (rendering convenience)."""
    out: dict[str, list[dict[str, Any]]] = {s: [] for s in STATUSES}
    for cap in CAPABILITIES:
        out[cap["status"]].append(cap)
    return out
