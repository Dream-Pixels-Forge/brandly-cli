"""Commands for the ``brandly production`` group.
Moved from cli.py (structural split, no behavioral change).
Shared helpers and state still live in ``brandly_cli.cli``.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import click
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from brandly_cli import layout, scenes, shot_runner, stitch
from brandly_cli.agnes_client import (
    create_video_task,
    generate_image,
    poll_video,
)
from brandly_cli.ark_client import (
    create_video_task as ark_create_video_task,
)
from brandly_cli.ark_client import (
    generate_image as ark_generate_image,
)
from brandly_cli.ark_client import (
    poll_video as ark_poll_video,
)
from brandly_cli.audio_client import generate_music, generate_tts
from brandly_cli.cli import (
    _check_budget,
    _check_phase_artifacts,
    _get_root,
    _print_json,
    _print_project_summary,
    _print_scene_report,
    cli,
    console,
)
from brandly_cli.cmd.generation import _generate_shot, _run_produce_runner
from brandly_cli.constants import (
    DEFAULT_AGNES_VIDEO_MODEL,
    PHASE_ORDER,
    SHOT_COSTS,
    STYLE_COSTS,
    VIDEO_STYLES,
    StylePreset,
)
from brandly_cli.cost_tracker import CostTracker
from brandly_cli.director import get_director_prompt
from brandly_cli.memory import UserPreferences
from brandly_cli.project_manager import ProjectManager
from brandly_cli.style_presets import apply_style_preset
from brandly_cli.types import PhaseResult
from brandly_cli.utils import (
    _now_iso,
    _read_production_plan_rows,
    download_file,
    ellipsize,
    generate_project_id,
    generate_project_slug,
    generate_readable_id,
    is_valid_project_id,
    now_iso,
    sanitize_filename,
)
from brandly_cli.video_prompts import build_enhanced_video_prompt


@click.command()
@click.option("--name", "-n", required=True, help="Product name")
@click.option("--idea", "-i", required=True, help="Product idea / brief")
@click.option(
    "--style",
    "-s",
    default="cinematic",
    help=f"Video style (default: cinematic). Choices: {', '.join(VIDEO_STYLES)}",
)
@click.option("--budget", "-b", default=500, help="Max credits to spend (default: 500)")
@click.option("--shots", default=5, help="Number of shots (3-10, default: 5)")
@click.option(
    "--platforms", "-p", multiple=True, help="Target platforms (tiktok, instagram, youtube, all)"
)
@click.option("--image", "-img", default=None, help="Optional product image path")
@click.pass_context
def init(
    ctx: click.Context,
    name: str,
    idea: str,
    style: str,
    budget: int,
    shots: int,
    platforms: tuple[str, ...],
    image: str | None,
) -> None:
    """Start a new Brandly video project."""
    if style not in VIDEO_STYLES:
        console.print(f"[red]Invalid style '{style}'. Choices: {', '.join(VIDEO_STYLES)}[/red]")
        sys.exit(1)
    if shots < 3 or shots > 10:
        console.print("[red]Shots must be between 3 and 10.[/red]")
        sys.exit(1)

    root = _get_root(ctx)
    pm = ProjectManager(root)
    # Use human-readable ID based on project name
    pid = generate_readable_id(name)
    # Ensure unique ID by appending timestamp if needed
    existing = asyncio.run(pm.read(pid))
    if existing:
        pid = f"{pid}-{generate_project_id().replace('project-', '')}"

    from brandly_cli.types import ProjectData

    slug = generate_project_slug(name)
    proj = ProjectData(
        id=pid,
        name=name,
        slug=slug,
        description=idea,
        style=style,
        shot_count=shots,
        budget=budget,
        target_platforms=list(platforms) if platforms else ["tiktok", "instagram"],
    )
    proj = proj.model_copy(update={"layout_version": 2})
    asyncio.run(pm.create(proj))
    from brandly_cli import migrate as migrate_mod

    migrate_mod.ensure_v2_skeleton(root, pid)

    # Agent onboarding (audit F1): point agents at the tool surface instead of
    # letting them invent their own tools. Never overwrites a user's file.
    from brandly_cli import agent_surface

    agents_path, agents_created = agent_surface.ensure_agents_md(root)

    console.print(Panel(f"Project created! [green]{pid}[/green]", title="Brandly"))
    console.print(f"  Slug:      {slug}")
    console.print(f"  Name:      {name}")
    console.print(f"  Style:     {style}")
    console.print(f"  Shots:     {shots}")
    console.print(f"  Budget:    {budget} credits")
    console.print(f"  Platforms: {proj.target_platforms}")
    console.print(
        f"  AGENTS.md: {'created' if agents_created else 'kept existing'} "
        f"({agents_path.name} → brandly tools / brandly mcp serve)"
    )
    console.print(f"\nNext: [bold]brandly run {pid}[/bold] to start the pipeline.")

@click.command()
@click.argument("project_id")
@click.pass_context
def status(ctx: click.Context, project_id: str) -> None:
    """Show project status and phase progress."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    pm = ProjectManager(root)
    proj = asyncio.run(pm.read(project_id))
    if not proj:
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)

    summary: dict[str, Any] = {
        "id": proj.id,
        "slug": proj.slug,
        "name": proj.name,
        "status": proj.status,
        "current_phase": proj.current_phase,
        "budget": proj.budget,
        "spent": proj.spent,
        "remaining": proj.budget - proj.spent,
        "style": proj.style,
        "shot_count": proj.shot_count,
        "target_platforms": proj.target_platforms,
        "created_at": proj.created_at,
        "updated_at": proj.updated_at,
    }
    _print_project_summary(summary)

@click.command(name="list")
@click.pass_context
def list_projects(ctx: click.Context) -> None:
    """List all projects."""
    root = _get_root(ctx)
    pm = ProjectManager(root)
    projects = asyncio.run(pm.list_with_status())
    if not projects:
        console.print("[dim]No projects found.[/dim]")
        return
    from rich.table import Table

    table = Table(title="Projects")
    table.add_column("ID", style="cyan")
    table.add_column("Slug", style="green")
    table.add_column("Name", style="white")
    table.add_column("Status", style="green")
    table.add_column("Phase", style="yellow")
    table.add_column("Budget", style="magenta")
    table.add_column("Spent", style="blue")
    table.add_column("Updated", style="dim")
    for p in projects:
        table.add_row(
            p["id"][:8] + "...",
            p.get("slug") or "",
            ellipsize(p.get("name") or "", 20),
            p["status"],
            p["current_phase"],
            f"{p['budget']}",
            f"{p['spent']}/{p['budget']}",
            (p.get("updated_at") or "")[:10],
        )
    console.print(table)

@click.command()
@click.argument("project_id")
@click.option(
    "--execute",
    is_flag=True,
    help="Execute the pipeline for real via the Director orchestrator (resumable).",
)
@click.option(
    "--until",
    "until_phase",
    type=click.Choice(PHASE_ORDER),
    default=None,
    help="With --execute: stop after this phase completes.",
)
@click.option(
    "--yes",
    is_flag=True,
    help="With --execute: skip the confirmation prompt.",
)
@click.pass_context
def run(
    ctx: click.Context,
    project_id: str,
    execute: bool,
    until_phase: str | None,
    yes: bool,
) -> None:
    """Run the next phase of the pipeline.

    Without ``--execute`` this only marks the current phase running (the
    agent-driven workflow; approve with ``brandly approve``). With
    ``--execute`` the Director orchestrator runs the real phase workers
    from the current phase onward, resuming from ``project.phases`` and
    failing closed on the first phase error.
    """
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    pm = ProjectManager(root)
    proj = asyncio.run(pm.read(project_id))
    if not proj:
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)
    if proj.status in ("cancelled", "paused"):
        console.print(f"[red]Project is {proj.status}. Cannot run.[/red]")
        sys.exit(1)
    if proj.status == "completed":
        console.print("[dim]All phases completed.[/dim]")
        return

    _check_budget(ctx, project_id)

    if execute:
        if not yes:
            click.confirm(
                f"Execute the pipeline from '{proj.current_phase}' to "
                f"'{until_phase or 'done'}'? This runs real generation and "
                "spends credits.",
                abort=True,
            )
        director = Director(DirectorConfig(root))
        result = asyncio.run(director.run_pipeline(project_id, until=until_phase))
        if "error" in result:
            console.print(
                f"[red]✗ Phase '{result['failed_phase']}' failed: "
                f"{result['error']}[/red]"
            )
            console.print(
                "[dim]Fix the issue and re-run the same command to resume.[/dim]"
            )
            sys.exit(1)
        console.print(
            f"[green]✓ Pipeline executed: {' → '.join(result['phases_run'])}[/green]"
        )
        return

    current = proj.current_phase
    console.print(f"[bold]Running phase:[/bold] {current}")
    console.print(f"[dim]Agent: {PHASE_ORDER.index(str(current)) + 1}/{len(PHASE_ORDER)}[/dim]")  # type: ignore[arg-type]

    phases = getattr(proj, "phases", {})
    if current not in phases:
        phases[current] = PhaseResult(status="pending")
    phases[current] = PhaseResult(status="running", started_at=now_iso())
    asyncio.run(pm.update(project_id, {"phases": phases, "status": "running"}))

    console.print(f"[green]Phase '{current}' started.[/green]")
    console.print(f"\nNext: approve with [bold]brandly approve {project_id} {current}[/bold]")

@click.command()
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Emit the handoffs as one JSON document")
@click.pass_context
def plan(ctx: click.Context, project_id: str, as_json: bool) -> None:
    """Show the per-phase handoff contracts for orchestrator/subagent dispatch.

    Human-readable table by default; ``--json`` emits one machine-readable
    document (``brandly plan <id> --json`` is the dispatch source of truth for
    agents — rich console output is suppressed for the whole run).
    """
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    payload = phase_handoffs(root, project_id)
    if as_json:
        # Plain print: console.print would wrap/mangle long JSON lines.
        print(json.dumps(payload, indent=2))
        return
    table = Table(title="Phase handoffs (dispatch contracts)")
    table.add_column("Phase", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Gate", style="dim")
    table.add_column("Est. cost", justify="right")
    for h in payload["handoffs"]:
        status = h["status"]
        style = {"completed": "green", "failed": "red", "running": "yellow"}.get(status, "dim")
        table.add_row(h["id"], f"[{style}]{status}[/{style}]", h["gate"]["command"], str(h["est_cost"]))
    console.print(table)
    nxt = payload["next_command"]
    if payload["current"] is None:
        if nxt is None:
            console.print("[green]Pipeline complete — nothing left to run.[/green]")
        else:
            console.print(f"Next command: [bold]{nxt}[/bold]")
    else:
        console.print(f"Current step: [bold]{payload['current']}[/bold]")
        console.print(f"Next command: [bold]{nxt}[/bold]")


@click.command(name="director")
@click.argument("project_id", required=False, default=None)
@click.pass_context
def director(ctx: click.Context, project_id: str | None = None) -> None:
    """Show the Director prompt and orchestrator plan for AI tools.

    Prints the agent-facing prompt plus the live plan: pipeline phases,
    per-phase status, current step, and the exact next command
    (``brandly run <id> --execute --yes``).  With no project, the plan
    is generic and the next command is ``brandly init``.
    """
    prompt = get_director_prompt()
    console.print(Panel(Markdown(prompt), title="Brandly Director Mode"))

    plan = director_plan(_get_root(ctx), project_id)
    table = Table(title="Orchestrator plan")
    table.add_column("Phase", style="cyan")
    table.add_column("Status", style="white")
    status_styles = {
        "completed": "green",
        "failed": "red",
        "running": "yellow",
        "in_progress": "yellow",
    }
    for phase in plan["phases"]:
        status = plan["phases_status"][phase]
        style = status_styles.get(status, "dim")
        table.add_row(phase, f"[{style}]{status}[/{style}]")
    console.print(table)

    if plan["current"] is None:
        if plan["next_command"] is None:
            console.print("[green]Pipeline complete — nothing left to run.[/green]")
        else:
            console.print(f"Next command: [bold]{plan['next_command']}[/bold]")
    else:
        console.print(f"Current step: [bold]{plan['current']}[/bold]")
        console.print(f"Next command: [bold]{plan['next_command']}[/bold]")

    _print_dispatch_table(project_id)


def _print_dispatch_table(project_id: str | None) -> None:
    """Print the subagent dispatch contracts (G7 PR F).

    Compact, in-command render of :data:`PHASE_HANDOFF_SPECS` — the same
    contracts ``brandly plan --json`` emits as data. Kept terse on purpose:
    static strings only, no project reads, so this never fails on an
    unknown project.
    """
    _ = project_id  # reserved: per-project est_cost rendering stays in `plan`.
    table = Table(title="Subagent dispatch (orchestrator → phase workers)")
    table.add_column("Phase", style="cyan")
    table.add_column("Gives worker", style="white")
    table.add_column("Must produce", style="white")
    table.add_column("Verify with", style="dim")
    for phase in PHASE_ORDER:
        if phase in ("init", "done"):
            continue
        spec = PHASE_HANDOFF_SPECS[phase]
        table.add_row(
            phase,
            "; ".join(spec["inputs"]),
            "; ".join(spec["outputs"]),
            spec["gate"]["command"],
        )
    console.print(table)
    console.print("[dim]Dispatch source of truth: `brandly plan <project_id> --json`[/dim]")


@click.command()
@click.argument("project_id")
@click.argument("phase")
@click.pass_context
def approve(ctx: click.Context, project_id: str, phase: str) -> None:
    """Approve a phase and advance the pipeline."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    if phase not in PHASE_ORDER:
        console.print(f"[red]Invalid phase '{phase}'. Choices: {', '.join(PHASE_ORDER)}[/red]")
        sys.exit(1)

    root = _get_root(ctx)
    pm = ProjectManager(root)
    proj = asyncio.run(pm.read(project_id))
    if not proj:
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)
    if proj.status == "cancelled":
        console.print("[red]Cannot approve — project is cancelled.[/red]")
        sys.exit(1)
    if proj.current_phase != phase:
        console.print(f"[red]Current phase is '{proj.current_phase}', not '{phase}'.[/red]")
        sys.exit(1)

    _check_budget(ctx, project_id)

    # Gate: verify that the phase actually produced its required artifacts.
    missing = _check_phase_artifacts(project_id, phase, root)
    if missing:
        console.print(
            f"[red]Cannot approve '{phase}': missing required artifacts.[/red]"
        )
        for label, path in missing:
            console.print(f"  [red]✗[/red] {label}: {path}")
        sys.exit(1)

    idx = PHASE_ORDER.index(phase)
    next_phase = PHASE_ORDER[idx + 1] if idx < len(PHASE_ORDER) - 1 else "done"

    phases = dict(getattr(proj, "phases", {}))
    existing = phases.get(phase)
    existing_dict = existing.model_dump() if isinstance(existing, PhaseResult) else (existing or {})
    phases[phase] = PhaseResult(
        status="completed",
        started_at=existing_dict.get("started_at"),
        completed_at=now_iso(),
        output=existing_dict.get("output"),
        error=existing_dict.get("error"),
    )
    phases[next_phase] = PhaseResult(status="pending", started_at=now_iso())

    updates: dict[str, Any] = {
        "current_phase": next_phase,
        "phases": phases,
        "updated_at": now_iso(),
    }
    if next_phase == "done":
        updates["status"] = "completed"

    asyncio.run(pm.update(project_id, updates))
    from rich.panel import Panel

    console.print(
        Panel(f"Phase '{phase}' approved → next: [bold]{next_phase}[/bold]", title="Approved")
    )

@click.command()
@click.option("--style", default="cinematic", help="Video style")
@click.option("--shots", default=5, help="Number of shots (3-10)")
@click.pass_context
def estimate(ctx: click.Context, style: str, shots: int) -> None:
    """Estimate credit cost before starting."""
    if style not in STYLE_COSTS:
        console.print(f"[red]Invalid style '{style}'.[/red]")
        sys.exit(1)
    if shots < 3 or shots > 10:
        console.print("[red]Shots must be between 3 and 10.[/red]")
        sys.exit(1)

    style_cost = STYLE_COSTS[style]
    shot_cost = SHOT_COSTS.get(shots, 0)
    total_base = style_cost + shot_cost
    overhead = 60
    total_estimate = total_base + overhead

    phase_estimates = phase_costs(style, shots)

    console.print(f"\n[bold]Cost Estimate — {style} style, {shots} shots[/bold]\n")
    from rich.table import Table

    table = Table(show_header=True, header_style="cyan")
    table.add_column("Phase", style="white")
    table.add_column("Estimate (credits)", justify="right")
    for phase, cost in phase_estimates.items():
        table.add_row(phase, str(cost))
    table.add_row("Style base", str(style_cost))
    table.add_row("Shot extra", str(shot_cost))
    table.add_row("[bold]Total[/bold]", f"[bold]{total_estimate}[/bold]")
    console.print(table)
    console.print(
        f"\n[dim]Recommendation: Set budget to at least {total_estimate} credits.[/dim]\n"
    )

@click.command()
@click.argument("project_id")
@click.option(
    "--shots",
    "shots_file",
    required=True,
    help="Path to a shot list JSON file. Flat schema: "
    '[{"name": "shot-1", "prompt": "...", "duration": 5, "style": "cinematic", '
    '"references": "a.png,b.png"}, ...]. Structured schema (acts with per-act '
    'prefix/style/folder and plate-stem references): {"character": "...", '
    '"acts": {"act1": {"prefix": "...", "style": "cinematic", "folder": '
    '"scenes", "shots": [{"id": "shot01", "prompt": "...", "duration": 6, '
    '"refs": ["char_rebel", "loc_ink"]}]}}}',
)
@click.option(
    "--interval",
    default=60.0,
    show_default=True,
    help="Seconds to wait BETWEEN shot generations (Agnes: 1 request per minute).",
)
@click.option(
    "--no-auto-refs",
    "no_auto_refs",
    is_flag=True,
    default=False,
    help="Do NOT auto-inject project images as references (issue #20). Each shot's "
    "reference payload comes from the shot list only. Routes the run through the "
    "progress-file runner (docs/tmp/produce_progress.txt).",
)
@click.option(
    "--character",
    default=None,
    help="Character identity anchor passed to every shot whose references include "
    "a character plate. Overrides the shot list's top-level 'character' string.",
)
@click.option(
    "--allow-referenceless",
    is_flag=True,
    default=False,
    help="Bypass the require-reference check for shots without references.",
)
@click.option(
    "--max-wait",
    "max_wait",
    default=600,
    show_default=True,
    help="Max wait seconds per shot generation.",
)
@click.option(
    "--only",
    multiple=True,
    help="Run only this shot id (repeatable). Routes through the progress-file runner.",
)
@click.option(
    "--max",
    "max_shots",
    default=0,
    show_default=True,
    help="Run at most N shots, then stop. Routes through the progress-file runner.",
)
@click.option(
    "--retries",
    type=int,
    default=0,
    show_default=True,
    help=(
        "On-the-spot retries per failed shot (issue #39). Each retry waits the "
        "retry backoff (default: --interval) and is logged to the progress file "
        "as RETRY retry=N backoff=Xs <reason>; terminal failures log FAIL with "
        "the attempt count. 0 = fail fast (legacy)."
    ),
)
@click.option(
    "--split-long-shots",
    is_flag=True,
    default=False,
    help=(
        "Split shots whose duration exceeds the Agnes model max (12s) into 6s "
        "parts with continuity notes, so takes are no longer silently clamped "
        "(issue #35)."
    ),
)
@click.option(
    "--aspect-ratio",
    "aspect_ratio",
    default=None,
    help=(
        "Crop every generated clip to this aspect ratio (e.g. 2.39:1) as a "
        "post-processing step when the model cannot output it natively "
        "(issue #40). Requires ffmpeg."
    ),
)
@click.option(
    "--no-plan",
    is_flag=True,
    default=False,
    help=(
        "Do not register runner-path shots on the production plan (legacy "
        "behavior). By default each shot gets a plan file named with its shot "
        "ID (issue #37)."
    ),
)
@click.option(
    "--open-ui",
    is_flag=True,
    default=False,
    help="Open the timeline editor UI after all shots are generated.",
)
@click.pass_context
def produce(
    ctx: click.Context,
    project_id: str,
    shots_file: str,
    interval: float,
    no_auto_refs: bool,
    character: str | None,
    allow_referenceless: bool,
    max_wait: int,
    only: tuple[str, ...],
    max_shots: int,
    retries: int,
    split_long_shots: bool,
    aspect_ratio: str | None,
    no_plan: bool,
    open_ui: bool,
) -> None:
    """Generate a multi-shot film shot by shot from the production plan.

    The production plan is the source of truth: ALL shots are first
    registered on it (docs/plan/production_plan.md), then generation is
    pulled from the plan one shot at a time — there is deliberately NO batch
    or parallel mode, honouring the Agnes 1 request/minute rate limit.

    Shots already COMPLETED in the production plan are skipped, so the run
    is resumable: fix a failed shot and run the same command again.

    A structured shot list ({"acts": ...}), or any of --no-auto-refs /
    --character / --allow-referenceless / --only / --max, routes the run
    through the progress-file runner instead: resumable via
    .brandly/<project>/docs/tmp/produce_progress.txt, per-act prompt prefix
    and style, plate-stem reference resolution (optimized .opt.jpg twins
    preferred), character anchoring, transition clips moved to
    videos/transition/, clips renamed to the deterministic
    Scene-<scene:02d>-Shot-<scene>-<shot-in-scene>.mp4 convention (scene =
    act-level/shot-level "scene" key, else the act's position in the shot
    list), and a post-generation-step failure (quality gate crash)
    tolerates a downloaded clip.
    """
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)

    root = _get_root(ctx)
    path = Path(shots_file)
    if not path.is_file():
        console.print(f"[red]Shot list not found: {path}[/red]")
        sys.exit(1)
    try:
        shots = shot_runner.load_shots_file(path)
    except ValueError as e:
        console.print(f"[red]Invalid shot list: {e}[/red]")
        sys.exit(1)

    # Goal 3 (audit F6/F7): register the scene manifest BEFORE any generation
    # begins — scenes.json is the source of truth for the scene gate
    # (`brandly scenes status`, `brandly gate --scene/--all-scenes`).
    scenes.write_scenes(project_id, shots, root=root)

    use_runner = (
        isinstance(shots, dict)
        or no_auto_refs
        or character
        or allow_referenceless
        or only
        or max_shots
    )
    if use_runner:
        console.print(
            "[dim]Resumable runner → "
            f".brandly/{project_id}/docs/tmp/{shot_runner.PROGRESS_FILENAME}"
        )
        _run_produce_runner(
            ctx,
            project_id,
            shots,
            root,
            interval,
            no_auto_refs,
            character,
            allow_referenceless,
            max_wait,
            only,
            max_shots,
            retries=retries,
            split_long_shots=split_long_shots,
            aspect_ratio=aspect_ratio,
            no_plan=no_plan,
        )
        return

    # The production-plan loop is flat-schema only: a structured shot list
    # always takes the runner above. Re-asserting the shape narrows the
    # load_shots_file() union for the type checker and fails loudly if a
    # future schema ever reaches this branch.
    if not isinstance(shots, list):
        console.print("[red]Shot list must be a JSON array of shot objects.[/red]")
        sys.exit(1)

    # ---- Phase 1: prepare ALL shots on the production plan (source of truth)
    from brandly_cli.utils import (
        production_plan_path,
        upsert_production_plan,
        write_generation_plan,
    )

    model = "agnes-video-2.5-flash"
    prepared: list[tuple[dict[str, Any], str, Path]] = []
    for idx, shot in enumerate(shots, start=1):
        # Issue #37: prefer an explicit shot id in the plan file name.
        name = str(shot.get("id") or shot.get("name") or f"shot-{idx}")
        slug = sanitize_filename(name.lower()) or f"shot-{idx}"
        asset_type = f"video-shot-{slug}"
        # Issue #31: flat lists may also carry structured prompt dicts.
        raw_prompt = shot.get("prompt", "")
        if isinstance(raw_prompt, Mapping):
            from brandly_cli.video_prompts import expand_structured_prompt

            raw_prompt = expand_structured_prompt(
                raw_prompt,
                character=str(shot.get("character", "")) or None,
                duration=int(shot.get("duration", 5)),
            )
        plan, plan_reused = write_generation_plan(
            project_id,
            asset_type,
            root=root,
            prompt=str(raw_prompt),
            model=model,
            style=str(shot.get("style", "cinematic")),
            extra_config={
                "shot": name,
                "duration": f"{shot.get('duration', 5)}s",
                "role": "shot",
            },
            source="brandly produce",
            shot_id=name,
            scene=shot_runner.as_int(shot.get("scene"), 1),
        )
        prepared.append(({**shot, "prompt": str(raw_prompt)}, name, plan))
        console.print(
            f"[dim]Shot {name}: plan {'reused' if plan_reused else 'written'}: "
            f"{plan.name}[/dim]"
        )

    plan_doc = production_plan_path(project_id, root=root)
    console.print(
        f"[green]✓ {len(prepared)} shot(s) registered on the production plan:[/green] "
        f"{plan_doc}"
    )

    # ---- Phase 2: generate from the plan, one shot at a time (NO batch).
    rows = _read_production_plan_rows(plan_doc)
    for idx, (shot, name, plan) in enumerate(prepared):
        status = rows.get(plan.name, {}).get("status", "PENDING")
        if status == "COMPLETED":
            console.print(f"[dim]Shot {name} already COMPLETED — skipping.[/dim]")
            continue
        if idx > 0:
            console.print(
                f"[dim]Rate limit (Agnes 1 request/min): waiting {interval:.0f}s "
                f"before shot {name}...[/dim]"
            )
            time.sleep(interval)
        console.print(f"[bold]▶ Shot {name}[/bold]")
        ok = _generate_shot(
            project_id,
            shot,
            ctx=ctx,
            root=root,
            # Flat lists carry no act grouping: scene 1, shot order = list order.
            scene=shot_runner.as_int(shot.get("scene"), 1),
            shot_number=shot_runner.as_int(shot.get("shot"), idx + 1),
        )
        slug = sanitize_filename(name.lower()) or f"shot-{idx + 1}"
        if ok:
            upsert_production_plan(
                project_id,
                root=root,
                plan_file=str(plan),
                asset_type=f"video-shot-{slug}",
                model=model,
                status="COMPLETED",
                source="brandly produce",
            )
            console.print(f"[green]✓ Shot {name} completed.[/green]")
        else:
            upsert_production_plan(
                project_id,
                root=root,
                plan_file=str(plan),
                asset_type=f"video-shot-{slug}",
                model=model,
                status="FAILED",
                source="brandly produce",
            )
            console.print(
                f"[red]✗ Shot {name} failed — stopping. Remaining shots stay "
                f"PENDING on the production plan; fix and re-run the same "
                f"command to resume.[/red]"
            )
            sys.exit(1)

    console.print(f"[green]✓ Production complete — see {plan_doc}[/green]")

    # Open UI if requested
    if open_ui:
        console.print("[dim]Opening timeline editor...[/dim]")
        try:
            import threading

            from brandly_cli.web import start_server
            def _open_ui():
                import time
                time.sleep(1)
                start_server(str(root), port=8765, open_browser=True)
            t = threading.Thread(target=_open_ui, daemon=True)
            t.start()
        except ImportError:
            console.print("[yellow]Web UI not available — install with: pip install brandly-cli[web][/yellow]")

@click.command(name="storyboard")
@click.argument("project_id")
@click.option(
    "--shots",
    "shots_file",
    required=True,
    help="Path to the shot list JSON used for the production run.",
)
@click.option(
    "--only",
    "only",
    multiple=True,
    help="Generate keyframes for only this shot id (repeatable).",
)
@click.option(
    "--model",
    default="agnes-image-2.5-flash",
    show_default=True,
    help="Agnes image model for keyframe generation (1-2 credits each).",
)
@click.option(
    "--interval",
    default=60.0,
    show_default=True,
    help="Seconds between image generations (Agnes 1 request/min).",
)
@click.option(
    "--no-gate",
    is_flag=True,
    default=False,
    help="Skip the offline composition pre-check (blank/undecodable frames).",
)
@click.option(
    "--character",
    default=None,
    help="Character identity anchor (same semantics as brandly produce).",
)
@click.pass_context
def storyboard(
    ctx: click.Context,
    project_id: str,
    shots_file: str,
    only: tuple[str, ...],
    model: str,
    interval: float,
    no_gate: bool,
    character: str | None,
) -> None:
    """Generate storyboard keyframes for each shot before spending video credits.

    Pipeline (issue #33): Reference Import → Storyboard (1-2 credits) →
    Gate → Video Generation (20 credits) → Gate. A keyframe that fails the
    offline composition check is flagged so composition/character errors are
    caught at image cost, not video cost. Approved keyframes are stored
    under .brandly/<project>/images/storyboard/ with the canonical
    Scene-XX-Shot-X-Y name and can be re-used as references for the video
    pass. The run is resumable: an approved keyframe skips regeneration
    (.brandly/<project>/docs/tmp/storyboard_progress.txt).
    """
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)

    root = _get_root(ctx)
    path = Path(shots_file)
    if not path.is_file():
        console.print(f"[red]Shot list not found: {path}[/red]")
        sys.exit(1)
    try:
        data = shot_runner.load_shots_file(path)
    except ValueError as e:
        console.print(f"[red]Invalid shot list: {e}[/red]")
        sys.exit(1)

    # v2-aware roots (issue #43).
    images_dir = layout.resolve_media_root(root, project_id, "images")
    storyboard_dir = images_dir / "storyboard"
    project_dir = layout.resolve_project_dir(root, project_id)
    shots = shot_runner.flatten_shots(data, images_dir, character=character)
    if only:
        shots = [s for s in shots if s.id in set(only)]
        console.print(f"[dim]--only: {len(shots)} of the shot list match(es) given ids[/dim]")

    progress_path = layout.docs_dir(project_dir, "tmp") / "storyboard_progress.txt"
    progress = shot_runner.ProgressLog(progress_path)
    done = progress.completed_ids(s.id for s in shots)
    pending = [s for s in shots if s.id not in done]

    from brandly_cli import quality_gate

    approved = 0
    for i, shot in enumerate(pending):
        if i > 0:
            console.print(f"[dim]rate limit: waiting {interval:.0f}s before {shot.id}...[/dim]")
            time.sleep(interval)
        keyframe_prompt = f"{shot.prompt}\n\n{STORYBOARD_INSTRUCTION}"
        console.print(f"[bold]▶ Keyframe for {shot.id} ({shot.clip_name})[/bold]")
        try:
            result = asyncio.run(generate_image(keyframe_prompt, model=model))
        except Exception as e:
            console.print(f"[red]✗ {shot.id}: generation failed: {e}[/red]")
            progress.record(shot.id, "FAIL", 1, f" generation error: {e}")
            continue
        url = result.get("url") or ""
        storyboard_dir.mkdir(parents=True, exist_ok=True)
        dest = storyboard_dir / shot.clip_name.replace(".mp4", ".jpg")
        try:
            asyncio.run(download_file(url, dest))
            saved = dest
        except Exception as e:
            console.print(f"[yellow]⚠ Could not save keyframe: {e}[/yellow]")
            saved = None
        if saved is None:
            progress.record(shot.id, "FAIL", 1, " no image returned (base64-only result)")
            continue
        if not no_gate:
            gate_result = asyncio.run(
                quality_gate.verify_element(
                    saved,
                    use_ai=False,
                    root=root,
                    project_id=project_id,
                    write_report=True,
                )
            )
            if gate_result.status == quality_gate.FAIL:
                console.print(
                    f"[red]✗ {shot.id}: composition gate FAIL — "
                    f"{gate_result.issues[0] if gate_result.issues else 'check report'} "
                    f"Fix references/prompt and re-run (keyframe not approved).[/red]"
                )
                progress.record(shot.id, "FAIL", 2, " composition gate failed")
                continue
            if gate_result.status == quality_gate.WARN:
                console.print(f"[yellow]⚠ {shot.id}: gate WARN — {gate_result.warnings[:1]}[/yellow]")
        progress.record(shot.id, "OK", 0)
        approved += 1
        console.print(f"[green]✓ {shot.id}: keyframe approved -> {saved.name}[/green]")

    if pending:
        console.print(
            f"[bold]Storyboard: {approved}/{len(pending)} keyframes approved "
            f"({len(done)} already done, {len(shots)} total)."
            f"Re-run to resume or regenerate.[/bold]"
        )
    else:
        console.print(
            f"[green]✓ All {len(shots)} shots have approved keyframes — "
            "proceed to video generation.[/green]"
        )

@click.command(name="migrate")
@click.argument("project_id")
@click.option(
    "--apply",
    is_flag=True,
    default=False,
    help="Actually move the folders (default: dry-run preview).",
)
@click.pass_context
def migrate(ctx: click.Context, project_id: str, apply: bool) -> None:
    """Restructure a project's folders into the v2 layout (issue #43).

    Documents/config stay in .brandly/<project>/; reference plates and
    storyboards move to pre-production/<project>/; generated clips and
    audio move to production/<project>/. Move-only: nothing is copied or
    deleted. Dry-run previews every move; --apply executes and stamps
    layout_version=2 so all layout-aware commands resolve the new roots.
    """
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)

    from brandly_cli import migrate as migrate_mod

    root = _get_root(ctx)
    result = migrate_mod.apply_migration(root, project_id, apply=apply)
    if not result.moves and not result.skipped:
        console.print(
            "[dim]No media folders to migrate — project already looks v2-clean "
            "(or has no generated assets yet).[/dim]"
        )
        if apply:
            migrate_mod._stamp_v2(root, project_id)
            console.print("[green]✓ layout_version=2 stamped on project.json.[/green]")
        return
    for plan in result.moves:
        marker = "✓" if apply else "→"
        console.print(f"[cyan]{marker}[/cyan] {plan.source.relative_to(root)}  →  {plan.dest.relative_to(root)}")
    for plan in result.skipped:
        console.print(f"[yellow]✗ skipped (destination exists): {plan.source.relative_to(root)}[/yellow]")
    if not apply:
        console.print(
            f"[bold]Dry run — {len(result.moves)} move(s) planned. "
            "Re-run with --apply to execute.[/bold]"
        )
    else:
        console.print(f"[green]✓ Migrated {len(result.moves)} folder(s) to the v2 layout.[/green]")
        if result.skipped:
            console.print(
                f"[yellow]⚠ {len(result.skipped)} move(s) skipped (destination "
                "exists) — resolve those manually.[/yellow]"
            )

@click.command()
@click.argument("project_id")
@click.pass_context
def progress(ctx: click.Context, project_id: str) -> None:
    """Show detailed progress of a project."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    pm = ProjectManager(root)
    proj = asyncio.run(pm.read(project_id))
    if not proj:
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)

    phases = getattr(proj, "phases", {})
    # Normalize phases: values may be PhaseResult models, plain dicts, or missing.
    phase_dicts: dict[str, dict[str, Any]] = {}
    for k, v in phases.items():
        if hasattr(v, "model_dump"):
            phase_dicts[k] = v.model_dump()  # type: ignore[union-attr]
        elif isinstance(v, dict):
            phase_dicts[k] = v
        else:
            phase_dicts[k] = {}
    total = len(PHASE_ORDER)
    completed = sum(1 for p in PHASE_ORDER if phase_dicts.get(p, {}).get("status") == "completed")
    overall_pct = round((completed / total) * 100) if total else 0

    from rich.console import Console as RConsole
    from rich.progress import BarColumn, Progress, TextColumn
    from rich.table import Table as RTable

    r = RConsole()
    r.print(f"\n[bold]Progress: {overall_pct}%[/bold] ({completed}/{total} phases)")
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as prog:
        task = prog.add_task("Pipeline", total=100)
        prog.update(task, completed=overall_pct)

    table = RTable(show_header=True, header_style="cyan")
    table.add_column("Phase", style="white")
    table.add_column("Status", style="green")
    table.add_column("Started", style="dim")
    table.add_column("Completed", style="dim")
    for phase in PHASE_ORDER:
        data = phase_dicts.get(phase, {})
        table.add_row(
            phase,
            data.get("status", "pending"),
            (data.get("started_at") or "")[:16],
            (data.get("completed_at") or "")[:16],
        )
    r.print(table)

@click.command()
@click.argument("project_id")
@click.pass_context
def cancel(ctx: click.Context, project_id: str) -> None:
    """Cancel a project."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    pm = ProjectManager(root)
    asyncio.run(pm.update(project_id, {"status": "cancelled", "updated_at": now_iso()}))
    console.print(f"[dim]Project {project_id} cancelled.[/dim]")

@click.command()
@click.argument("project_id")
@click.pass_context
def pause(ctx: click.Context, project_id: str) -> None:
    """Pause a project."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    pm = ProjectManager(root)
    asyncio.run(pm.update(project_id, {"status": "paused", "updated_at": now_iso()}))
    console.print(f"[dim]Project {project_id} paused.[/dim]")

@click.command()
@click.argument("project_id")
@click.pass_context
def resume(ctx: click.Context, project_id: str) -> None:
    """Resume a paused project."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    pm = ProjectManager(root)
    asyncio.run(pm.update(project_id, {"status": "running", "updated_at": now_iso()}))
    console.print(f"[green]Project {project_id} resumed.[/green]")

@click.command()
@click.argument("project_id")
@click.argument("base_prompt")
@click.option("--style", default="cinematic", help="Video style")
@click.option(
    "--model",
    default="agnes-video-2.5-flash",
    help="Model to use (2.5-flash is the current default)",
)
@click.option("-n", "--count", default=3, help="Number of variants to generate")
@click.option(
    "--interval",
    default=60.0,
    show_default=True,
    help="Seconds to wait between variant submissions (Agnes: 1 request/min).",
)
@click.option("--wait", is_flag=True, help="Wait for each generation to complete")
@click.option("--character", default=None, help="Character description for consistency")
@click.option("--reference-images", default=None, help="Comma-separated reference image URLs or local file paths")
@click.pass_context
def batch(
    ctx: click.Context,
    project_id: str,
    base_prompt: str,
    style: str,
    model: str,
    count: int,
    interval: float,
    wait: bool,
    character: str | None,
    reference_images: str | None,
) -> None:
    """Generate multiple video variants from a base prompt.

    Variants are submitted one at a time with a 60 s wait between requests
    (Agnes 1 request/minute rate limit). For multi-shot films use
    ``brandly produce`` instead — the production-plan-driven, shot-by-shot
    workflow.
    """
    async def _batch(ctx, project_id, base_prompt, style, model, count, interval, wait, character, reference_images):
        root = _get_root(ctx)
        if not is_valid_project_id(project_id):
            console.print("[red]Invalid project ID.[/red]")
            sys.exit(1)

        pm = ProjectManager(root)
        proj = await pm.read(project_id)
        if not proj:
            console.print(f"[red]Project not found: {project_id}[/red]")
            sys.exit(1)

        imgs: list[str] = []
        if reference_images:
            imgs = [u.strip() for u in reference_images.split(",") if u.strip()]

        console.print(f"[bold]Batch generating {count} variant{'s' if count > 1 else ''}[/bold]")
        console.print(f"  Project: {project_id}")
        console.print(f"  Style: {style} | Model: {model}")
        console.print()

        results = []
        for i in range(count):
            # 1 request/minute: wait between consecutive submissions.
            if i > 0:
                console.print(
                    f"[dim]Rate limit (Agnes 1 request/min): waiting {interval:.0f}s "
                    f"before variant {i + 1}...[/dim]"
                )
                time.sleep(interval)
            variant_prompt = f"{base_prompt}"
            if count > 1:
                variant_prompt += f"\n\nVariation {i + 1}: Unique camera angle and composition."
            console.print(f"[dim]Generating variant {i + 1}/{count}...[/dim]")
            try:
                # Parity with `brandly video` (issue #21 fix): cinematic style
                # keeps the cinematic preset, others get none. Applied here
                # (prompt layer) because providers no longer import style_presets.
                if style == "cinematic":
                    variant_prompt = apply_style_preset(variant_prompt, "cinematic", media="still")
                task = await create_video_task(
                    variant_prompt,
                    model=model,
                    duration=5,
                    aspect_ratio="16:9",
                    reference_images=imgs,
                )
            except Exception as e:
                console.print(
                    f"[yellow]⚠ Variant {i + 1} failed to submit ({e}); "
                    f"continuing with the next variant.[/yellow]"
                )
                results.append(
                    {
                        "variant": i + 1,
                        "status": "failed",
                        "error": str(e),
                        "created_one_at_a_time": True,
                    }
                )
                continue
            video_id = task.get("video_id", "")
            if wait and video_id:
                console.print("[dim]Waiting for completion...[/dim]")
                try:
                    result = await poll_video(video_id, max_wait_seconds=300)
                    task["url"] = result.get("url")
                    task["final_status"] = result.get("status")
                except TimeoutError:
                    task["final_status"] = "timeout"
            results.append(task)
            msg = (
                f"  {'✓' if task.get('url') else '↺'} "
                f"Variant {i + 1}: {task.get('status', 'pending')}"
            )
            console.print(msg)
            if task.get("url"):
                console.print(f"    URL: {task['url']}")

        console.print(
            f"\n[green]✓ Batch complete: "
            f"{sum(1 for r in results if r.get('url'))}/{count} generated[/green]"
        )
    asyncio.run(_batch(ctx, project_id, base_prompt, style, model, count, interval, wait, character, reference_images))

@click.command()
@click.argument("project_id")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def compare(ctx: click.Context, project_id: str, output: str) -> None:
    """Compare all generated assets in a project side by side."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    pm = ProjectManager(root)
    proj = asyncio.run(pm.read(project_id))
    if not proj:
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)

    # Collect all generated assets from phases
    phases = getattr(proj, "phases", {})
    assets: list[dict[str, Any]] = []
    for phase_name, phase_data in phases.items():
        output_data = phase_data.get("output")
        if not output_data:
            continue
        try:
            parsed = json.loads(output_data)
        except (json.JSONDecodeError, TypeError):
            continue
        videos = parsed.get("video_generations", [])
        for v in videos:
            v["_phase"] = phase_name
            assets.append(v)

    if not assets:
        console.print("[dim]No generated assets found for this project.[/dim]")
        return

    if output == "json":
        _print_json({"project": project_id, "asset_count": len(assets), "assets": assets})
        return

    table = Table(title=f"Generated Assets — {project_id} ({len(assets)} total)")
    table.add_column("#", style="dim", width=3)
    table.add_column("Phase", style="cyan", width=10)
    table.add_column("Model", style="dim", width=16)
    table.add_column("Status", style="green")
    table.add_column("URL", style="blue", max_width=40)
    table.add_column("Created", style="dim", width=16)
    for i, asset in enumerate(assets, 1):
        url = (asset.get("url") or "")[:40]
        table.add_row(
            str(i),
            asset.get("_phase", ""),
            asset.get("model", "")[:16],
            asset.get("status", "pending"),
            url or "—",
            (asset.get("created_at") or "")[:16],
        )
    console.print(table)

    # Show success rate
    completed = sum(1 for a in assets if a.get("url"))
    console.print(f"\n[dim]{completed}/{len(assets)} assets generated successfully[/dim]")



# ---------------------------------------------------------------------------
# Director orchestrator (moved from brandly_cli.director — caller layer that
# owns the provider/state calls; director.py is now a pure prompt composer)
# ---------------------------------------------------------------------------
def _director_shots_path(root: Path, project_id: str) -> Path:
    """Where the director's script phase writes the shot list the asset phase
    consumes (mirrors the timeline editor's ``.brandly/<id>/shots.json``)."""
    return layout.resolve_project_dir(root, project_id) / "shots.json"



def _scene_clip_paths(
    root: Path, project_id: str, manifest: dict[str, Any]
) -> list[Path]:
    """Ordered scene clip paths from the manifest (the re_edit stitch input).

    Clips live under ``<videos root>/<folder>/<clip>`` exactly where
    ``brandly produce`` writes them; folders default to ``scenes``.
    """
    videos_root = layout.resolve_media_root(root, project_id, "videos")
    clips: list[Path] = []
    for entry in manifest.get("scenes", []):
        for shot in entry.get("shots", []):
            clips.append(
                videos_root
                / str(shot.get("folder") or "scenes")
                / str(shot["clip"])
            )
    return clips

# ---------------------------------------------------------------------------
# Phase handoffs (G7 PR E) — per-phase dispatch contracts for agents
# ---------------------------------------------------------------------------

#: Static dispatch contract per phase: what a phase reads, what it must
#: produce, and which gate verifies it. Statuses, errors, and costs are
#: filled in per-project by :func:`phase_handoffs`; this table never changes.
PHASE_HANDOFF_SPECS: dict[str, dict[str, Any]] = {
    "init": {
        "inputs": ["product name", "product idea / brief"],
        "outputs": [".brandly/<project>/project.json", "AGENTS.md (project root)"],
        "gate": {
            "command": "brandly status <project_id>",
            "exit_codes": "0 = project exists",
        },
    },
    "trends": {
        "inputs": ["product brief (project.json)", "web research"],
        "outputs": ["docs/plan/trends.md"],
        "gate": {
            "command": "brandly status <project_id>",
            "exit_codes": "0 = phase recorded; docs/plan/trends.md non-empty",
        },
    },
    "concept": {
        "inputs": ["docs/plan/trends.md"],
        "outputs": ["docs/plan/concept.md", "moodboard assets"],
        "gate": {
            "command": "brandly status <project_id>",
            "exit_codes": "0 = phase recorded; concept artifact exists",
        },
    },
    "script": {
        "inputs": ["docs/plan/concept.md", "moodboard assets"],
        "outputs": ["shots.json"],
        "gate": {
            "command": "brandly status <project_id>",
            "exit_codes": "0 = phase recorded; shots.json written",
        },
    },
    "asset": {
        "inputs": ["shots.json", "reference images", "docs/plan/scenes.json"],
        "outputs": ["docs/plan/scenes.json", "scene clip files in the media store"],
        "gate": {
            "command": "brandly gate <project_id> --all-scenes --json",
            "exit_codes": "0 = pass, 1 = warn, 2 = fail",
        },
    },
    "audio": {
        "inputs": ["scenes.json", "shots.json"],
        "outputs": ["audio assets (music, SFX, voiceover) in the media store"],
        "gate": {
            "command": "brandly status <project_id>",
            "exit_codes": "0 = phase recorded; audio present (duration ~= scenes)",
        },
    },
    "re_edit": {
        "inputs": ["scene clips", "audio assets"],
        "outputs": ["videos/final.mp4"],
        "gate": {
            "command": "brandly stitch <clips...> --output videos/final.mp4",
            "exit_codes": "0 = stitched; clip count matches scenes.json",
        },
    },
    "validate": {
        "inputs": ["videos/final.mp4"],
        "outputs": ["scene-gate verdicts (all must pass)"],
        "gate": {
            "command": "brandly gate <project_id> --all-scenes --json",
            "exit_codes": "0 = pass (advance); 1/2 = re_edit, do not advance",
        },
    },
    "publish": {
        "inputs": ["videos/final.mp4", "gate verdicts", "brandly approve <id> <phase>"],
        "outputs": ["<project>/export/ platform deliverables"],
        "gate": {
            "command": "brandly export-platforms <project_id>",
            "exit_codes": "0 = deliverables written for every target platform",
        },
    },
    "done": {
        "inputs": ["all real-phase outputs (completed pipeline)"],
        "outputs": ["pipeline complete"],
        "gate": {"command": "None", "exit_codes": "terminal state — nothing to verify"},
    },
}


def phase_costs(style: str, shot_count: int) -> dict[str, int]:
    """Per-phase credit estimates — the ``estimate`` math, minus the console.

    Shared by the ``brandly estimate`` command and :func:`phase_handoffs`
    (single formula, one home). Unknown styles/shots fall back to the
    ``cinematic``/5-shot defaults so an agent always gets a number.
    """
    cinematic_cost: int = STYLE_COSTS["cinematic"]
    style_cost = STYLE_COSTS[style] if style in STYLE_COSTS else cinematic_cost
    shot_cost = SHOT_COSTS.get(shot_count, SHOT_COSTS[5])
    total_base = style_cost + shot_cost
    return {
        "init": 0,
        "trends": 10,
        "concept": round(total_base * 0.15),
        "script": round(total_base * 0.20),
        "asset": round(total_base * 0.25),
        "audio": round(total_base * 0.15),
        "re_edit": 20,
        "validate": 10,
        "publish": 5,
    }


def _phase_status(project: Any, phase: str) -> tuple[str, str | None]:
    """Return ``(status, error)`` for one phase from ``project.phases``."""
    entry = project.phases.get(phase)
    if isinstance(entry, Mapping):
        return str(entry.get("status") or "pending"), (
            str(entry["error"]) if entry.get("error") else None
        )
    status = str(getattr(entry, "status", "pending") or "pending")
    error = getattr(entry, "error", None)
    return status, (str(error) if error else None)


def phase_handoffs(root: Path, project_id: str) -> dict[str, Any]:
    """Data-only per-phase dispatch contracts for orchestrating agents (G7 PR E).

    Same sources as :func:`director_plan` — ``PHASE_ORDER`` for ordering, the
    project's ``phases`` map for status/error, ``current_phase`` for the resume
    point — plus :data:`PHASE_HANDOFF_SPECS` (inputs/outputs/gate) and
    :func:`phase_costs` (per-phase ``est_cost`` from the project's
    style/shot_count). Read-only: derives everything, writes nothing.

    ``next_command`` mirrors ``director_plan`` exactly (``brandly init`` before
    a project exists, ``None`` when complete, ``brandly run <id> --execute
    --yes`` otherwise).
    """
    handoffs: list[dict[str, Any]] = [
        {
            "id": phase,
            "status": "pending",
            "error": None,
            "inputs": list(PHASE_HANDOFF_SPECS[phase]["inputs"]),
            "outputs": list(PHASE_HANDOFF_SPECS[phase]["outputs"]),
            "gate": dict(PHASE_HANDOFF_SPECS[phase]["gate"]),
            "next_command": f"brandly run {project_id} --execute --yes",
            "est_cost": 0,
        }
        for phase in PHASE_ORDER
    ]
    result: dict[str, Any] = {
        "project_id": project_id,
        "current": None,
        "next_command": "brandly init",
        "handoffs": handoffs,
    }
    project = asyncio.run(ProjectManager(root).read(project_id))
    if project is None:
        return result

    costs = phase_costs(str(project.style), int(project.shot_count or 5))
    by_id = {h["id"]: h for h in handoffs}
    for phase in PHASE_ORDER:
        status, error = _phase_status(project, phase)
        by_id[phase]["status"] = status
        by_id[phase]["error"] = error
        by_id[phase]["est_cost"] = costs.get(phase, 0)

    plan = director_plan(root, project_id)
    result["current"] = plan["current"]
    result["next_command"] = plan["next_command"]
    for h in handoffs:
        h["next_command"] = f"brandly run {project_id} --execute --yes"
    return result


def director_plan(root: Path, project_id: str | None = None) -> dict[str, Any]:
    """Data-only orchestrator plan for ``brandly director`` (G2 PR D).

    Single source of truth: ``PHASE_ORDER`` (phase order), the project's
    ``phases`` map (per-phase status) and ``current_phase`` (the resume
    point ``Director.run_pipeline`` picks up).  No rich rendering here —
    agents consume the dict; the command layer renders it.

    ``next_command`` is the exact resume command: ``brandly init`` before a
    project exists, ``None`` when the pipeline is complete, and
    ``brandly run <id> --execute --yes`` from any incomplete state
    (a failed or in-progress phase is retried on re-run).
    """
    plan: dict[str, Any] = {
        "project_id": project_id,
        "phases": list(PHASE_ORDER),
        "phases_status": dict.fromkeys(PHASE_ORDER, "pending"),
        "completed": [],
        "current": None,
        "next_command": "brandly init",
    }
    if project_id is None:
        return plan
    project = asyncio.run(ProjectManager(root).read(project_id))
    if project is None:
        return plan

    statuses: dict[str, str] = {}
    completed: list[str] = []
    for phase in PHASE_ORDER:
        entry = project.phases.get(phase)
        if isinstance(entry, Mapping):
            status = str(entry.get("status") or "pending")
        else:
            status = str(getattr(entry, "status", "pending") or "pending")
        statuses[phase] = status
        if status == "completed":
            completed.append(phase)
    plan["phases_status"] = statuses
    plan["completed"] = completed

    real_phases = PHASE_ORDER[1:-1]  # everything between init and done
    current_phase = str(project.current_phase)
    if current_phase not in PHASE_ORDER or current_phase == "done" or all(
        statuses[p] == "completed" for p in real_phases
    ):
        # Complete (or untracked state): nothing left to resume.
        plan["next_command"] = None
        return plan

    # "init" is a bookkeeping marker — the first real step is "trends".
    plan["current"] = "trends" if current_phase == "init" else current_phase
    plan["next_command"] = f"brandly run {project_id} --execute --yes"
    return plan


class DirectorConfig:
    """Configuration for the Director orchestrator."""

    def __init__(
        self,
        root: str | Path,
        default_style: str = "cinematic",
        default_budget: int = 500,
        default_shots: int = 5,
    ) -> None:
        self.root = Path(root)
        self.default_style = default_style
        self.default_budget = default_budget
        self.default_shots = default_shots
        self.pm = ProjectManager(self.root)
        self.ct = CostTracker(self.root / ".brandly")
        self.mem = UserPreferences(self.root)


class Director:
    """Autonomous video production orchestrator."""

    def __init__(self, config: DirectorConfig) -> None:
        self.cfg = config

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------

    async def start_project(
        self,
        name: str,
        idea: str,
        *,
        style: str | None = None,
        budget: int | None = None,
        shots: int | None = None,
        platforms: list[str] | None = None,
    ) -> str:
        """Create a new project and return its ID."""
        s = style or self.cfg.default_style
        b = budget or self.cfg.default_budget
        sh = shots or self.cfg.default_shots
        pts = platforms or ["tiktok", "instagram"]

        if s not in VIDEO_STYLES:
            raise ValueError(f"Invalid style '{s}'. Choices: {', '.join(VIDEO_STYLES)}")
        if sh < 3 or sh > 10:
            raise ValueError("Shots must be between 3 and 10.")

        from brandly_cli.types import ProjectData

        proj = ProjectData(
            id=generate_project_id(),
            name=name,
            description=idea,
            style=s,
            shot_count=sh,
            budget=b,
            target_platforms=pts,
        )
        await self.cfg.pm.create(proj)
        return proj.id

    async def get_status(self, project_id: str) -> dict[str, Any]:
        """Return project status summary."""
        proj = await self.cfg.pm.read(project_id)
        if not proj:
            raise ValueError(f"Project not found: {project_id}")
        return {
            "id": proj.id,
            "name": proj.name,
            "status": proj.status,
            "current_phase": proj.current_phase,
            "style": proj.style,
            "shot_count": proj.shot_count,
            "budget": proj.budget,
            "spent": proj.spent,
            "remaining": proj.budget - proj.spent,
            "target_platforms": proj.target_platforms,
            "created_at": proj.created_at,
            "updated_at": proj.updated_at,
        }

    async def estimate(
        self,
        style: str,
        shots: int,
    ) -> dict[str, Any]:
        """Estimate cost for a given style and shot count."""
        if style not in STYLE_COSTS:
            raise ValueError(f"Invalid style '{style}'")
        if shots < 3 or shots > 10:
            raise ValueError("Shots must be between 3 and 10.")

        style_cost = STYLE_COSTS[style]
        shot_cost = SHOT_COSTS.get(shots, 0)
        total_base = style_cost + shot_cost
        overhead = 60

        return {
            "style": style,
            "shot_count": shots,
            "style_cost": style_cost,
            "shot_cost": shot_cost,
            "total_base": total_base,
            "overhead": overhead,
            "total_estimate": total_base + overhead,
        }

    # ------------------------------------------------------------------
    # Image generation
    # ------------------------------------------------------------------

    async def generate_image(
        self,
        project_id: str,
        prompt: str,
        *,
        model: str = "agnes-image-2.1-flash",
        size: str = "2K",
        ratio: str = "16:9",
        style_preset: StylePreset | None = None,
        n: int = 1,
    ) -> dict[str, Any]:
        """Generate an image and store result in project."""
        enhanced = apply_style_preset(prompt, style_preset, media="still") if style_preset else prompt
        is_ark = model.startswith("seedream")

        if is_ark:
            result = await ark_generate_image(enhanced, model=model, size=size, n=n)
            urls = result.get("urls", [])
            url = urls[0] if urls else None
        else:
            result = await generate_image(enhanced, model=model, size=size, ratio=ratio)
            url = result.get("url")

        proj = await self.cfg.pm.read(project_id)
        if proj:
            analysis = proj.image_analysis or {}
            analysis.update(
                {
                    "generated_url": url,
                    "prompt": prompt,
                    "enhanced_prompt": enhanced,
                    "style_preset": style_preset,
                    "model": model,
                    "generated_at": _now_iso(),
                }
            )
            await self.cfg.pm.update(project_id, {"image_analysis": analysis})

        return result

    # ------------------------------------------------------------------
    # Video generation
    # ------------------------------------------------------------------

    async def generate_video(
        self,
        project_id: str,
        prompt: str,
        *,
        model: str = DEFAULT_AGNES_VIDEO_MODEL,
        mode: str = "auto",
        duration: int = 5,
        aspect_ratio: str = "16:9",
        style: str = "cinematic",
        character: str | None = None,
        reference_images: list[str] | None = None,
        first_frame: str | None = None,
        last_frame: str | None = None,
        wait: bool = False,
        max_wait: int = 300,
    ) -> dict[str, Any]:
        """Generate a video with enhanced prompt engineering and character consistency.

        ``mode="auto"`` (default) infers the mode from the inputs:
        keyframe when a start/end frame is provided, reference when
        reference images are provided, otherwise text.
        """
        # Enhance prompt with style and consistency hints
        enhanced = build_enhanced_video_prompt(
            prompt, style, character=character, reference_images=reference_images
        )

        is_ark = model.startswith("seedance")
        if is_ark:
            # Legacy parity: the Ark provider used to apply the "cinematic"
            # preset internally; providers no longer touch the prompt layer.
            enhanced = apply_style_preset(enhanced, "cinematic")
            task = await ark_create_video_task(
                enhanced,
                model=model,
                duration=duration,
                aspect_ratio=aspect_ratio,
                reference_images=reference_images,
            )
            video_id = task.get("task_id") or ""
        else:
            task = await create_video_task(
                enhanced,
                model=model,
                mode=mode,
                duration=duration,
                aspect_ratio=aspect_ratio,
                first_frame=first_frame,
                last_frame=last_frame,
                reference_images=reference_images,
            )
            video_id = task["video_id"]

        if wait and video_id:
            if is_ark:
                result = await ark_poll_video(video_id, max_wait_seconds=max_wait)
            else:
                result = await poll_video(video_id, max_wait_seconds=max_wait, model_name=model)
            task["url"] = result.get("url")
            task["final_status"] = result.get("status")

        # Persist to project phase
        proj = await self.cfg.pm.read(project_id)
        if proj:
            phases = dict(getattr(proj, "phases", {}))
            current = proj.current_phase
            if current not in phases:
                phases[current] = {"status": "pending"}
            phase_out = json.loads(phases[current].get("output") or "{}")
            videos = phase_out.setdefault("video_generations", [])
            videos.append(
                {
                    "task_id": task.get("id"),
                    "video_id": video_id,
                    "model": model,
                    "mode": task.get("mode") or mode,
                    "prompt": prompt,
                    "url": task.get("url"),
                    "status": task.get("status"),
                    "created_at": _now_iso(),
                }
            )
            phases[current]["output"] = json.dumps(phase_out)
            await self.cfg.pm.update(project_id, {"phases": phases})

        return task

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    async def generate_music(
        self,
        prompt: str,
        *,
        model: str = "google-lyria",
        duration: int = 30,
        instrumental: bool = True,
    ) -> dict[str, Any]:
        """Generate background music."""
        return await generate_music(
            prompt, model=model, duration_seconds=duration, instrumental=instrumental
        )

    async def generate_tts(
        self,
        text: str,
        *,
        model: str = "eleven_v3",
        voice_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate voiceover."""
        return await generate_tts(
            text, model=model, voice_id=voice_id or "English_Insightful_Speaker"
        )

    # ------------------------------------------------------------------
    # Pipeline orchestration
    # ------------------------------------------------------------------

    async def run_phase(self, project_id: str, phase: str) -> dict[str, Any]:
        """Advance a single pipeline phase by dispatching real work.

        Fails closed: a worker ``error`` payload or exception marks the
        phase ``failed`` and leaves ``current_phase`` untouched, so a
        re-run resumes at the failed phase.
        """
        if phase not in PHASE_ORDER:
            raise ValueError(f"Invalid phase '{phase}'")

        proj = await self.cfg.pm.read(project_id)
        if not proj:
            raise ValueError(f"Project not found: {project_id}")
        if proj.status == "cancelled":
            return {"error": "Project cancelled", "phase": phase}
        if proj.status == "paused":
            return {"error": "Project paused", "phase": phase}

        # Mark phase running
        phases = dict(getattr(proj, "phases", {}))
        started_at = _now_iso()
        phases[phase] = {"status": "running", "started_at": started_at}
        await self.cfg.pm.update(project_id, {"phases": phases, "status": "running"})

        # Dispatch to the real phase worker. A phase that cannot do its
        # work truthfully reports an error instead of fabricating success.
        try:
            result = await self._run_phase_real(phase, proj)
        except Exception as e:
            result = {"error": f"{type(e).__name__}: {e}"}

        phases = dict(getattr(proj, "phases", {}))
        if "error" in result:
            phases[phase] = {
                "status": "failed",
                "started_at": started_at,
                "completed_at": _now_iso(),
                "error": result["error"],
            }
            await self.cfg.pm.update(
                project_id, {"phases": phases, "status": "failed"}
            )
            return {"phase": phase, "error": result["error"]}

        # Mark phase completed
        phases[phase] = {
            "status": "completed",
            "started_at": started_at,
            "completed_at": _now_iso(),
            "output": json.dumps(result),
        }
        idx = PHASE_ORDER.index(phase)
        next_phase = PHASE_ORDER[idx + 1] if idx < len(PHASE_ORDER) - 1 else "done"
        updates: dict[str, Any] = {"phases": phases, "current_phase": next_phase}
        if phase == "done":
            updates["status"] = "completed"
        await self.cfg.pm.update(project_id, updates)

        return {"phase": phase, "next_phase": next_phase, "result": result}

    async def _run_phase_real(self, phase: str, proj: Any) -> dict[str, Any]:
        """Execute the real work for a pipeline phase."""
        from brandly_cli.constants import SHOT_COSTS
        from brandly_cli.constants import STYLE_COSTS as SC

        style_cost = SC.get(proj.style, 250)
        shot_cost = SHOT_COSTS.get(proj.shot_count, 30)
        base = style_cost + shot_cost

        if phase == "init":
            return {"message": "Project initialized"}

        if phase == "trends":
            from brandly_cli.trends import research_trends
            results = await research_trends("commercial")
            return {
                "trending_formats": results.get("trending_formats", [])[:3],
                "recommended_style": proj.style,
            }

        if phase == "concept":
            return {
                "error": (
                    "concept phase is not implemented yet — derive the concept "
                    "from the project brief with an agent, then continue the "
                    "pipeline"
                )
            }

        if phase == "script":
            from brandly_cli.video_prompts import CAMERA_MOVES, build_single_shot_prompt

            cameras = list(CAMERA_MOVES)
            shot_duration = 5  # within Agnes' single-segment clamp window
            shot_list: list[dict[str, Any]] = []
            for i in range(1, proj.shot_count + 1):
                shot_list.append(
                    {
                        "id": f"shot-{i}",
                        "prompt": build_single_shot_prompt(
                            subject=proj.name or "product",
                            action="demonstrates key features",
                            environment="clean studio setting",
                            style=proj.style,
                            camera=cameras[(i - 1) % len(cameras)],
                            duration=shot_duration,
                        ),
                        "duration": shot_duration,
                        "style": proj.style,
                        # G3 scene-id inputs: one scene, ordered shots —
                        # scenes.json derives S01… from these at produce time.
                        "scene": 1,
                        "shot": i,
                    }
                )
            shots_path = _director_shots_path(self.cfg.root, proj.id)
            shots_path.parent.mkdir(parents=True, exist_ok=True)
            shots_path.write_text(
                json.dumps(shot_list, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return {
                "shots_path": str(shots_path),
                "shots": len(shot_list),
                "duration": len(shot_list) * shot_duration,
            }

        if phase == "asset":
            shots_path = _director_shots_path(self.cfg.root, proj.id)
            if not shots_path.is_file():
                return {
                    "error": (
                        f"shot list not found: {shots_path} — run the script "
                        "phase first so it writes shots.json "
                        "(`brandly run <id> --execute --until script`)"
                    )
                }
            try:
                shots_data = shot_runner.load_shots_file(shots_path)
            except (ValueError, OSError) as e:
                return {"error": f"invalid shot list {shots_path}: {e}"}

            # Goal 3: register the scene manifest BEFORE any generation
            # begins — scenes.json is the source of truth for the scene gate.
            manifest = scenes.write_scenes(proj.id, shots_data, root=self.cfg.root)

            # Drive the real produce runner (shot_runner): Scene-XX-Shot-X-Y
            # naming, identity anchors, retries, production-plan rows, cost
            # recording — never a private generation loop.
            ctx = click.Context(cli, obj={"root": str(self.cfg.root)})
            try:
                _run_produce_runner(
                    ctx,
                    proj.id,
                    shots_data,
                    self.cfg.root,
                    shot_runner.DEFAULT_INTERVAL,
                    False,  # no_auto_refs
                    None,  # character
                    False,  # allow_referenceless
                    600,  # max_wait
                    (),  # only
                    0,  # max_shots
                    retries=0,
                )
                rc = 0
            except SystemExit as exc:
                code = exc.code
                rc = code if isinstance(code, int) else (0 if code is None else 1)
            if rc != 0:
                return {
                    "error": (
                        f"asset generation stopped on a failed shot (runner "
                        f"exit {rc}) — fix the shot and re-run to resume; "
                        "completed shots are recorded in "
                        "docs/tmp/produce_progress.txt"
                    )
                }
            return {
                "shots": sum(len(s["shots"]) for s in manifest["scenes"]),
                "scenes": len(manifest["scenes"]),
                "runner": "brandly produce (shot_runner)",
            }

        if phase == "audio":
            music = await self.generate_music("upbeat corporate", duration=30)
            return {
                "music_task": music,
                "estimated_credits": round(base * 0.15),
            }

        if phase == "re_edit":
            scene_manifest = scenes.load_scenes(proj.id, root=self.cfg.root)
            if scene_manifest is None:
                return {
                    "error": (
                        f"scene manifest not found: "
                        f"{scenes.scenes_path(proj.id, root=self.cfg.root)} — run "
                        "the asset phase first (`brandly run <id> --execute "
                        "--until asset`) and re-run to resume"
                    )
                }
            clips = _scene_clip_paths(Path(self.cfg.root), proj.id, scene_manifest)
            missing = [c for c in clips if not (c.is_file() and c.stat().st_size > 0)]
            if missing:
                return {
                    "error": (
                        f"re_edit cannot stitch: {len(missing)} scene clip(s) "
                        f"missing ({', '.join(str(c) for c in missing)}) — "
                        "generate them with the asset phase "
                        "(`brandly run <id> --execute --until asset`) and "
                        "re-run to resume"
                    )
                }
            if not clips:
                return {
                    "error": (
                        "re_edit cannot stitch: the scene manifest lists no shots"
                    )
                }
            videos_root = layout.resolve_media_root(
                Path(self.cfg.root), proj.id, "videos"
            )
            output = videos_root / "final.mp4"
            result = await stitch.stitch_videos(
                clips, output, root=Path(self.cfg.root)
            )
            if "error" in result:
                return {"error": f"stitch failed: {result['error']}"}
            return {
                "output": str(output),
                "clips": len(clips),
                "duration_seconds": result.get("duration_seconds", 0.0),
            }

        if phase == "validate":
            from brandly_cli import quality_gate

            scene_manifest = scenes.load_scenes(proj.id, root=self.cfg.root)
            if scene_manifest is None:
                return {
                    "error": (
                        f"scene manifest not found: "
                        f"{scenes.scenes_path(proj.id, root=self.cfg.root)} — run "
                        "the asset phase first (`brandly run <id> --execute "
                        "--until asset`) and re-run to resume"
                    )
                }
            root_path = Path(self.cfg.root)

            def gate_runner(clip: Path) -> str:
                # Deterministic pre-checks only (use_ai=False) — the same
                # runner the ``brandly gate --all-scenes`` CLI uses. The
                # pipeline is async, so the sync QualityRunner contract is
                # served with a fresh event loop per clip.
                return asyncio.run(
                    quality_gate.verify_element(
                        clip,
                        use_ai=False,
                        root=root_path,
                        project_id=proj.id,
                        write_report=False,
                    )
                ).status

            # evaluate_all is sync and calls the gate runner inline, so run
            # the whole gate off the event loop (mirrors the gate CLI).
            report = await asyncio.to_thread(
                lambda: scenes.evaluate_all(
                    proj.id, root=root_path, gate_runner=gate_runner
                )
            )
            if report["verdict"] != "pass":
                bad = [s for s in report["scenes"] if s["verdict"] != "pass"]
                detail = "; ".join(f"{s['id']}={s['verdict']}" for s in bad)
                return {
                    "error": (
                        f"scene gate {report['verdict'].upper()} ({detail}) — "
                        "fix the flagged scene(s) with "
                        f"`brandly gate {proj.id} --all-scenes` and re-run to "
                        "resume"
                    )
                }
            return {
                "verdict": report["verdict"],
                "scenes": len(report["scenes"]),
            }

        if phase == "publish":
            from brandly_cli import export_platforms

            root_path = Path(self.cfg.root)
            videos_root = layout.resolve_media_root(root_path, proj.id, "videos")
            source = videos_root / "final.mp4"
            if not source.is_file():
                found = next(videos_root.rglob("*.mp4"), None) if videos_root.is_dir() else None
                if found is None:
                    return {
                        "error": (
                            f"no video to publish under {videos_root} — run the "
                            "re_edit phase first so it stitches a final video "
                            "(and the validate phase can pass), then re-run to "
                            "resume"
                        )
                    }
                source = found
            out_dir = layout.resolve_project_dir(root_path, proj.id) / "export"
            platforms = ("tiktok", "youtube_standard")
            outputs: list[dict[str, Any]] = []
            for platform in platforms:
                result = await export_platforms.export_for_platform(
                    source, platform, out_dir, root=root_path
                )
                if "error" in result:
                    return {
                        "error": (
                            f"export to {platform} failed: {result['error']} — "
                            "re-run the publish phase to resume (completed "
                            "exports are kept)"
                        )
                    }
                outputs.append({"platform": platform, "output_path": result["output_path"]})
            return {
                "source": str(source),
                "platforms": [o["platform"] for o in outputs],
                "outputs": [o["output_path"] for o in outputs],
            }

        if phase == "done":
            return {"message": "Pipeline complete!"}

        return {"message": f"Phase {phase} completed"}

    async def run_pipeline(
        self, project_id: str, *, until: str | None = None
    ) -> dict[str, Any]:
        """Run remaining phases sequentially, resuming from ``current_phase``.

        Stops after ``until`` completes (inclusive), or at the first failed
        phase — fail-closed: a failed phase never advances the pipeline.
        """
        if until is not None and until not in PHASE_ORDER:
            raise ValueError(f"Invalid phase '{until}'")
        proj = await self.cfg.pm.read(project_id)
        if not proj:
            raise ValueError(f"Project not found: {project_id}")

        current_idx = PHASE_ORDER.index(str(proj.current_phase))  # type: ignore[arg-type]
        stop_idx = PHASE_ORDER.index(until) if until else len(PHASE_ORDER) - 1  # type: ignore[arg-type]
        results = []
        for phase in PHASE_ORDER[current_idx : stop_idx + 1]:
            r = await self.run_phase(project_id, phase)
            results.append(r)
            if "error" in r:
                return {
                    "project_id": project_id,
                    "phases_run": [x["phase"] for x in results],
                    "failed_phase": phase,
                    "error": r["error"],
                    "results": results,
                }

        return {
            "project_id": project_id,
            "phases_run": [r["phase"] for r in results],
            "final_phase": results[-1]["phase"] if results else "none",
            "results": results,
        }

    # ------------------------------------------------------------------
    # Dashboard / progress
    # ------------------------------------------------------------------

    async def get_progress(self, project_id: str) -> dict[str, Any]:
        """Return detailed progress information."""
        proj = await self.cfg.pm.read(project_id)
        if not proj:
            raise ValueError(f"Project not found: {project_id}")

        phases = getattr(proj, "phases", {})
        total = len(PHASE_ORDER)
        completed = sum(1 for p in PHASE_ORDER if phases.get(p, {}).get("status") == "completed")
        overall_pct = round((completed / total) * 100) if total else 0

        current = proj.current_phase
        current_data = phases.get(current, {})
        time_in_phase: str | None = None
        if current_data.get("started_at"):
            from datetime import datetime, timezone

            elapsed = int(
                (
                    datetime.now(timezone.utc).timestamp()
                    - datetime.fromisoformat(current_data["started_at"]).timestamp()
                )
                * 1000
            )
            mins, secs = divmod(elapsed // 1000, 60)
            time_in_phase = f"{mins}m {secs}s"

        return {
            "project_id": project_id,
            "project_status": proj.status,
            "current_phase": current,
            "overall_percent": overall_pct,
            "completed_phases": completed,
            "total_phases": total,
            "time_in_current_phase": time_in_phase,
            "phase_statuses": {p: phases.get(p, {}).get("status", "pending") for p in PHASE_ORDER},
        }




# Keyframe instruction for storyboard shots (moved out of cli.py — P2-8).
STORYBOARD_INSTRUCTION = (
    "[KEYFRAME] Render a single still frame capturing this exact moment — "
    "composition, lighting, and character placement exactly as directed. "
    "This frame is a storyboard keyframe for pre-visualizing the shot."
)


@click.group(name="scenes")
def scenes_group() -> None:
    """Inspect the scene manifest (docs/plan/scenes.json) — Goal 3."""


@scenes_group.command(name="status")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Emit the raw matrix as JSON")
@click.pass_context
def scenes_status(ctx: click.Context, project_id: str, as_json: bool) -> None:
    """Report the per-scene completeness matrix (expected/present/missing/stale)."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    try:
        report = scenes.status(project_id, root=root)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        console.print(
            "[dim]Run `brandly produce <project-id> --shots <file>` to create "
            "the scene manifest.[/dim]"
        )
        sys.exit(1)
    if as_json:
        # Plain print: console.print would wrap/mangle long JSON lines.
        print(json.dumps(report, indent=2))
    else:
        _print_scene_report(report)


def register(cli) -> None:
    cli.add_command(init)
    cli.add_command(status)
    cli.add_command(list_projects)
    cli.add_command(run)
    cli.add_command(director)
    cli.add_command(plan)
    cli.add_command(approve)
    cli.add_command(estimate)
    cli.add_command(produce)
    cli.add_command(storyboard)
    cli.add_command(migrate)
    cli.add_command(progress)
    cli.add_command(cancel)
    cli.add_command(pause)
    cli.add_command(resume)
    cli.add_command(batch)
    cli.add_command(compare)
    cli.add_command(timeline)
    cli.add_command(scenes_group)


@click.command()
@click.option("--port", "-p", default=8765, help="Port to serve the editor on (default: 8765)")
@click.option("--no-browser", is_flag=True, help="Do not open browser automatically")
@click.pass_context
def timeline(ctx: click.Context, port: int, no_browser: bool) -> None:
    """Open the visual timeline editor in a browser.

    Lists all .brandly/ projects and lets you view/edit the timeline
    for any project with a generated shot list.

    If no project ID is given, the UI shows a project picker.
    """
    try:
        from brandly_cli.web import start_server
    except ImportError as e:
        console.print(f"[red]Web UI dependency not installed: {e}[/red]")
        console.print("[yellow]Install with: pip install brandly-cli[web][/yellow]")
        sys.exit(1)

    root = str(_get_root(ctx))
    console.print(f"[dim]Starting timeline editor on http://127.0.0.1:{port}[/dim]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    start_server(root, port=port, open_browser=not no_browser)
