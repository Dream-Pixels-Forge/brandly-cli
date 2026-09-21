"""Validate command for brandly-cli."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from brandly_cli import __version__, layout, shot_runner
from brandly_cli.agent_tools import get_builtin_tools
from brandly_cli.agnes_client import (
    agent_tool_loop,
    cancel_job,
    create_video_task,
    generate_image,
    list_jobs,
    list_text_models,
    poll_video,
)
from brandly_cli.ark_client import (
    cancel_job as ark_cancel_job,
)
from brandly_cli.ark_client import (
    create_video_task as ark_create_video_task,
)
from brandly_cli.ark_client import (
    generate_image as ark_generate_image,
)
from brandly_cli.ark_client import (
    list_jobs as ark_list_jobs,
)
from brandly_cli.ark_client import (
    poll_video as ark_poll_video,
)
from brandly_cli.audio_client import generate_music, generate_tts, list_voices
from brandly_cli.constants import (
    PHASE_ORDER,
    PROVIDER_RATE_LIMITS,
    SHOT_COSTS,
    STYLE_COSTS,
    STYLE_PRESET_OPTIONS,
    VIDEO_STYLES,
    get_all_models,
    get_model_info,
)
from brandly_cli.cost_tracker import CostTracker
from brandly_cli.director import get_director_prompt
from brandly_cli.edit import (
    add_subtitles,
    change_speed,
    concatenate_videos,
    extract_audio,
    get_video_info,
    resize_video,
    trim_video,
)
from brandly_cli.memory import UserPreferences
from brandly_cli.minimax_client import (
    create_video_task as minimax_create_video,
)
from brandly_cli.minimax_client import (
    generate_image as minimax_generate_image,
)
from brandly_cli.minimax_client import (
    list_jobs as minimax_list_jobs,
)
from brandly_cli.minimax_client import (
    poll_video as minimax_poll_video,
)
from brandly_cli.project_manager import ProjectManager
from brandly_cli.style_presets import apply_style_preset
from brandly_cli.sync import SYNC_HANDLERS, TOOLS, detect_tools, sync_keys
from brandly_cli.types import PhaseResult
from brandly_cli.utils import (
    _read_production_plan_rows,
    download_file,
    ellipsize,
    generate_project_id,
    generate_project_slug,
    generate_readable_id,
    get_reference_image_urls,
    human_size,
    is_valid_project_id,
    load_sheet_reference,
    now_iso,
    sanitize_filename,
)
from brandly_cli.video_prompts import (
    build_enhanced_video_prompt,
    build_single_shot_prompt,
    build_video_prompt,
    list_video_styles,
)

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_root(ctx: click.Context) -> Path:
    root = ctx.obj.get("root")
    if root:
        return Path(root)
    import os

    env_root = os.getenv("ROOT")
    if env_root:
        return Path(env_root)
    # Auto-detect: walk up from cwd looking for a .brandly marker.
    # This prevents double-nesting when the user runs brandly from inside
    # .brandly/<project-id>/ (the common case on Windows).
    cwd = Path.cwd()
    candidate = cwd
    for _ in range(10):  # safety limit
        if (candidate / ".brandly").is_dir():
            return candidate
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent
    return cwd


def _load_project_reference(project_id: str, root: Path) -> dict[str, Any] | None:
    """Read the project's primary_reference metadata block, if any.

    Returns the dict that ``brandly reference`` wrote to ``project.json``, or
    ``None`` if the project has no reference metadata (or cannot be read).
    Failures to read the project file are intentionally swallowed — callers
    treat ``None`` as "no reference" and surface a warning to the user.
    """
    try:
        proj = asyncio.run(ProjectManager(root).read(project_id))
    except Exception:
        return None
    if proj is None:
        return None
    ref = getattr(proj, "primary_reference", None)
    return ref if isinstance(ref, dict) else None


def _print_json(data: Any) -> None:
    console.print(json.dumps(data, indent=2, ensure_ascii=False))


def _save_artifact(
    url: str,
    project_id: str,
    type_label: str,
    *,
    root: Path,
    prompt_hint: str = "",
    category: str | None = None,
) -> Path | None:
    """Download a generated asset and save it under
    .brandly/{project_id}/{images|videos|audio}/{category}/.

    ``category`` routes the file into a sub-folder (e.g. 'scenes' for video,
    'prop' for object references, 'soundtrack' for music). Omit it to use
    the 'general' default.
    """
    if not url:
        return None
    proj_dir = layout.project_dir(root, project_id)
    media_category = category if category else "general"
    artifacts_dir = layout.media_dir(proj_dir, type_label, media_category)
    ext = Path(url.split("?")[0]).suffix or (".mp3" if type_label == "audio" else "")
    if not ext:
        ext = ".bin"
    ts = now_iso().replace(":", "-").replace(".", "_")
    hint = sanitize_filename(prompt_hint)[:20] if prompt_hint else ""
    fname = f"{type_label}_{ts}_{hint}{ext}"
    dest = artifacts_dir / fname
    try:
        asyncio.run(download_file(url, dest))
        return dest
    except Exception as e:
        console.print(f"[yellow]⚠ Could not save artifact: {e}[/yellow]")
        return None


def _print_project_summary(proj: dict[str, Any]) -> None:
    from rich.table import Table

    table = Table(title=f"Project: {proj.get('name', proj.get('id', 'Untitled'))}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("ID", proj.get("id", ""))
    table.add_row("Status", proj.get("status", ""))
    table.add_row("Phase", proj.get("current_phase", ""))
    table.add_row("Style", proj.get("style", ""))
    table.add_row("Budget", f"{proj.get('budget', 0)} credits")
    table.add_row("Spent", f"{proj.get('spent', 0)} credits")
    remaining = proj.get("remaining", proj.get("budget", 0) - proj.get("spent", 0))
    table.add_row("Remaining", f"{remaining} credits")
    table.add_row("Created", proj.get("created_at", ""))
    table.add_row("Updated", proj.get("updated_at", ""))
    console.print(table)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.option("--root", default=None, help="Working directory (default: cwd)")
@click.version_option(version=__version__, prog_name="brandly")
@click.pass_context
def cli(ctx: click.Context, root: str | None) -> None:
    """Brandly CLI — AI product video orchestrator.

    Add image, video, and sound generation to any AI tool.
    """
    ctx.ensure_object(dict)
    if root is not None:
        ctx.obj["root"] = root
    # Ensure stdout/stderr are UTF-8 on Windows (charmap codecs cannot encode U+26A0 etc.)
    if sys.platform == "win32":
        for _s in (sys.stdout, sys.stderr):
            if _s is not None and hasattr(_s, "reconfigure"):
                try:
                    _s.reconfigure(encoding="utf-8")
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@cli.command()
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
    asyncio.run(pm.create(proj))
    console.print(Panel(f"Project created! [green]{pid}[/green]", title="Brandly"))
    console.print(f"  Slug:      {slug}")
    console.print(f"  Name:      {name}")
    console.print(f"  Style:     {style}")
    console.print(f"  Shots:     {shots}")
    console.print(f"  Budget:    {budget} credits")
    console.print(f"  Platforms: {proj.target_platforms}")
    console.print(f"\nNext: [bold]brandly run {pid}[/bold] to start the pipeline.")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@cli.command()
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


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@cli.command(name="list")
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


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


def _check_budget(ctx: click.Context, project_id: str) -> None:
    """Warn if project budget has been exceeded."""
    root = _get_root(ctx)
    ct = CostTracker(root / ".brandly")
    try:
        summary = asyncio.run(ct.get_summary(project_id))
        if summary["total"] >= summary["budget"] and summary["budget"] > 0:
            console.print(
                f"[yellow]⚠ Budget exceeded: "
                f"{summary['total']}/{summary['budget']} credits used[/yellow]"
            )
    except FileNotFoundError:
        pass  # No cost tracking set up yet — skip check


@cli.command()
@click.argument("project_id")
@click.pass_context
def run(ctx: click.Context, project_id: str) -> None:
    """Run the next phase of the pipeline."""
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


# ---------------------------------------------------------------------------
# approve
# ---------------------------------------------------------------------------


@cli.command()
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


# ---------------------------------------------------------------------------
# estimate
# ---------------------------------------------------------------------------


@cli.command()
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

    phase_estimates = {
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
    total_estimate = total_base + overhead

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


# ---------------------------------------------------------------------------
# reference (primary reference image)
# ---------------------------------------------------------------------------


# Subject types that map to brandly's built-in sheet skills.
REFERENCE_SUBJECTS: dict[str, str] = {
    "object": "brandly-object-sheet",
    "character": "brandly-character-sheet",
    "location": "brandly-location-sheet",
    "vehicle": "brandly-vehicle-sheet",
    "animal": "brandly-animal-sheet",
    "plant": "brandly-plant-sheet",
    "mecha": "brandly-mecha-sheet",
}

# Per-subject prompt templates. These produce GOLD-grade primary reference
# images that downstream `brandly video` calls will auto-detect.
#
# Layout convention:
#   - object / character / vehicle / animal / plant / mecha:
#       MULTI-VIEW GRID — all views in one 16:9 image, split by columns/rows
#   - location:
#       FULL-FRAME — single wide establishing shot (16:9)
#
# Aspect ratio (16:9) is the project default; users can override with --ratio.
REFERENCE_PROMPT_TEMPLATES: dict[str, str] = {
    "object": (
        "Subject and Character\n"
        "{subject}. A single product, shown alone, with consistent material, "
        "color and form across every view. The product identity is strictly "
        "consistent across all views.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape production product reference board set "
        "against a seamless matte neutral mid-grey studio backdrop with subtle "
        "thin grey divider lines. Left two-thirds: a 3-column multi-view grid "
        "(front three-quarter, pure side profile, rear three-quarter). Right "
        "third: a single large hero front view. All views show the same "
        "product at the same scale.\n\n"
        "Lighting and Technical\n"
        "Soft, even three-point studio lighting, uniform across all panels. "
        "Shot with an 85mm lens, f/8 for deep focus across the whole board, "
        "high-resolution photorealistic texture with sharp definition of "
        "materials and surface detail, neutral color temperature with no "
        "color spill.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no people, no "
        "environment context, no dramatic shadows, no oversaturated colors."
    ),
    "character": (
        "Subject and Character\n"
        "{subject}. The character identity is strictly consistent across all "
        "views.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape production character reference board set "
        "against a seamless matte neutral mid-grey studio backdrop with "
        "subtle thin grey divider lines. The layout features a 2 by 2 grid in "
        "the left two-thirds of the frame, consisting of 2 equal square "
        "panels: top left is an extreme close-up of the face from eyes to "
        "chin; top right is a front-facing head and shoulders portrait; the "
        "right third of the board contains two tall vertical panels spanning "
        "the full height of the image with correct proportions, showing a "
        "full-body front-facing standing view and a full-body back standing "
        "view.\n\n"
        "Lighting and Technical\n"
        "Soft, even three-point studio lighting, uniform across all panels "
        "to ensure professional clarity. Shot with an 85mm lens, f/8 for "
        "deep focus across the entire board, high-resolution photorealistic "
        "texture, sharp definition of fabric weaves and skin pores, neutral "
        "color temperature with no color spill.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no distorted facial "
        "features, no inconsistent character design, no dramatic shadows, "
        "no oversaturated colors."
    ),
    "location": (
        "Subject and Character\n"
        "{subject}. A single environment shown with consistent lighting, "
        "time of day and reference points across the frame.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape establishing frame filling the entire "
        "canvas, no grid, no split panels, no insets. No people. Clear "
        "architectural or environmental reference points with consistent "
        "lighting and time of day across the whole frame.\n\n"
        "Lighting and Technical\n"
        "Uniform, professional lighting matched to the stated time of day; "
        "deep focus across the frame; high-resolution photorealistic "
        "texture; neutral, accurate color grading.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no UI elements, no "
        "people, no dramatic color cast."
    ),
    "vehicle": (
        "Subject and Character\n"
        "{subject}. A single vehicle shown with consistent form, paint and "
        "detail across every view. The vehicle identity is strictly "
        "consistent across all views.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape production vehicle reference board set "
        "against a seamless matte neutral mid-grey studio backdrop with "
        "subtle thin grey divider lines. Left two-thirds: a 3-column "
        "multi-view grid (front three-quarter, pure side profile, rear "
        "three-quarter). Right third: a single large hero front three-"
        "quarter view. All views show the same vehicle at the same scale.\n\n"
        "Lighting and Technical\n"
        "Soft, even three-point studio lighting, uniform across all panels. "
        "Shot with an 85mm lens, f/8 for deep focus, high-resolution "
        "photorealistic texture with sharp definition of paint, glass and "
        "surface detail, neutral color temperature with no color spill.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no people, no "
        "environment context, no dramatic shadows, no oversaturated colors."
    ),
    "animal": (
        "Subject and Character\n"
        "{subject}. A single animal shown with consistent anatomy, coat and "
        "proportion across every view. The animal identity is strictly "
        "consistent across all views.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape production animal reference board set "
        "against a seamless matte neutral mid-grey studio backdrop with "
        "subtle thin grey divider lines. Left two-thirds: a 3-column "
        "multi-view grid (full-body side profile, head close-up with eye "
        "detail, three-quarter body). Right third: a single large hero "
        "full-body view. All views show the same animal at the same scale.\n\n"
        "Lighting and Technical\n"
        "Soft, even three-point studio lighting, uniform across all panels. "
        "Shot with an 85mm lens, f/8 for deep focus, high-resolution "
        "photorealistic texture with sharp definition of coat and features, "
        "neutral color temperature with no color spill.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no people, no "
        "habitat or environment context, no distorted anatomy, no dramatic "
        "shadows, no oversaturated colors."
    ),
    "plant": (
        "Subject and Character\n"
        "{subject}. A single plant shown with consistent foliage, structure "
        "and color across every view. The plant identity is strictly "
        "consistent across all views.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape production botanical reference board set "
        "against a seamless matte neutral mid-grey studio backdrop with "
        "subtle thin grey divider lines. Left two-thirds: a 3-column "
        "multi-view grid (full-plant overview, leaf detail close-up, "
        "stem/trunk detail). Right third: a single large hero full-plant "
        "view. All views show the same plant at the same scale.\n\n"
        "Lighting and Technical\n"
        "Soft, even diffused studio lighting, uniform across all panels. "
        "Shot with a 100mm macro-to-mid lens, f/11 for deep focus, "
        "high-resolution photorealistic texture with sharp definition of "
        "leaf texture and color, neutral color temperature with no color "
        "spill.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no people, no soil "
        "or environment context, no distorted foliage, no dramatic shadows, "
        "no oversaturated colors."
    ),
    "mecha": (
        "Subject and Character\n"
        "{subject}. A single mecha shown with consistent proportions, "
        "panel lines, materials and detailing across every view. The mecha "
        "identity is strictly consistent across all views.\n\n"
        "Composition and Layout\n"
        "A single 16:9 landscape production mecha reference board set "
        "against a seamless matte neutral mid-grey studio backdrop with "
        "subtle thin grey divider lines. Left two-thirds: a 3-column "
        "multi-view grid (front three-quarter, pure side profile, detail "
        "close-up of distinctive mechanical features). Right third: a "
        "single large hero front three-quarter view. All views show the "
        "same mecha at the same scale.\n\n"
        "Lighting and Technical\n"
        "Soft, even three-point studio lighting, uniform across all panels. "
        "Shot with an 85mm lens, f/8 for deep focus, high-resolution "
        "photorealistic texture with sharp definition of metal, panel "
        "lines and wear, neutral color temperature with no color spill.\n\n"
        "Constraints\n"
        "No text, no labels, no watermarks, no logos, no people, no "
        "environment context, no distorted structure, no dramatic shadows, "
        "no oversaturated colors."
    ),
}


def build_reference_prompt(subject_type: str, subject: str) -> str:
    """Build a subject-styled reference prompt. Returns empty string for unknown types."""
    template = REFERENCE_PROMPT_TEMPLATES.get(subject_type)
    if not template:
        return ""
    return template.format(subject=subject.strip())


@cli.command(name="reference")
@click.argument("project_id")
@click.option(
    "--subject-type",
    "subject_type",
    required=True,
    type=click.Choice(list(REFERENCE_SUBJECTS.keys())),
    help="What kind of asset this reference is (object, character, location, etc.)",
)
@click.option(
    "--subject",
    "-s",
    required=True,
    help=(
        "The asset itself, e.g. 'Nike Air Max 1, white colorway, visible Air unit'. "
        "This is the asset that subsequent videos will reference."
    ),
)
@click.option(
    "--style-preset",
    default="commercial",
    type=click.Choice(STYLE_PRESET_OPTIONS),
    help="Style preset (default: commercial — best for product references)",
)
@click.option("--size", default="2K", help="Image size tier (1K, 2K, 3K, 4K)")
@click.option(
    "--ratio",
    default="16:9",
    help=(
        "Aspect ratio (16:9 default; multi-view grid for object/character, "
        "full-frame for location)"
    ),
)
@click.option(
    "--model",
    default="agnes-image-2.1-flash",
    help="Agnes image model (2.1-flash default, 2.0-flash for higher quality)",
)
@click.option(
    "--gate/--no-gate",
    "run_gate",
    default=True,
    help="Run the quality gate (AI check) on the generated sheet (default: on)",
)
@click.option(
    "--image",
    "import_image",
    default=None,
    help="Import an existing local image file as the project's primary "
    "reference instead of generating one (issue #23: adopt client-supplied "
    "plates without spending credits).",
)
@click.option(
    "--no-generate",
    "no_generate",
    is_flag=True,
    default=False,
    help="With --image: skip generation entirely and just register the file.",
)
@click.pass_context
def reference(
    ctx: click.Context,
    project_id: str,
    subject_type: str,
    subject: str,
    style_preset: str,
    size: str,
    ratio: str,
    model: str,
    run_gate: bool,
    import_image: str | None,
    no_generate: bool,
) -> None:
    """Generate the primary reference image for a project.

    The primary reference is a GOLD-grade image that locks the appearance of a
    key asset (object, character, location, etc.) across all subsequent
    `brandly video` generations. Should be the FIRST generation step.

    The generated image is saved to
    .brandly/<project_id>/images/<category>/ (e.g. images/prop/ for objects)
    with the prefix `reference_<subject_type>_*` and is auto-detected by
    `brandly video` (auto-injected as the strongest reference image).
    """
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)

    subject_skill = REFERENCE_SUBJECTS[subject_type]
    prompt = build_reference_prompt(subject_type, subject)
    if not prompt:
        console.print(f"[red]Unknown subject type: {subject_type}[/red]")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Issue #23: import an existing local plate as the primary reference.
    # No generation, no credit spend — just register and lock the file.
    # ------------------------------------------------------------------
    if import_image:
        if not no_generate:
            console.print(
                "[yellow]⚠ --image implies --no-generate: the existing file is "
                "registered as-is (no new image is generated).[/yellow]"
            )
        src = Path(import_image)
        if not src.is_file():
            console.print(f"[red]Image not found: {src}[/red]")
            sys.exit(1)

        root = _get_root(ctx)
        category = layout.image_category_for_subject(subject_type)
        target_dir = layout.media_dir(
            layout.project_dir(root, project_id), "images", category
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        stem = sanitize_filename(src.stem) or "plate"
        dest = target_dir / f"reference_{subject_type}_{stem}{src.suffix or '.png'}"
        shutil.copyfile(src, dest)
        console.print(f"[green]✓ Imported reference plate:[/green] {dest}")

        from brandly_cli.utils import write_generation_plan

        plan, plan_reused = write_generation_plan(
            project_id,
            "reference",
            root=root,
            prompt=subject,
            model="imported",
            style=style_preset or "default",
            extra_config={
                "subject_type": subject_type,
                "role": "primary_reference",
                "imported_from": str(src),
            },
            source="brandly reference --image",
        )
        console.print(f"[dim]Plan {'reused' if plan_reused else 'written'}: {plan}[/dim]")

        reference_meta = {
            "subject_type": subject_type,
            "skill": subject_skill,
            "subject": subject,
            "image_path": str(dest),
            "source_url": "",
            "generated_at": now_iso(),
            "model": "imported",
            "style_preset": style_preset,
            "imported_from": str(src),
        }
        pm = ProjectManager(root)
        update_result = asyncio.run(
            pm.update(  # type: ignore[arg-type]
                project_id, {"primary_reference": reference_meta}
            )
        )
        if update_result is None:
            console.print("[red]✗ Failed to update project metadata.[/red]")
            sys.exit(1)
        console.print("[green]✓ Project primary_reference metadata updated.[/green]")

        approved, note = _human_review_gate(
            "reference", f"the imported {subject_type} reference for '{subject}'"
        )
        if note:
            _write_review_note(
                root, project_id, "reference", note, extra=f"subject: {subject}"
            )
        if not approved:
            console.print(
                "[red]✗ Imported reference rejected at the human gate — the "
                "plan stays PENDING; remove it or import a different file.[/red]"
            )
            sys.exit(1)
        console.print("[green]✓ Human gate passed — reference approved.[/green]")

        from brandly_cli.utils import write_generation_doc

        write_generation_doc(
            project_id,
            "reference",
            dest,
            root=root,
            prompt=subject,
            model="imported",
            style=style_preset,
            metadata={
                "subject_type": subject_type,
                "imported_from": str(src),
                "role": "primary_reference",
            },
            source="brandly reference --image",
            plan_file=str(plan),
        )
        console.print(
            f"\n[bold]Next:[/bold] run [cyan]brandly video {project_id} ...[/cyan] — "
            f"the imported reference will be auto-injected as a reference image."
        )
        return

    # Add the project's idea as additional context (for multi-asset campaigns)
    root = _get_root(ctx)
    try:
        proj = asyncio.run(ProjectManager(root).read(project_id))
        if proj and getattr(proj, "description", None):
            prompt += f"\n\nCampaign context: {proj.description}"
    except Exception:
        pass  # project read failure is non-fatal for reference

    # Apply style preset
    prompt = apply_style_preset(prompt, style_preset) if style_preset else prompt

    # Load subject-skill reference docs for richer prompting
    skill_data = load_sheet_reference(subject_skill, root)
    if skill_data and skill_data.get("references"):
        prompt_variants = skill_data["references"].get("prompt-variants.md", "")
        if prompt_variants:
            prompt += f"\n\n[Reference skill: {subject_skill}]\n{prompt_variants[:500]}"

    # Write pre-generation plan
    from brandly_cli.utils import write_generation_plan

    plan, plan_reused = write_generation_plan(
        project_id,
        "reference",
        root=root,
        prompt=subject,
        model=model,
        style=style_preset or "default",
        extra_config={
            "subject_type": subject_type,
            "size": size,
            "ratio": ratio,
            "role": "primary_reference",
        },
        source="brandly reference",
    )
    console.print(f"[dim]Plan {'reused' if plan_reused else 'written'}: {plan}[/dim]")

    console.print(
        f"[dim]Generating {subject_type} reference with model {model} "
        f"({style_preset} style)...[/dim]"
    )
    console.print(f"[dim]Subject skill: {subject_skill}[/dim]")

    try:
        result = asyncio.run(generate_image(prompt, model=model, size=size, ratio=ratio))
    except Exception as e:
        console.print(f"[red]Error generating reference: {e}[/red]")
        if project_id:
            docs_dir = layout.docs_dir(layout.project_dir(root, project_id), "tmp")
            docs_dir.mkdir(parents=True, exist_ok=True)
            fail_doc = (
                docs_dir
                / f"reference_fail_{now_iso().replace(':', '-').replace('.', '_')}.md"
            )
            fail_doc.write_text(
                f"# Reference Generation Failed\n\n"
                f"**Subject type:** {subject_type}\n\n**Error:** {e}\n\n"
                f"**Subject:** {subject}\n\n**Status:** FAILED\n",
                encoding="utf-8",
            )
            from brandly_cli.utils import upsert_production_plan

            upsert_production_plan(
                project_id,
                root=root,
                plan_file=str(plan),
                asset_type="reference",
                model=model,
                status="FAILED",
                source="brandly reference",
            )
        sys.exit(1)

    url = result.get("url") or ""
    if not url:
        console.print(
            "[yellow]Reference generated (base64 returned) — no URL to save[/yellow]"
        )
        sys.exit(1)

    from brandly_cli.utils import write_generation_doc

    # Primary references live in images/<category>/ — the matching sub-folder.
    saved = _save_artifact(
        url,
        project_id,
        "images",
        root=root,
        prompt_hint=f"reference_{subject_type}_{subject}",
        category=layout.image_category_for_subject(subject_type),
    )
    if saved:
        # Rename to the conventional sheet name:
        #   character -> char_<name>  ·  location -> loc_<name>  ·  object -> prop_<name>
        timestamp = now_iso().replace(":", "-").replace(".", "_")
        ext = saved.suffix or ".png"
        stem = layout.build_sheet_filename(subject_type, subject, timestamp)
        new_path = saved.parent / f"{stem}{ext}"
        try:
            saved.rename(new_path)
        except OSError:
            new_path = saved  # fall back to the original name if rename fails
        saved = new_path
        console.print(f"[green]✓ Reference image saved:[/green] {saved}")

        # Persist the primary reference metadata on the project so downstream
        # tools (e.g. `brandly video`) can read it.
        reference_meta = {
            "subject_type": subject_type,
            "skill": subject_skill,
            "subject": subject,
            "image_path": str(saved),
            "source_url": url,
            "generated_at": now_iso(),
            "model": model,
            "style_preset": style_preset,
        }
        pm = ProjectManager(root)
        result = asyncio.run(
            pm.update(  # type: ignore[arg-type]
                project_id, {"primary_reference": reference_meta}
            )
        )
        if result is None:
            console.print("[red]✗ Failed to update project metadata.[/red]")
            sys.exit(1)
        console.print("[green]✓ Project primary_reference metadata updated.[/green]")

        if run_gate:
            from brandly_cli import quality_gate

            gate_result = asyncio.run(
                quality_gate.verify_element(
                    saved,
                    description=subject,
                    expect_matt_background=True,
                    use_ai=True,
                    root=root,
                    project_id=project_id,
                )
            )
            _print_gate_report(gate_result)
            if gate_result.status == quality_gate.FAIL:
                console.print(
                    "[yellow]⚠ Quality gate failed — review or regenerate the "
                    "sheet before using it as a reference.[/yellow]"
                )

        # Human-in-the-loop gate: confirm the result matches expectations
        approved, note = _human_review_gate(
            "reference", f"the {subject_type} reference for '{subject}'"
        )
        if note:
            _write_review_note(
                root, project_id, "reference", note, extra=f"subject: {subject}"
            )
        if not approved:
            console.print(
                "[red]✗ Reference rejected at the human gate — adjust the prompt "
                "or subject details and regenerate.[/red]"
            )
            sys.exit(1)
        console.print("[green]✓ Human gate passed — reference approved.[/green]")

        # Only after approval: write the generation doc and flip the plan to
        # COMPLETED in the production plan (a rejection keeps it PENDING so
        # the next run reuses the same plan).
        write_generation_doc(
            project_id,
            "reference",
            saved,
            root=root,
            prompt=prompt,
            model=model,
            style=style_preset,
            metadata={
                "subject_type": subject_type,
                "size": size,
                "ratio": ratio,
                "source_url": url,
            },
            source="brandly reference",
            plan_file=str(plan),
        )

        console.print(
            f"\n[bold]Next:[/bold] run [cyan]brandly video {project_id} ...[/cyan] — the "
            f"primary reference image will be auto-injected as a reference image."
        )
    else:
        console.print("[yellow]⚠ Could not save reference artifact[/yellow]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# image
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--project-id", default=None, help="Optional project UUID")
@click.option("--prompt", "-p", required=True, help="Image generation prompt")
@click.option(
    "--model",
    default="agnes-image-2.5-flash",
    help="Agnes image model (2.5-flash is the current default)",
)
@click.option("--size", default="2K", help="Image size tier (1K, 2K, 3K, 4K)")
@click.option("--ratio", default="16:9", help="Aspect ratio")
@click.option(
    "--style-preset",
    default=None,
    type=click.Choice(STYLE_PRESET_OPTIONS),
    help="Style preset to avoid AI slop",
)
@click.pass_context
def image(
    ctx: click.Context,
    project_id: str | None,
    prompt: str,
    model: str,
    size: str,
    ratio: str,
    style_preset: str | None,
) -> None:
    """Generate an image via Agnes AI."""
    enhanced = apply_style_preset(prompt, style_preset) if style_preset else prompt

    # Try to load sheet reference for better prompting if project has context
    root = _get_root(ctx)
    if project_id:
        skill_names = [
            "brandly-vehicle-sheet",
            "brandly-character-sheet",
            "brandly-object-sheet",
            "brandly-location-sheet",
            "brandly-animal-sheet",
            "brandly-plant-sheet",
            "brandly-mecha-sheet",
        ]
        for skill in skill_names:
            sheet = load_sheet_reference(skill, root)
            if sheet and sheet["references"]:
                sheet_hint = sheet["references"].get("prompt-variants.md", "")
                if sheet_hint:
                    enhanced += f"\n\n[Sheet reference from {skill}]\n{sheet_hint[:300]}"
                    console.print(f"[dim]Loaded sheet reference: {skill}[/dim]")
                    break

        # Also auto-detect existing artifacts as references
        auto_refs = get_reference_image_urls(project_id, root)
        if auto_refs:
            enhanced += (
                f"\n\nReference images ({len(auto_refs)}): "
                "Use these as visual guides for consistency."
            )
            console.print(f"[dim]Found {len(auto_refs)} artifact(s) for reference[/dim]")

    # Write pre-generation plan BEFORE API call
    plan_file_ref: str | None = None
    if project_id:
        from brandly_cli.utils import write_generation_plan

        plan, plan_reused = write_generation_plan(
            project_id,
            "image",
            root=root,
            prompt=prompt,
            model=model,
            style=style_preset or "default",
            extra_config={"size": size, "ratio": ratio},
            source="brandly image",
        )
        plan_file_ref = str(plan)
        console.print(f"[dim]Plan {'reused' if plan_reused else 'written'}: {plan}[/dim]")

    console.print(
        f"[dim]Generating image with model {model} ({style_preset or 'default'} style)...[/dim]"
    )

    try:
        result = asyncio.run(generate_image(enhanced, model=model, size=size, ratio=ratio))
    except Exception as e:
        console.print(f"[red]Error generating image: {e}[/red]")
        if project_id:
            # Update plan to show failure
            from brandly_cli.utils import write_generation_doc

            docs_dir = layout.docs_dir(layout.project_dir(root, project_id), "tmp")
            docs_dir.mkdir(parents=True, exist_ok=True)
            fail_doc = docs_dir / f"image_fail_{now_iso().replace(':', '-').replace('.', '_')}.md"
            fail_doc.write_text(
                f"# Image Generation Failed\n\n"
                f"**Error:** {e}\n\n**Prompt:** {prompt}\n\n**Status:** FAILED\n",
                encoding="utf-8",
            )
            from brandly_cli.utils import upsert_production_plan

            if plan_file_ref:
                upsert_production_plan(
                    project_id,
                    root=root,
                    plan_file=plan_file_ref,
                    asset_type="image",
                    model=model,
                    status="FAILED",
                    source="brandly image",
                )
        sys.exit(1)

    url = result.get("url") or ""
    if url:
        console.print(f"[green]✓ Image generated:[/green] {url}")
        # Always save to disk
        pid = project_id or "untitled"
        root = _get_root(ctx)
        saved = _save_artifact(url, pid, "images", root=root, prompt_hint=prompt)
        if saved:
            console.print(f"  Saved → {saved}")
            # Write generation document
            from brandly_cli.utils import write_generation_doc

            write_generation_doc(
                pid,
                "image",
                saved,
                root=root,
                prompt=enhanced,
                model=model,
                style=style_preset,
                metadata={"size": size, "ratio": ratio, "source_url": url},
                source="brandly image",
                plan_file=plan_file_ref,
            )
            console.print(f"  Doc → {saved.parent.parent / 'docs'}")
        else:
            console.print("[yellow]⚠ Could not save artifact, but URL is available[/yellow]")
    else:
        console.print("[yellow]Image generated (base64 returned)[/yellow]")
        if project_id:
            from brandly_cli.utils import write_generation_doc

            write_generation_doc(
                project_id,
                "image",
                Path("base64_output"),
                root=root,
                prompt=enhanced,
                model=model,
                style=style_preset,
                metadata={"size": size, "ratio": ratio, "note": "base64 output"},
                source="brandly image",
                plan_file=plan_file_ref,
            )

    if project_id:
        root = _get_root(ctx)
        pm = ProjectManager(root)
        asyncio.run(
            pm.update(
                project_id,
                {
                    "image_analysis": {
                        "generated_url": url,
                        "prompt": prompt,
                        "enhanced_prompt": enhanced,
                        "style_preset": style_preset,
                        "model": model,
                        "generated_at": now_iso(),
                    }
                },
            )
        )
        # Auto-record credit spend so budget gates can fire.
        _record_media_spend(root, project_id, "image", model)

    _print_json(result)


# ---------------------------------------------------------------------------
# video
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("project_id")
@click.option("--prompt", "-p", required=True, help="Video generation prompt")
@click.option(
    "--model",
    default="agnes-video-2.5-flash",
    help="Agnes video model (2.5-flash is the current default; 720P, 4-12s)",
)
@click.option(
    "--style",
    default="cinematic",
    type=click.Choice(list_video_styles()),
    help="Video style preset for consistent output",
)
@click.option(
    "--mode",
    default="auto",
    type=click.Choice(["auto", "text", "keyframe", "reference"]),
    help=(
        "Generation mode. 'auto' (default) infers it: keyframe when a start/"
        "end frame is provided, reference when reference images are provided, "
        "text otherwise."
    ),
)
@click.option("--duration", "-d", default=10, help="Duration in seconds (default: 10)")
@click.option("--aspect-ratio", default="16:9", help="Aspect ratio")
@click.option("--first-frame", default=None, help="Start frame image URL or local file path (keyframe mode)")
@click.option("--last-frame", default=None, help="End frame image URL or local file path (keyframe mode)")
@click.option(
    "--reference-images",
    "-r",
    default=None,
    help="Comma-separated image URLs or local file paths for character/object consistency (reference mode)",
)
@click.option(
    "--character",
    "-c",
    default=None,
    help="Character description for identity locking (e.g. 'woman in red dress, blonde hair')",
)
@click.option(
    "--wait/--no-wait",
    "wait",
    default=True,
    help="Poll until generation completes and download the video to disk (default: on)",
)
@click.option("--max-wait", default=600, help="Max wait seconds (default: 600)")
@click.option(
    "--require-reference/--no-require-reference",
    "require_reference",
    default=False,
    help="If set, fail when project has no primary reference image.",
)
@click.option(
    "--allow-referenceless",
    "allow_referenceless",
    is_flag=True,
    help="Bypass the require-reference check (escape hatch for re-runs/edge cases).",
)
@click.option(
    "--gate/--no-gate",
    "run_gate",
    default=True,
    help="Run the quality gate on the generated video (default: on)",
)
@click.option(
    "--reference-audios",
    default=None,
    help="Comma-separated reference audio URLs (reference mode)",
)
@click.option(
    "--no-auto-refs",
    "auto_refs_enabled",
    flag_value=False,
    default=True,
    help="Do NOT auto-inject every project image as a reference (issue #20: "
    "prevents payload bloat and style bleed between visual worlds).",
)
@click.option(
    "--auto-ref-category",
    default=None,
    help="Scope auto-injected references to one image category "
    "(e.g. 'prop', 'character', 'location') instead of all images.",
)
@click.pass_context
def video(
    ctx: click.Context,
    project_id: str,
    prompt: str,
    model: str,
    style: str,
    mode: str,
    duration: int,
    aspect_ratio: str,
    first_frame: str | None,
    last_frame: str | None,
    reference_images: str | None,
    character: str | None,
    wait: bool,
    max_wait: int,
    require_reference: bool | None,
    allow_referenceless: bool,
    run_gate: bool,
    reference_audios: str | None,
    auto_refs_enabled: bool,
    auto_ref_category: str | None,
) -> None:
    """Generate an AI video via Agnes AI.

    For best results, the project should have a primary reference image
    generated first via `brandly reference`. The reference is auto-injected
    as the FIRST reference image (strongest influence). Use --require-reference
    to fail if the reference is missing.

    By default the command polls until generation completes and downloads
    the video to .brandly/<project>/videos/scenes/ (disable with --no-wait).

    Mode is auto-inferred unless --mode is given explicitly:
    text (no image inputs) → reference (reference images provided) →
    keyframe (start/end frame provided).
    """
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)

    # Auto-detect project artifacts as additional reference images
    root = _get_root(ctx)
    auto_refs = get_reference_image_urls(project_id, root) if auto_refs_enabled else []
    # Issue #20: optionally scope auto-injected references to one category
    # (e.g. images/prop/, images/location/) so each scene is anchored to
    # exactly its own plates instead of receiving the whole images tree.
    if auto_ref_category:
        marker = f"images{os.sep}{auto_ref_category}{os.sep}"
        auto_refs = [p for p in auto_refs if marker in p or f"images/{auto_ref_category}/" in p]
        if not auto_refs:
            console.print(
                f"[yellow]⚠ No images found in category '{auto_ref_category}' — "
                "auto references are empty for this run.[/yellow]"
            )

    # Read the project's primary_reference metadata (set by `brandly reference`)
    reference: dict[str, Any] | None = _load_project_reference(project_id, root)

    # Build the list of paths to pass as the FIRST reference (strongest influence).
    # Include the local file path (if on disk) and the source URL (if any).
    ref_paths: list[str] = []
    if reference is not None:
        path = reference.get("image_path", "")
        if path and Path(path).exists():
            ref_paths.append(path)
        src_url = reference.get("source_url", "")
        if src_url:
            ref_paths.append(src_url)
        if not ref_paths:
            reference = None  # stale metadata, no usable path

    missing = reference is None
    if missing and not allow_referenceless:
        next_cmd = (
            f"brandly reference {project_id} --subject-type object "
            f"--subject '<product/character/location description>'"
        )
        if require_reference:
            console.print(
                f"[red]⚠ No primary reference for project {project_id}.[/red]\n"
                f"  Video generation without a reference produces high-drift output.\n"
                f"  Generate one first:\n"
                f"    [cyan]{next_cmd}[/cyan]\n"
            )
            console.print(
                "[red]Aborting because --require-reference was set. "
                "Use --allow-referenceless to override.[/red]"
            )
            sys.exit(2)
        else:
            console.print(
                f"[yellow]⚠ No primary reference for project {project_id}.[/yellow]\n"
                f"  Video generation without a reference produces high-drift output.\n"
                f"  Generate one first:\n"
                f"    [cyan]{next_cmd}[/cyan]\n"
            )
            console.print(
                "[dim]Continuing without reference. Pass --require-reference to "
                "enforce, --allow-referenceless to silence this warning.[/dim]"
            )
    elif reference is not None:
        ref_name = (
            Path(ref_paths[0]).name
            if ref_paths
            else reference.get("source_url", "")[:50]
        )
        console.print(
            f"[green]✓ Primary reference:[/green] "
            f"{reference.get('subject_type', 'unknown')} ({ref_name})"
        )

    # Merge references: primary reference first (strongest influence),
    # then user-supplied, then auto-detected artifacts.
    user_imgs = (
        [u.strip() for u in reference_images.split(",") if u.strip()] if reference_images else []
    )
    imgs = ref_paths + user_imgs + auto_refs

    # Parse reference audio URLs
    auds = (
        [u.strip() for u in reference_audios.split(",") if u.strip()]
        if reference_audios
        else None
    )

    # Enhance prompt with style and character consistency
    enhanced = build_enhanced_video_prompt(
        prompt, style, character=character, reference_images=imgs
    )

    # Try to load sheet reference for better prompting
    skill_names = [
        "brandly-vehicle-sheet",
        "brandly-character-sheet",
        "brandly-object-sheet",
        "brandly-location-sheet",
        "brandly-animal-sheet",
        "brandly-plant-sheet",
        "brandly-mecha-sheet",
    ]
    sheet_hint = ""
    loaded_skill = "none"
    for skill in skill_names:
        sheet = load_sheet_reference(skill, root)
        if sheet and sheet["references"]:
            sheet_hint = sheet["references"].get("prompt-variants.md", "")
            if sheet_hint:
                enhanced += f"\n\n[Sheet reference from {skill}]\n{sheet_hint[:500]}"
                loaded_skill = skill
            break

    console.print(f"[dim]Creating video task with model {model} (style: {style})...[/dim]")
    # Note: 2.5-flash is the only Agnes video model; rate-limited (1 req/min)
    console.print(f"[dim]Model: {model} | Style: {style} | Mode: {mode}[/dim]")
    if character:
        console.print(f"[dim]Character anchor: {character[:60]}...[/dim]")
    if imgs:
        console.print(f"[dim]Reference images: {len(imgs)}[/dim]")
    if sheet_hint:
        console.print(f"[dim]Loaded sheet reference: {loaded_skill}[/dim]")

    # Write pre-generation plan BEFORE API call
    from brandly_cli.utils import write_generation_plan

    plan, plan_reused = write_generation_plan(
        project_id,
        "video",
        root=root,
        prompt=prompt,
        model=model,
        style=style,
        extra_config={
            "mode": mode,
            "duration": f"{duration}s",
            "aspect_ratio": aspect_ratio,
            "reference_images": len(imgs),
            "sheet_reference": loaded_skill,
        },
        source="brandly video",
    )
    console.print(f"[dim]Plan {'reused' if plan_reused else 'written'}: {plan}[/dim]")

    # Archive local keyframes into the project (images/keyframe/)
    if project_id and (first_frame or last_frame) and mode in ("auto", "keyframe"):
        for label, frame in (("start_frame", first_frame), ("end_frame", last_frame)):
            if not frame:
                continue
            frame_path = Path(frame)
            if not frame_path.is_file():
                continue  # remote URL or missing local file
            keyframe_dir = layout.media_dir(
                layout.project_dir(root, project_id), "images", "keyframe"
            )
            keyframe_dir.mkdir(parents=True, exist_ok=True)
            slug = layout.image_name_token(frame_path.stem) or "frame"
            target = keyframe_dir / f"{label}_{slug}{frame_path.suffix or '.png'}"
            try:
                shutil.copyfile(frame_path, target)
                console.print(f"[dim]Keyframe archived: {target}[/dim]")
            except OSError:
                pass

    try:
        task = asyncio.run(
            create_video_task(
                enhanced,
                model=model,
                mode=mode,
                duration=duration,
                aspect_ratio=aspect_ratio,
                first_frame=first_frame,
                last_frame=last_frame,
                reference_images=imgs if imgs else None,
                reference_audios=auds,
                # Issue #21: the preset follows --style instead of being
                # hardcoded — cinematic only for cinematic; disabled for
                # non-photographic styles (sumi-e ink, cel animation, ...).
                style_preset="cinematic" if style == "cinematic" else None,
            )
        )
    except Exception as e:
        # Issue #24: never print an empty message — show the exception type
        # and whatever detail we have (timeout exceptions often have none).
        detail = str(e).strip()
        console.print(
            f"[red]Error creating video task: {type(e).__name__}: "
            f"{detail or '(no error message — likely a timeout; see retry log above)'}"
            f"[/red]"
        )
        console.print(
            "[dim]Tip: large reference payloads can time out the create endpoint — "
            "references are now auto-converted to smaller webp/jpeg copies; use "
            "--no-auto-refs / --auto-ref-category to slim the request further.[/dim]"
        )
        from brandly_cli.utils import upsert_production_plan

        upsert_production_plan(
            project_id,
            root=root,
            plan_file=str(plan),
            asset_type="video",
            model=model,
            status="FAILED",
            source="brandly video",
        )
        sys.exit(1)

    video_id = task["video_id"]
    console.print(f"[green]✓ Task created:[/green] {video_id}")
    console.print(f"  Status: {task['status']}  Progress: {task['progress']}%")
    if task.get("mode"):
        mode = task["mode"]
        console.print(f"  Mode: {mode}")

    if wait:
        console.print(f"[dim]Polling (max {max_wait}s)...[/dim]")
        try:
            result = asyncio.run(poll_video(video_id, max_wait_seconds=max_wait, model_name=model))
        except TimeoutError as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print(
                f"[dim]Video ID: {video_id} — run "
                f"'brandly job-resume {video_id} --project-id {project_id}' to poll later.[/dim]"
            )
            # Update plan to show timeout
            from brandly_cli.utils import (
                upsert_production_plan,
                write_generation_doc,
            )

            write_generation_doc(
                project_id,
                "video",
                Path("timeout"),
                root=root,
                prompt=enhanced,
                model=model,
                style=style,
                metadata={"video_id": video_id, "status": "timeout", "error": str(e)},
                source="brandly video",
            )
            upsert_production_plan(
                project_id,
                root=root,
                plan_file=str(plan),
                asset_type="video",
                model=model,
                status="FAILED",
                source="brandly video",
            )
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error polling video: {e}[/red]")
            sys.exit(1)

        url = result.get("url") or ""
        console.print(f"[green]✓ Video ready:[/green] {url or 'no URL'}")
        task["url"] = url
        task["final_status"] = result.get("status")
        # Always save video to disk if URL exists
        if url:
            saved = _save_artifact(
                url,
                project_id,
                "videos",
                root=root,
                prompt_hint=prompt,
                category="scenes",
            )
            if saved:
                console.print(f"  Saved → {saved}")
                # Record the job so `brandly job-resume <id>` can locate the project.
                # (The generation doc + plan COMPLETED upsert happen after the
                # human gate approves, or later via `job-resume`.)
                pm = ProjectManager(root)
                asyncio.run(
                    pm.update(
                        project_id,
                        {
                            "last_video_job": {
                                "video_id": video_id,
                                "url": url,
                                "saved_path": str(saved),
                                "mode": mode,
                                "model": model,
                                "created_at": now_iso(),
                            }
                        },
                    )
                )
            else:
                console.print("[yellow]⚠ Could not save artifact, but URL is available[/yellow]")
    else:
        console.print(
            f"[dim]Not waiting (use --wait to poll). To download when the video "
            f"is ready, run:\n  brandly job-resume {video_id} --project-id {project_id}[/dim]"
        )

    # Quality gate: verify the generated video before the next step.
    if run_gate:
        from brandly_cli import quality_gate

        _saved_media = locals().get("saved")
        if isinstance(_saved_media, Path) and _saved_media.exists():
            gate_result = asyncio.run(
                quality_gate.verify_element(
                    _saved_media,
                    description=character or prompt,
                    expect_matt_background=False,
                    use_ai=True,
                    root=root,
                    project_id=project_id,
                )
            )
            _print_gate_report(gate_result)
            if gate_result.status == quality_gate.FAIL:
                console.print(
                    "[yellow]⚠ Quality gate failed — review or regenerate "
                    "before editing/publishing.[/yellow]"
                )

    # Human-in-the-loop gate: confirm the video before the next step
    # (only when an artifact was actually downloaded and saved).
    _media_local = locals().get("saved")
    _media_local = (
        _media_local
        if isinstance(_media_local, Path) and _media_local.exists()
        else None
    )
    if _media_local:
        approved, note = _human_review_gate(
            "video", f"video {video_id} ({_media_local.name})"
        )
        if note:
            _write_review_note(
                root, project_id, "video", note, extra=f"video_id: {video_id}"
            )
        if not approved:
            console.print(
                "[red]✗ Video rejected at the human gate — regenerate with an "
                "adjusted prompt (the plan is reused until the config changes).[/red]"
            )
            sys.exit(1)
        console.print("[green]✓ Human gate passed — video approved.[/green]")

        # Only after approval: write the generation doc and flip the plan to
        # COMPLETED in the production plan.
        from brandly_cli.utils import write_generation_doc

        write_generation_doc(
            project_id,
            "video",
            _media_local,
            root=root,
            prompt=enhanced,
            model=model,
            style=style,
            metadata={
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "source_url": url,
                "video_id": video_id,
            },
            source="brandly video",
            plan_file=str(plan),
        )
        console.print(f"  Doc → {_media_local.parent.parent / 'docs'}")

    # Persist to project
    root = _get_root(ctx)
    pm = ProjectManager(root)
    asyncio.run(pm.update(project_id, {"current_phase": "asset"}))
    # Auto-record credit spend so budget gates can fire.
    _record_media_spend(root, project_id, "video", model)

    _print_json(task)


# ---------------------------------------------------------------------------
# produce — shot-by-shot generation driven by the production plan
# (issue #22, per production directive: NO batch generation. The production
# plan is the source of truth: every shot is prepared on it first, then
# generation is pulled from the plan one shot at a time at the Agnes
# rate limit of 1 request per minute.)
# ---------------------------------------------------------------------------


def _generate_shot(
    project_id: str,
    shot: dict[str, Any],
    *,
    ctx: click.Context,
    root: Path,
    auto_refs_enabled: bool = True,
    allow_referenceless: bool = False,
    max_wait: int = 600,
) -> bool:
    """Generate ONE shot through the standard ``brandly video`` pipeline.

    This keeps every per-shot safeguard: pre-generation plan, quality gate,
    human gate, generation doc and credit recording. Returns True when the
    shot finished successfully.
    """
    references = shot.get("references")
    if isinstance(references, list):
        references = ",".join(str(r) for r in references if str(r).strip())

    try:
        ctx.invoke(
            video,
            project_id=project_id,
            prompt=str(shot.get("prompt", "")),
            duration=int(shot.get("duration", 5)),
            style=str(shot.get("style", "cinematic")),
            reference_images=references or None,
            character=shot.get("character") or None,
            wait=True,
            max_wait=max_wait,
            require_reference=False,
            auto_refs_enabled=auto_refs_enabled,
            allow_referenceless=allow_referenceless,
        )
    except SystemExit as exc:
        return exc.code in (0, None)
    return True


@cli.command()
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
        console.print(f"[red]Invalid shot list JSON: {e}[/red]")
        sys.exit(1)

    use_runner = (
        isinstance(shots, dict)
        or no_auto_refs
        or character
        or allow_referenceless
        or only
        or max_shots
    )
    if use_runner:
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
        name = str(shot.get("name") or f"shot-{idx}")
        slug = sanitize_filename(name.lower()) or f"shot-{idx}"
        asset_type = f"video-shot-{slug}"
        plan, plan_reused = write_generation_plan(
            project_id,
            asset_type,
            root=root,
            prompt=str(shot.get("prompt", "")),
            model=model,
            style=str(shot.get("style", "cinematic")),
            extra_config={
                "shot": name,
                "duration": f"{shot.get('duration', 5)}s",
                "role": "shot",
            },
            source="brandly produce",
        )
        prepared.append((shot, name, plan))
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
        ok = _generate_shot(project_id, shot, ctx=ctx, root=root)
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


def _run_produce_runner(
    ctx: click.Context,
    project_id: str,
    data: dict[str, Any] | list[dict[str, Any]],
    root: Path,
    interval: float,
    no_auto_refs: bool,
    character: str | None,
    allow_referenceless: bool,
    max_wait: int,
    only: tuple[str, ...],
    max_shots: int,
) -> None:
    """Progress-file runner path for ``brandly produce`` (see produce())."""
    project_dir = root / ".brandly" / project_id
    images_dir = project_dir / "images"
    scenes_dir = project_dir / "videos" / "scenes"
    progress = shot_runner.ProgressLog(
        project_dir / "docs" / "tmp" / "produce_progress.txt"
    )
    shots = shot_runner.flatten_shots(data, images_dir, character=character)

    def generate_one(shot: shot_runner.Shot) -> tuple[bool, int, str]:
        ok = _generate_shot(
            project_id,
            {**shot.to_video_kwargs(), "character": shot.character},
            ctx=ctx,
            root=root,
            auto_refs_enabled=not no_auto_refs,
            allow_referenceless=allow_referenceless,
            max_wait=max_wait,
        )
        return ok, 0 if ok else 1, ""

    config = shot_runner.RunnerConfig(
        shots=shots,
        generate_one=generate_one,
        scenes_dir=scenes_dir,
        progress=progress,
        interval=interval,
        only=set(only) if only else None,
        max_shots=max_shots,
        say=lambda msg: console.print(f"[dim]{msg}[/dim]"),
    )
    sys.exit(shot_runner.run_shots(config))


def _record_media_spend(root: Path, project_id: str, kind: str, model_id: str) -> None:
    """Auto-record credit spend after a successful media generation.

    Looks up the model's ``cost_credits`` from constants and calls
    CostTracker.record_spend, then syncs the result back into the
    project's ``spent`` field so ``brandly status`` stays accurate.
    """
    from typing import cast

    from brandly_cli.constants import IMAGE_MODEL_INFO, VIDEO_MODEL_INFO

    cost = (
        cast(dict[str, Any], VIDEO_MODEL_INFO).get(model_id, {}).get("cost_credits")
        or cast(dict[str, Any], IMAGE_MODEL_INFO).get(model_id, {}).get("cost_credits")
        or 0
    )
    if cost <= 0:
        return
    ct = CostTracker(root / ".brandly")
    pm = ProjectManager(root)
    try:
        proj = asyncio.run(pm.read(project_id))
        budget = proj.budget if proj else None
    except Exception:
        budget = None
    try:
        result = asyncio.run(ct.record_spend(project_id, kind, kind, cost, budget_credits=budget))
        asyncio.run(pm.update(project_id, {"spent": result["total_spent"]}))
        console.print(
            f"[dim]  Spent: {result['credits']} credits for {kind} ({model_id})  "
            f"Total: {result['total_spent']}/{result['budget']}[/dim]"
        )
    except ValueError as e:
        console.print(f"[yellow]⚠ Budget exceeded — {e}[/yellow]")
    except Exception as e:
        console.print(f"[dim]  Cost record failed (non-fatal): {e}[/dim]")


def _check_phase_artifacts(
    project_id: str, phase: str, root: Path
) -> list[tuple[str, Path]]:
    """Return a list of (label, path) for artifacts that a phase requires but does not have.

    Currently covers the most common cases:
    - ``asset``: at least one video clip OR at least one image in the project tree.
    - ``audio``: at least one audio file under ``audio/``.
    - ``re_edit``: at least one video under ``videos/`` (already present from asset).

    Returns an empty list when the phase passes its gate.
    """
    proj_dir = layout.resolve_project_dir(root, project_id)
    missing: list[tuple[str, Path]] = []

    if phase == "asset":
        videos = list((proj_dir / "videos").rglob("*.mp4"))
        images = list((proj_dir / "images").rglob("*"))
        images = [p for p in images if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
        if not videos and not images:
            missing.append(("video or image", proj_dir / "videos"))

    elif phase == "audio":
        audios = list((proj_dir / "audio").rglob("*"))
        audios = [p for p in audios if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg")]
        # A silent-track-only project is still acceptable if there are videos (voiceover optional)
        if not audios:
            videos = list((proj_dir / "videos").rglob("*.mp4"))
            if not videos:
                missing.append(("audio file", proj_dir / "audio"))

    elif phase == "re_edit":
        videos = list((proj_dir / "videos").rglob("*.mp4"))
        if not videos:
            missing.append(("video clip", proj_dir / "videos"))

    return missing


# ---------------------------------------------------------------------------
# prompt (generate cinematic prompts)
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--subject", "-s", required=True, help="Main subject (person, product, or object)")
@click.option("--action", "-a", required=True, help="What the subject does")
@click.option("--environment", "-e", required=True, help="Where the scene takes place")
@click.option("--shots", "-n", default=3, help="Number of shots (1-6, default: 3)")
@click.option(
    "--style",
    "-st",
    default="cinematic",
    type=click.Choice(list_video_styles()),
    help="Video style preset",
)
@click.option("--character", "-c", default=None, help="Character description for identity locking")
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Choice(["text", "code"]),
    help="Output format (default: text)",
)
@click.pass_context
def prompt(
    ctx: click.Context,
    subject: str,
    action: str,
    environment: str,
    shots: int,
    style: str,
    character: str | None,
    output: str | None,
) -> None:
    """Generate a cinematic video prompt for Agnes AI."""
    if shots < 1 or shots > 6:
        console.print("[red]Shots must be between 1 and 6.[/red]")
        sys.exit(1)

    if shots == 1:
        result = build_single_shot_prompt(
            subject=subject,
            action=action,
            environment=environment,
            style=style,
            character_description=character,
        )
    else:
        result = build_video_prompt(
            subject=subject,
            action=action,
            environment=environment,
            shots=shots,
            style=style,
            character_description=character,
        )

    console.print(
        f"\n[bold]Generated Prompt — {shots} shot"
        f"{'s' if shots > 1 else ''} ({style} style)[/bold]\n"
    )
    console.print(result)
    console.print("\n[dim]Tip: Use this prompt with 'brandly video' or copy it directly.[/dim]")


# ---------------------------------------------------------------------------
# audio
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--project-id", default=None, help="Optional project UUID")
@click.option("--prompt", "-p", required=True, help="Music description prompt")
@click.option("--model", default="music-3.0", help="Music generation model (music-3.0, music-2.6)")
@click.option("--duration", "-d", default=30, help="Duration in seconds")
@click.option("--instrumental", is_flag=True, default=True, help="Instrumental only")
@click.option("--lyrics", default=None, help="Song lyrics (\\n separated, max 3500 chars)")
@click.pass_context
def music(
    ctx: click.Context,
    project_id: str | None,
    prompt: str,
    model: str,
    duration: int,
    instrumental: bool,
    lyrics: str | None,
) -> None:
    """Generate background music via MiniMax Audio."""
    console.print(f"[dim]Generating music ({model}, {duration}s)...[/dim]")
    result = asyncio.run(
        generate_music(
            prompt, model=model, duration_seconds=duration, instrumental=instrumental, lyrics=lyrics
        )
    )
    url = result.get("url") or ""
    if url:
        console.print(f"[green]✓ Music generated:[/green] {url}")
        # Save to disk
        pid = project_id or ""
        root = _get_root(ctx)
        saved = _save_artifact(
            url, pid, "audio", root=root, prompt_hint=prompt, category="soundtrack"
        )
        if saved:
            console.print(f"  Saved → {saved}")
    _print_json(result)


@cli.command()
@click.option("--project-id", default=None, help="Optional project UUID")
@click.argument("text")
@click.option("--model", default="speech-2.8-hd", help="TTS model")
@click.option(
    "--voice-id",
    default="English_Insightful_Speaker",
    help="Voice ID (e.g. English_Insightful_Speaker)",
)
@click.option("--speed", default=1.0, help="Speech speed (0.5–2.0)")
@click.option("--vol", default=1.0, help="Volume (0.1-2.0)")
@click.option("--pitch", default=0, type=click.IntRange(-12, 12),
              help="Pitch shift in semitones (-12 to 12)")
@click.option("--emotion", default=None,
              help="Emotion tag: happy, sad, angry, fearful, neutral")
@click.pass_context
def tts(
    ctx: click.Context, project_id: str | None, text: str, model: str, voice_id: str,
    speed: float, vol: float, pitch: int, emotion: str | None,
) -> None:
    """Generate voiceover via MiniMax TTS."""
    console.print(f"[dim]Generating TTS ({model}, voice={voice_id})...[/dim]")
    result = asyncio.run(
        generate_tts(
            text, model=model, voice_id=voice_id, speed=speed,
            vol=vol, pitch=pitch, emotion=emotion,
        )
    )
    url = result.get("url") or ""
    if url:
        console.print(f"[green]✓ Voiceover generated:[/green] {url}")
        # Save to disk
        pid = project_id or ""
        root = _get_root(ctx)
        saved = _save_artifact(
            url,
            pid,
            "audio",
            root=root,
            prompt_hint=text[:60],
            category="voiceover",
        )
        if saved:
            console.print(f"  Saved → {saved}")
    _print_json(result)


@cli.command(name="voices")
@click.pass_context
def voices_cmd(ctx: click.Context) -> None:
    """List available TTS voices."""
    results = asyncio.run(list_voices())
    if results:
        table = Table(title="MiniMax TTS Voices")
        table.add_column("Voice ID", style="cyan")
        table.add_column("Language", style="white")
        table.add_column("Gender", style="dim")
        for v in results:
            table.add_row(v.get("voice_id", ""), v.get("language", ""), v.get("gender", ""))
        console.print(table)
    else:
        console.print("[dim]No voices found or API not configured.[/dim]")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("project_id")
@click.option("--video-path", default=None, help="Path to rendered video")
@click.pass_context
def validate(ctx: click.Context, project_id: str, video_path: str | None) -> None:
    """Run virality validation on a finished video."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    console.print(f"[dim]Validating project {project_id}...[/dim]")
    console.print("[yellow]Validation requires Higgsfield virality predictor MCP tool.[/yellow]")
    console.print(f"  Video path: {video_path or '(not provided)'}")
    _print_json(
        {
            "project_id": project_id,
            "video_path": video_path,
            "status": "validating",
            "message": "Virality validation initiated (requires higgsfield MCP tool)",
        }
    )



# ---------------------------------------------------------------------------
# gate (quality verification before the next step)
# ---------------------------------------------------------------------------


@cli.command(name="gate")
@click.argument("project_id")
@click.argument("element", default=None, required=False)
@click.option(
    "--ref",
    "reference",
    default=None,
    help="Reference image to compare against (drift check)",
)
@click.option(
    "--kind",
    type=click.Choice(["auto", "image", "video"]),
    default="auto",
    help="Element type (default: infer from extension)",
)
@click.option("--description", "-d", default="", help="Expected subject/description")
@click.option(
    "--matt-background/--no-matt-background",
    "expect_matt_background",
    default=None,
    help=(
        "Require a seamless matte mid-grey backdrop. "
        "Default: on for reference/sheet images, off for videos."
    ),
)
@click.option(
    "--use-ai/--no-ai",
    default=True,
    help="Use the Agnes multimodal model for visual analysis (default: on)",
)
@click.option("--strict", is_flag=True, help="Promote warnings to failures")
@click.option(
    "-o",
    "--output",
    type=click.Choice(["text", "json"]),
    default="text",
)
@click.pass_context
def gate(
    ctx: click.Context,
    project_id: str,
    element: str | None,
    reference: str | None,
    kind: str,
    description: str,
    expect_matt_background: bool | None,
    use_ai: bool,
    strict: bool,
    output: str,
) -> None:
    """Verify a generated element before proceeding (anti-slop/drift gate).

    Runs cheap offline pre-checks and a multimodal model analysis of the
    candidate (and optional reference). Exits 0 for pass, 1 for warn,
    2 for fail.
    """
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)

    from brandly_cli import quality_gate

    root = _get_root(ctx)

    # Resolve the element: explicit path, or auto-detect the newest media
    # artifact in the project.
    element_path: Path | None
    if element is None:
        element_path = _latest_project_media(root, project_id)
    else:
        element_path = Path(element)
    if element_path is None:
        console.print("[red]No element to verify. Pass a path or generate one first.[/red]")
        sys.exit(2)

    inferred_video = kind == "video" or quality_gate.is_video(element_path)

    # Auto-detect a project reference when not supplied.
    ref_path = reference
    if ref_path is None:
        ref = _load_project_reference(project_id, root)
        if ref:
            img = ref.get("image_path")
            if img and Path(img).exists():
                ref_path = img

    # A reference/sheet image expects a matte backdrop unless overridden.
    if expect_matt_background is None:
        expect_matt_background = not inferred_video

    result = asyncio.run(
        quality_gate.verify_element(
            element_path,
            reference=Path(ref_path) if ref_path else None,
            description=description,
            expect_matt_background=expect_matt_background,
            use_ai=use_ai,
            root=root,
            project_id=project_id,
            strict=strict,
        )
    )

    if output == "json":
        _print_json(result.to_dict())
    else:
        _print_gate_report(result)

    exit_code = 0 if result.status == quality_gate.PASS else (
        1 if result.status == quality_gate.WARN else 2
    )

    # Human-in-the-loop: confirm the gate result matches expectations before
    # the next step (a human can override a non-pass result).
    agree, note = _human_review_gate(
        "gate",
        f"the gate result ({result.status.upper()}) for {element_path.name}",
        default=result.status == quality_gate.PASS,
    )
    if note:
        _write_review_note(
            root,
            project_id,
            "gate",
            note,
            extra=f"element: {element_path}\ngate status: {result.status}\n",
        )
    if not agree:
        if result.status != quality_gate.PASS:
            try:
                override = click.confirm(
                    f"[gate] Override the {result.status} result and continue anyway?",
                    default=False,
                )
            except click.exceptions.Abort:
                override = False
            if override:
                console.print(
                    f"[yellow]⚠ Human override: continuing despite the "
                    f"{result.status} result.[/yellow]"
                )
                exit_code = 0
            else:
                console.print(
                    "[red]✗ Gate result not approved — rework the element "
                    "and re-run the gate.[/red]"
                )
        else:
            console.print(
                "[red]✗ PASS result not confirmed — treat the element as "
                "rework until it matches expectations.[/red]"
            )
            exit_code = 1

    sys.exit(exit_code)


def _latest_project_media(root: Path, project_id: str) -> Path | None:
    """Return the most recently modified media file under the project tree."""
    proj_dir = layout.resolve_project_dir(root, project_id)
    if not proj_dir.exists():
        return None
    media_exts = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".mov"}
    files: list[Path] = []
    for top in ("images", "videos", "audio"):
        base = proj_dir / top
        if base.exists():
            for f in base.rglob("*"):
                if f.is_file() and f.suffix.lower() in media_exts:
                    files.append(f)
    if not files:
        return None
    return max(files, key=lambda pth: pth.stat().st_mtime)


def _print_gate_report(result: Any) -> None:
    from brandly_cli import quality_gate

    color = {
        quality_gate.PASS: "green",
        quality_gate.WARN: "yellow",
        quality_gate.FAIL: "red",
    }
    mark = {quality_gate.PASS: "✓", quality_gate.WARN: "⚠", quality_gate.FAIL: "✗"}
    console.print(
        f"[{color[result.status]}]{mark[result.status]} GATE {result.status.upper()}"
        f"[/] [{result.score}/100] {result.kind} → {result.element}"
    )
    if result.issues:
        console.print(f"[red]Failures ({len(result.issues)}):[/red]")
        for i in result.issues:
            console.print(f"  [red]✗ {i}[/red]")
    if result.warnings:
        console.print(f"[yellow]Warnings ({len(result.warnings)}):[/yellow]")
        for w in result.warnings:
            console.print(f"  [yellow]⚠ {w}[/yellow]")
    if result.ai:
        console.print(
            f"[dim]AI verdict: {result.ai.get('verdict', '?')} — "
            f"{result.ai.get('notes', '')}[/dim]"
        )
    console.print(
        "[dim]Report: .brandly/<project>/docs/tmp/ (gate_<kind>_<ts>.md)[/dim]"
    )


def _human_review_gate(stage: str, label: str, default: bool = True) -> tuple[bool, str]:
    """Human-in-the-loop gate: ask up to 3 questions before continuing.

    Confirms the generated result matches what's expected. In
    non-interactive mode (EOF on stdin) the defaults are used, so piped
    runs auto-approve unless input is provided.

    Returns:
        (approved, note) — ``approved`` is False when the result was
        rejected, ``note`` carries the optional free-text issue.
    """
    try:
        q1 = click.confirm(
            f"[{stage} gate] Does {label} match what you expected?", default=default
        )
    except click.exceptions.Abort:
        q1 = default
    if q1:
        try:
            q2 = click.confirm(
                f"[{stage} gate] Approve {label} and continue to the next step?",
                default=True,
            )
        except click.exceptions.Abort:
            q2 = True
        return q2, ""
    try:
        note = click.prompt(
            f"[{stage} gate] What didn't match? (short note)",
            default="no note",
            show_default=False,
        )
    except click.exceptions.Abort:
        note = "no note (non-interactive)"
    return False, note


def _write_review_note(
    root: Path, project_id: str, stage: str, note: str, extra: str = ""
) -> Path:
    """Save a human-gate review note under ``docs/tmp`` for the record."""
    docs_dir = layout.docs_dir(layout.project_dir(root, project_id), "tmp")
    docs_dir.mkdir(parents=True, exist_ok=True)
    ts = now_iso().replace(":", "-").replace(".", "_")
    note_path = docs_dir / f"review_{stage}_{ts}.md"
    note_path.write_text(
        f"# Human Gate Review: {stage}\n\n"
        f"**Status:** REJECTED\n"
        f"**Note:** {note}\n\n"
        f"{extra}\n",
        encoding="utf-8",
    )
    return note_path



# ---------------------------------------------------------------------------
# progress
# ---------------------------------------------------------------------------


@cli.command()
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


# ---------------------------------------------------------------------------
# memory
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("action", type=click.Choice(["view", "like", "dislike", "reset"]))
@click.argument("hook", default=None, required=False)
@click.pass_context
def memory(ctx: click.Context, action: str, hook: str | None) -> None:
    """View or update user preferences."""
    root = _get_root(ctx)
    mem = UserPreferences(root)
    if action == "view":
        prefs = mem.get()
        console.print("[bold]User Preferences[/bold]")
        for k, v in prefs.items():
            console.print(f"  {k}: {v}")
    elif action == "like" and hook:
        mem.like_hook(hook)
        console.print(f"[green]✓ Liked hook:[/green] {hook}")
    elif action == "dislike" and hook:
        mem.dislike_hook(hook)
        console.print(f"[yellow]Disliked hook:[/yellow] {hook}")
    elif action == "reset":
        mem.reset()
        console.print("[dim]Memory reset.[/dim]")
    else:
        console.print("[red]Usage: brandly memory view|like|dislike|reset [HOOK][/red]")


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("project_id")
@click.option(
    "--output",
    "-o",
    default=None,
    help="Output directory (default: .brandly/{id}/export/)",
)
@click.pass_context
def export(ctx: click.Context, project_id: str, output: str | None) -> None:
    """Export a completed project's artifacts."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    pm = ProjectManager(root)
    proj = asyncio.run(pm.read(project_id))
    if not proj:
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)

    proj_dir = layout.resolve_project_dir(root, project_id)
    out_dir = Path(output) if output else proj_dir / "export"
    out_dir = out_dir.resolve()
    proj_dir_resolved = proj_dir.resolve()

    # Guard: if out_dir is the same as or an ancestor of proj_dir, copying would
    # recurse into itself. Error loudly so the user knows to pick a sibling dir.
    try:
        proj_dir_resolved.relative_to(out_dir)
        console.print(
            f"[red]Export aborted: output dir ({out_dir}) is the same as or an "
            f"ancestor of the project dir ({proj_dir_resolved}).[/red]\n"
            f"  Use a sibling or sub-folder, e.g. `--output {proj_dir_resolved.parent / 'export'}`"
        )
        sys.exit(1)
    except ValueError:
        pass  # out_dir is NOT an ancestor — proceed normally

    # Bookkeeping files at the project root are excluded from the export
    # by only scanning the user-facing top folders (images/videos/audio/docs).

    artifact_count = 0
    media_count = 0
    media_exts = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".mp3", ".wav", ".mpga"}
    # User-facing media + docs live in these top folders of the project dir
    # (reference images are included via their images/ sub-folder).
    for search_dir in [
        proj_dir / "images",
        proj_dir / "videos",
        proj_dir / "audio",
        proj_dir / "docs",
    ]:
        if not search_dir.exists():
            continue
        for f in search_dir.rglob("*"):
            if not f.is_file():
                continue
            # Skip files inside the export output directory to avoid recursion
            try:
                f.resolve().relative_to(out_dir)
                continue
            except ValueError:
                pass
            ext = f.suffix.lower()
            rel = f.relative_to(proj_dir)
            dest = out_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            import shutil

            shutil.copy2(f, dest)
            if ext in media_exts:
                media_count += 1
            else:
                artifact_count += 1

    if artifact_count == 0 and media_count == 0:
        console.print("[yellow]No artifacts to export.[/yellow]")
        console.print("[dim]The project has no media or doc files under images/, videos/, audio/, or docs/.[/dim]")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    from brandly_cli.types import ExportManifest

    manifest = ExportManifest(
        project_id=project_id,
        project_name=proj.name,
        style=proj.style,
        shot_count=proj.shot_count,
        budget=proj.budget,
        spent=proj.spent,
        target_platforms=proj.target_platforms,
        created_at=proj.created_at,
        exported_at=now_iso(),
        artifact_count=artifact_count,
        media_count=media_count,
        total_files=artifact_count + media_count,
    )
    manifest_path = out_dir / "export-manifest.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(), indent=2))

    console.print(
        f"[green]✓ Exported[/green] {artifact_count} artifacts + {media_count} media → {out_dir}"
    )
    console.print(f"  Manifest: {manifest_path}")


# ---------------------------------------------------------------------------
# cost
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("project_id")
@click.pass_context
def cost(ctx: click.Context, project_id: str) -> None:
    """Show cost summary for a project."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    ct = CostTracker(root / ".brandly")
    try:
        summary = asyncio.run(ct.get_summary(project_id))
    except FileNotFoundError:
        console.print(f"[yellow]No cost data found for project {project_id}.[/yellow]")
        console.print("  Run `brandly record-cost` to log spending,")
        console.print("  or initialize with `brandly init`.")
        sys.exit(0)
    _print_json(summary)


@cli.command()
@click.argument("project_id")
@click.argument("phase")
@click.argument("action")
@click.argument("credits", type=int)
@click.pass_context
def record_cost(ctx: click.Context, project_id: str, phase: str, action: str, credits: int) -> None:
    """Record actual credit spend for a phase operation."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    pm = ProjectManager(root)
    proj = asyncio.run(pm.read(project_id))
    if not proj:
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)
    ct = CostTracker(root / ".brandly")
    try:
        result = asyncio.run(
            ct.record_spend(project_id, phase, action, credits, budget_credits=proj.budget)
        )
        # Sync ProjectData.spent so brandly status shows the correct spend
        asyncio.run(pm.update(project_id, {"spent": result["total_spent"]}))
        console.print(f"[green]✓ Recorded[/green] {credits} credits for {phase}/{action}")
        console.print(
            f"  Total spent: {result['total_spent']}/{result['budget']}  "
            f"Remaining: {result['remaining']}"
        )
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# cancel / pause / resume
# ---------------------------------------------------------------------------


@cli.command()
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


@cli.command()
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


@cli.command()
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


# ---------------------------------------------------------------------------
# director (orchestrator)
# ---------------------------------------------------------------------------


@cli.command()
@click.pass_context
def director(ctx: click.Context) -> None:
    """Show the Director prompt for AI tools."""
    prompt = get_director_prompt()
    console.print(Panel(Markdown(prompt), title="Brandly Director Mode"))


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------


@cli.command()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Show current configuration (API keys status, root dir)."""
    root = _get_root(ctx)
    from rich.table import Table

    table = Table(title="Brandly Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Root directory", str(root))
    agnes_key = os.getenv("AGNES_API_KEY")
    minimax_key = os.getenv("MINIMAX_API_KEY")
    table.add_row("AGNES_API_KEY", "set" if agnes_key else "not set")
    table.add_row("MINIMAX_API_KEY", "set" if minimax_key else "not set")
    table.add_row("AGNES_BASE_URL", os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1"))
    table.add_row("MINIMAX_BASE_URL", os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1"))
    table.add_row("Version", __version__)
    console.print(table)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for brandly CLI — catches unhandled exceptions and offers to report."""
    try:
        cli()
    except Exception as exc:
        # Let Click handle its own exit codes for --help, bad args, etc.
        if isinstance(exc, SystemExit):
            raise
        if sys.stdout.isatty() or sys.stderr.isatty():
            from brandly_cli.issue_tracker import report_from_exception
            report_from_exception(exc)
        else:
            raise


@cli.command()
@click.option(
    "--tools", default=None, help="Comma-separated tool names to sync (default: all detected)"
)
@click.option("--dry-run", is_flag=True, help="Show what would be synced without writing")
@click.pass_context
def sync(ctx: click.Context, tools: str | None, dry_run: bool) -> None:
    """Auto-detect AI-tool configs and write Brandly API keys into them.

    Reads AGNES_API_KEY and MINIMAX_API_KEY from the current environment,
    then writes them into the configuration files of supported AI tools
    so they can use Agnes AI (image/video) and MiniMax (audio) directly.

    Supported tools: qwen, claude, gemini, codex, pi, opencode
    """
    from rich.panel import Panel
    from rich.table import Table

    # Detect which tools have config dirs
    detected = detect_tools()
    table = Table(title="Detected AI Tool Configs")
    table.add_column("Tool", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Path", style="dim")
    for name, exists in detected.items():
        status = "found" if exists else "missing"
        table.add_row(name, status, str(TOOLS.get(name, "")))
    console.print(table)
    console.print()

    # Resolve which tools to sync
    selected = None
    if tools:
        selected = [t.strip().lower() for t in tools.split(",")]
        unknown = [t for t in selected if t not in SYNC_HANDLERS]
        if unknown:
            console.print(f"[red]Unknown tools: {', '.join(unknown)}. ", end="")
            console.print(f"Available: {', '.join(SYNC_HANDLERS.keys())}[/red]")
            sys.exit(1)

    agnes = os.getenv("AGNES_API_KEY")
    minimax = os.getenv("MINIMAX_API_KEY")
    if not agnes and not minimax:
        console.print(
            "[red]No API keys found. Set AGNES_API_KEY and/or MINIMAX_API_KEY first.[/red]"
        )
        sys.exit(1)

    console.print(f"[dim]AGNES_API_KEY: {'set' if agnes else 'not set'}[/dim]")
    console.print(f"[dim]MINIMAX_API_KEY: {'set' if minimax else 'not set'}[/dim]")
    console.print()

    if dry_run:
        console.print("[yellow]Dry-run mode — no files will be written.[/yellow]")

    messages = sync_keys(tools=selected, include_dotenv=not dry_run)
    if messages:
        console.print(Panel("\n".join(messages), title="Sync Result"))
    else:
        console.print("[dim]Nothing to sync.[/dim]")


# ---------------------------------------------------------------------------
# models — list available AI models
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "-c",
    "--category",
    type=click.Choice(["image", "video", "audio", "all"]),
    default="all",
    help="Filter by category",
)
@click.option(
    "-q",
    "--query",
    default=None,
    help="Search models by name or provider",
)
@click.option(
    "-o",
    "--output",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def models(category: str, query: str | None, output: str) -> None:
    """List all available AI generation models."""
    all_models = get_all_models()
    results: dict[str, list[dict[str, Any]]] = {}

    cats = ["image", "video", "audio"] if category == "all" else [category]
    for cat in cats:
        models_list = all_models.get(cat, [])
        if query:
            q = query.lower()
            models_list = [
                m
                for m in models_list
                if q in m["name"].lower()
                or q in m["provider"].lower()
                or any(q in f.lower() for f in m.get("features", []))
            ]
        if models_list:
            results[cat] = models_list

    if output == "json":
        _print_json(results)
        return


    for cat, models_list in results.items():
        table = Table(title=f"{cat.title()} Models ({len(models_list)})")
        table.add_column("ID", style="cyan", max_width=28)
        table.add_column("Name", style="white")
        table.add_column("Provider", style="dim")
        table.add_column("Quality", style="green")
        table.add_column("Cost", style="yellow")
        table.add_column("Features", style="dim")
        for m in models_list:
            table.add_row(
                m["id"],
                m["name"],
                m.get("provider", ""),
                m.get("quality", ""),
                f"{m.get('cost', '?')} credits",
                ", ".join(m.get("features", [])[:3]),
            )
        console.print(table)
        console.print()


@cli.command()
@click.argument("model_id")
@click.option("-o", "--output", type=click.Choice(["text", "json"]), default="text")
def model(model_id: str, output: str) -> None:
    """Show detailed info about a specific AI model."""
    info = get_model_info(model_id)
    if not info:
        console.print(f"[red]Model not found: {model_id}[/red]")
        console.print("  Use 'brandly models' to see available models.")
        sys.exit(1)
    if output == "json":
        _print_json(info)
        return
    from rich.panel import Panel as RPanel

    sections = [
        (f"[bold cyan]{info['name']}[/bold cyan]", ""),
        ("Provider", info.get("provider", "")),
        ("Category", f"{info.get('category', '')} / {info.get('subtype', 'general')}"),
        ("Description", info.get("description", "")),
        ("Cost", f"{info.get('cost_credits', '?')} credits"),
        ("Features", ", ".join(info.get("features", []))),
    ]
    extra = {
        "max_duration": "max_duration",
        "max_resolution": "max_resolution",
        "speed": "speed",
        "quality": "quality",
    }
    for key, label in extra.items():
        if key in info:
            sections.append((label.title(), str(info[key])))
    lines = []
    for label, value in sections:
        if label and value:
            lines.append(f"[bold]{label}:[/bold] {value}")
        elif label:
            lines.append(f"[bold]{label}:[/bold]")
    console.print(RPanel("\n".join(lines), title=f"Model: {model_id}"))


@cli.command(name="rate-limits")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def rate_limits(output: str) -> None:
    """Show provider rate limits for Agnes AI and MiniMax.

    Values mirror the official documentation (Agnes Token Plan FAQ + MiniMax
    rate-limits page). Use these to plan batch / parallel generation.
    """
    if output == "json":
        # Emit raw, non-wrapped JSON so it is directly parseable.
        console.print(
            json.dumps(PROVIDER_RATE_LIMITS, indent=2, ensure_ascii=False),
            soft_wrap=True,
        )
        return

    for provider, limits in PROVIDER_RATE_LIMITS.items():
        table = Table(title=f"{provider} rate limits")
        table.add_column("Limit", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Notes", style="dim")
        for key, value in limits.items():
            if key in ("docs",):
                continue
            notes = ""
            if key == "image_rpm_by_size":
                value = " | ".join(f"{sz}:{rpm}" for sz, rpm in value.items())
                notes = "effective RPM on a free/default key"
            elif key == "h3_concurrent_tasks_free":
                notes = "parallel H3 video tasks (free tier)"
            elif key == "h3_concurrent_tasks_paid":
                notes = "parallel H3 video tasks (paid)"
            table.add_row(key, str(value), notes)
        console.print(table)
        console.print(f"[dim]Source: {limits.get('docs', '')}[/dim]")
        console.print()


# ---------------------------------------------------------------------------
# jobs — list/cancel async video jobs
# ---------------------------------------------------------------------------


@cli.command()
@click.option("-s", "--status", default=None, help="Filter by status (pending, completed, failed)")
@click.option("-n", "--limit", default=20, help="Max number of jobs to show")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def jobs(status: str | None, limit: int, output: str) -> None:
    """List recent video generation jobs from the API."""
    async def _jobs(status: str | None, limit: int, output: str) -> None:
        job_list = await list_jobs(status=status, limit=limit)
        if output == "json":
            _print_json(job_list)
            return
        if not job_list:
            console.print("[dim]No jobs found.[/dim]")
            return
        table = Table(title=f"Video Jobs ({len(job_list)})")
        table.add_column("ID", style="cyan", max_width=20)
        table.add_column("Status", style="green")
        table.add_column("Progress", style="yellow")
        table.add_column("Model", style="dim")
        table.add_column("Prompt Preview", style="dim")
        table.add_column("Created", style="dim")
        for j in job_list:
            table.add_row(
                j["video_id"][:20],
                j["status"],
                f"{j['progress']}%",
                j.get("model", ""),
                (j.get("prompt", "") or "")[:40],
                (j.get("created_at", "") or "")[:16],
            )
        console.print(table)
        console.print("[dim]Tip: Use 'brandly job-resume <id>' to poll for completion[/dim]")
    asyncio.run(_jobs(status, limit, output))


def _find_project_by_video_id(root: Path, video_id: str) -> str | None:
    """Find the project whose project.json records the given video_id."""
    brandly = layout.brandly_dir(root)
    if not brandly.exists():
        return None
    for proj_file in sorted(brandly.glob("*/project.json")):
        try:
            raw = proj_file.read_text(encoding="utf-8")
        except OSError:
            continue
        if video_id in raw:
            return proj_file.parent.name
    return None


@cli.command()
@click.argument("video_id")
@click.option(
    "--project-id",
    default=None,
    help="Project to save the video under (default: auto-detect from project.json)",
)
@click.option("--max-wait", default=600, help="Max wait seconds while polling (default: 600)")
@click.option(
    "--model",
    default="agnes-video-2.5-flash",
    help="Agnes video model name used when polling (2.5-flash is the current default)",
)
@click.option("--no-download", is_flag=True, help="Only report status, do not download the video")
@click.pass_context
def job_resume(
    ctx: click.Context,
    video_id: str,
    project_id: str | None,
    max_wait: int,
    model: str,
    no_download: bool,
) -> None:
    """Poll a video job to completion and download the video to disk.

    If the job is still running, polls until it completes (or --max-wait is
    reached). Once a URL is available the video is downloaded to
    .brandly/<project>/videos/scenes/ — use --no-download to skip saving.
    """
    from brandly_cli.agnes_client import get_video_status, poll_video

    root = _get_root(ctx)

    # Locate the owning project (explicit, auto-detected, or none).
    if project_id is not None and not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    if project_id is None:
        project_id = _find_project_by_video_id(root, video_id)

    console.print(f"[dim]Checking status for {video_id}...[/dim]")
    try:
        result = asyncio.run(get_video_status(video_id, model_name=model))
    except Exception as e:
        console.print(f"[red]Status check failed: {e}[/red]")
        console.print(
            "[dim]If the job is still queued, retry later — polling retries "
            "rate-limit errors automatically.[/dim]"
        )
        sys.exit(1)

    status = result.get("status", "unknown")
    console.print(f"  Status: {status}")
    console.print(f"  Progress: {result.get('progress', 0)}%")
    if result.get("error"):
        console.print(f"[red]  Error: {result['error']}[/red]")

    # Poll until completion if still in progress.
    if status not in ("completed", "failed"):
        console.print(f"[dim]Job still running — polling (max {max_wait}s)...[/dim]")
        try:
            result = asyncio.run(
                poll_video(video_id, max_wait_seconds=max_wait, model_name=model)
            )
        except TimeoutError as e:
            console.print(f"[yellow]⚠ {e}[/yellow]")
            console.print(f"[dim]Re-run 'brandly job-resume {video_id}' later.[/dim]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error polling video: {e}[/red]")
            sys.exit(1)
        status = result.get("status", "unknown")
        console.print(f"  Status: {status}")

    if status == "failed":
        console.print(f"[red]✗ Job failed: {result.get('error') or 'unknown error'}[/red]")
        sys.exit(1)
    if status != "completed":
        console.print(f"[yellow]⚠ Job not completed yet (status: {status}).[/yellow]")
        console.print(f"[dim]Re-run 'brandly job-resume {video_id}' later.[/dim]")
        return

    url = result.get("url") or ""
    console.print(f"[green]  URL: {url or 'none'}[/green]")
    if not url:
        console.print("[yellow]⚠ No download URL available for this job.[/yellow]")
        return
    if no_download:
        return

    if project_id is None:
        console.print(
            "[yellow]⚠ Could not detect the owning project — passing "
            "--project-id will save the video to the project tree.[/yellow]"
        )
        console.print(f"[dim]URL: {url}[/dim]")
        return

    saved = _save_artifact(
        url,
        project_id,
        "videos",
        root=root,
        prompt_hint=video_id[:20],
        category="scenes",
    )
    if saved:
        console.print(f"[green]✓ Video downloaded:[/green] {saved}")
        pm = ProjectManager(root)
        asyncio.run(
            pm.update(
                project_id,
                {
                    "last_video_job": {
                        "video_id": video_id,
                        "url": url,
                        "saved_path": str(saved),
                        "model": model,
                        "created_at": now_iso(),
                    }
                },
            )
        )
        # Mark the newest video plan COMPLETED in the production plan.
        plan_dir = layout.docs_dir(layout.project_dir(root, project_id), "plan")
        plan_files = sorted(plan_dir.glob("plan_video_*.md")) if plan_dir.exists() else []
        if plan_files:
            from brandly_cli.utils import upsert_production_plan

            upsert_production_plan(
                project_id,
                root=root,
                plan_file=str(plan_files[-1]),
                asset_type="video",
                model=model,
                status="COMPLETED",
                source="brandly job-resume",
            )
    else:
        console.print("[yellow]⚠ Could not save the video, but the URL is available.[/yellow]")
        console.print(f"[dim]URL: {url}[/dim]")


@cli.command()
@click.argument("video_id")
def job_cancel(video_id: str) -> None:
    """Cancel a pending video generation job."""
    result = asyncio.run(cancel_job(video_id))
    if result.get("status") == "cancelled":
        console.print(f"[green]✓ Job {video_id} cancelled successfully.[/green]")
    else:
        console.print(f"[red]✗ Failed to cancel job: {result.get('error', 'unknown error')}[/red]")


# ---------------------------------------------------------------------------
# agnes-chat — Agnes text/agent tool-calling
# ---------------------------------------------------------------------------


@cli.command(name="agnes-chat")
@click.argument("prompt")
@click.option("--model", default="agnes-2.5-flash",
              help="Agnes text model (2.5-flash, 2.0-flash, 1.5-flash)")
@click.option("--tools", is_flag=True,
              help="Enable built-in tools (projects, jobs, models, image gen)")
@click.option("--list-models", "list_models_flag", is_flag=True,
              help="List available Agnes text models and exit")
@click.option("--list-tools", "list_tools_flag", is_flag=True,
              help="List built-in agent tools and exit")
@click.option("-o", "--output", type=click.Choice(["text", "json"]), default="text")
def agnes_chat(
    prompt: str,
    model: str,
    tools: bool,
    list_models_flag: bool,
    list_tools_flag: bool,
    output: str,
) -> None:
    """Chat with an Agnes AI text model, optionally as a tool-calling agent.

    With --tools the model can call built-in tools (list_projects, get_project,
    list_jobs, generate_image, list_models) and reason over their results in a
    multi-turn agent loop. Requires AGNES_API_KEY.
    """
    if list_models_flag:
        for m in list_text_models():
            console.print(
                f"  [bold]{m['id']}[/bold]  ctx={m['context']} out={m['max_output']}"
            )
            console.print(f"    [dim]{m['use']}[/dim]")
        return

    if list_tools_flag:
        from brandly_cli.agent_tools import describe_tools

        for name, spec in describe_tools().items():
            console.print(f"  [bold]{name}[/bold] - {spec['description']}")
        return

    if not os.getenv("AGNES_API_KEY"):
        console.print(
            "[red]AGNES_API_KEY is not set. Get one from https://apihub.agnes-ai.com,"
            " or use --list-models / --list-tools (no key required).[/red]"
        )
        sys.exit(1)

    tool_specs = get_builtin_tools() if tools else None
    messages = [{"role": "user", "content": prompt}]
    if tool_specs:
        result = asyncio.run(agent_tool_loop(messages, tool_specs, model=model))
        if output == "json":
            _print_json(result)
            return
        iterations = result.get("iterations", 1)
        console.print(
            f"[bold]Agnes agent: {model}[/bold]  ({iterations} iteration(s))"
        )
        console.print(result.get("content") or "(no content)")
    else:
        from brandly_cli.agnes_client import chat_completion

        data = asyncio.run(chat_completion(messages, model=model))
        if output == "json":
            _print_json(data)
            return
        msg = (data.get("choices") or [{}])[0].get("message") or {}
        console.print(msg.get("content") or "(no content)")


# ---------------------------------------------------------------------------
# edit — video editing with FFmpeg
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--start", default=0.0, help="Start time in seconds")
@click.option("--end", default=None, help="End time in seconds")
@click.option("--duration", default=None, help="Duration in seconds (alternative to --end)")
@click.option("--codec", default="libx264", help="Video codec")
@click.option("--preset", default="fast", help="Encoding preset")
def edit(
    input: str,
    output: str,
    start: float,
    end: float | None,
    duration: float | None,
    codec: str,
    preset: str,
) -> None:
    """Trim a video to a segment."""
    async def _edit(input, output, start, end, duration, codec, preset):
        result = await trim_video(
            input, output, start=start, end=end,
            duration=duration, codec=codec, preset=preset,
        )
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        console.print(f"[green]✓ Trimmed to {output}[/green]")
        console.print(f"  Duration: {result.get('duration_seconds', '?')}s")
        console.print(f"  Size: {human_size(result.get('size_bytes', 0))}")
    asyncio.run(_edit(input, output, start, end, duration, codec, preset))


@cli.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--width", default=None, type=int, help="Target width in pixels")
@click.option("--height", default=None, type=int, help="Target height in pixels")
@click.option("--aspect", default=None, help="Aspect ratio (16:9, 9:16, 1:1, 4:3)")
@click.option("--codec", default="libx264", help="Video codec")
def resize(
    input: str,
    output: str,
    width: int | None,
    height: int | None,
    aspect: str | None,
    codec: str,
) -> None:
    """Resize a video to given dimensions or aspect ratio."""
    async def _resize(input, output, width, height, aspect, codec):
        result = await resize_video(
            input, output, width=width, height=height,
            aspect=aspect, codec=codec,
        )
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        console.print(f"[green]✓ Resized to {output}[/green]")
        if width:
            console.print(f"  Width: {width}px")
        if height:
            console.print(f"  Height: {height}px")
    asyncio.run(_resize(input, output, width, height, aspect, codec))


@cli.command()
@click.argument("inputs", nargs=-1, required=True, type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--codec", default="libx264", help="Video codec")
def concat(inputs: tuple[str, ...], output: str, codec: str) -> None:
    """Concatenate multiple videos into one."""
    async def _concat(inputs, output, codec):
        result = await concatenate_videos(list(inputs), output, codec=codec)
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        console.print(
            f"[green]✓ Concatenated {result.get('input_count', len(inputs))} "
            f"videos → {output}[/green]"
        )
        console.print(f"  Duration: {result.get('duration_seconds', '?')}s")
    asyncio.run(_concat(inputs, output, codec))


@cli.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--format", "fmt", default="mp3", help="Audio format (mp3, wav, m4a)")
@click.option("--bitrate", default="192k", help="Audio bitrate")
def audio(input: str, output: str, fmt: str, bitrate: str) -> None:
    """Extract audio track from a video file."""
    async def _audio(input, output, fmt, bitrate):
        result = await extract_audio(input, output, format=fmt, bitrate=bitrate)
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        console.print(f"[green]✓ Audio extracted to {output}[/green]")
        console.print(f"  Format: {fmt}")
        console.print(f"  Bitrate: {bitrate}")
    asyncio.run(_audio(input, output, fmt, bitrate))


@cli.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.argument("text")
@click.option("--font-size", default=24, type=int)
@click.option("--position", default="bottom", type=click.Choice(["top", "middle", "bottom"]))
@click.option("--codec", default="libx264")
def captions(
    input: str,
    output: str,
    text: str,
    font_size: int,
    position: str,
    codec: str,
) -> None:
    """Add burned-in subtitles to a video."""
    async def _captions(input, output, text, font_size, position, codec):
        result = await add_subtitles(
            input, output, text,
            font_size=font_size, position=position, codec=codec,
        )
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        console.print(f"[green]✓ Subtitles added to {output}[/green]")
    asyncio.run(_captions(input, output, text, font_size, position, codec))


@cli.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.argument("speed", type=float)
@click.option("--codec", default="libx264")
def speed(
    input: str, output: str, speed: float, codec: str
) -> None:
    """Change video playback speed."""
    async def _speed(input, output, speed, codec):
        result = await change_speed(input, output, speed, codec=codec)
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        console.print(f"[green]✓ Speed changed to {speed}x → {output}[/green]")
    asyncio.run(_speed(input, output, speed, codec))


# ---------------------------------------------------------------------------
# analyze — video metadata analysis
# ---------------------------------------------------------------------------


@cli.command(name="probe")
@click.argument("input", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def probe(input: str, output: str) -> None:
    """Analyze a video file's metadata and properties."""
    info = asyncio.run(get_video_info(input))
    if "error" in info:
        console.print(f"[red]Error: {info['error']}[/red]")
        sys.exit(1)
    if output == "json":
        _print_json(info)
        return
    table = Table(title=f"Video Analysis: {Path(input).name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Duration", f"{info.get('duration_seconds', 0):.1f}s")
    table.add_row("Size", human_size(info.get("size_bytes", 0)))
    table.add_row("Resolution", f"{info.get('video_width', 0)}×{info.get('video_height', 0)}")
    table.add_row("Aspect Ratio", info.get("video_aspect", ""))
    table.add_row("Frame Rate", info.get("video_fps", ""))
    table.add_row("Video Codec", info.get("video_codec", ""))
    table.add_row("Audio Codec", info.get("audio_codec", "none"))
    table.add_row("Has Audio", "yes" if info.get("has_audio") else "no")
    table.add_row("Format", info.get("format", ""))
    console.print(table)


# ---------------------------------------------------------------------------
# batch — generate multiple variants
# ---------------------------------------------------------------------------


@cli.command()
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
                task = await create_video_task(
                    variant_prompt,
                    model=model,
                    duration=5,
                    aspect_ratio="16:9",
                    reference_images=imgs,
                    # Parity with `brandly video` (issue #21 fix): cinematic
                    # style keeps the cinematic preset, others get none.
                    style_preset="cinematic" if style == "cinematic" else None,
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


# ---------------------------------------------------------------------------
# compare — compare generations side by side
# ---------------------------------------------------------------------------


@cli.command()
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
# version
# ---------------------------------------------------------------------------


@cli.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold]brandly-cli[/bold] v{__version__}")
    console.print(f"  Python: {sys.version.split()[0]}")
    console.print(f"  Platform: {sys.platform}")
    ffmpeg_ok = _ffmpeg_available()
    ffprobe_ok = _ffprobe_available()
    console.print(f"  FFmpeg: {'✓' if ffmpeg_ok else '✗ (install for edit/captions/concat)'}")
    console.print(f"  FFprobe: {'✓' if ffprobe_ok else '✗ (install for analyze)'}")


def _ffmpeg_available() -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _ffprobe_available() -> bool:
    try:
        result = subprocess.run(
            ["ffprobe", "-version"], capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ---------------------------------------------------------------------------
# minimax — MiniMax AI generation commands
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("prompt")
@click.option("--model", default="image-01", help="Model ID (image-01 or image-01-live)")
@click.option("--ratio", default="16:9",
              help="Aspect ratio (1:1, 16:9, 4:3, 3:2, 2:3, 3:4, 9:16, 21:9)")
@click.option("--width", default=None, type=int, help="Image width in px (512-2048)")
@click.option("--height", default=None, type=int, help="Image height in px (512-2048)")
@click.option("-n", "--count", default=1,
              type=click.IntRange(1, 9), help="Number of images to generate")
@click.option("--subject", default=None, help="Subject reference image URL for i2i generation")
@click.option("--seed", default=None, type=int, help="Seed for reproducible generations")
@click.option("--style", "style_setting", default=None,
              help="Art style for image-01-live (e.g. cinematic, anime, oil-painting)")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def minimax_image(
    prompt: str,
    model: str,
    ratio: str,
    width: int | None,
    height: int | None,
    count: int,
    subject: str | None,
    seed: int | None,
    style_setting: str | None,
    output: str,
) -> None:
    """Generate images using MiniMax API."""
    async def _minimax_image(prompt, model, ratio, width, height, count, subject, seed, style_setting, output):
        subject_ref = None
        if subject:
            subject_ref = [{"type": "character", "image_file": subject}]

        style_obj = {"style": style_setting} if style_setting else None

        result = await minimax_generate_image(
            prompt,
            model=model,
            aspect_ratio=ratio,
            width=width,
            height=height,
            n=count,
            subject_reference=subject_ref,
            seed=seed,
            image_style_setting=style_obj,
        )

        if output == "json":
            _print_json(result)
            return

        console.print("[bold]MiniMax Image Generation[/bold]")
        console.print(f"  Model: {result.get('model', model)}")
        console.print(f"  Success: {result.get('success_count', 0)}")
        console.print(f"  Failed: {result.get('failed_count', 0)}")
        urls = result.get("urls", [])
        if urls:
            console.print("[bold]Generated Images:[/bold]")
            for i, url in enumerate(urls, 1):
                console.print(f"  {i}. [link={url}]{url}[/link]")
        else:
            console.print("[yellow]No images generated.[/yellow]")
    asyncio.run(_minimax_image(prompt, model, ratio, width, height, count, subject, seed, style_setting, output))


@cli.command()
@click.argument("prompt")
@click.option("--model", default="MiniMax-H3", help="Model (MiniMax-H3 or MiniMax-H3-Max)")
@click.option("--resolution", default="768P", help="Resolution (480P, 768P, 2K)")
@click.option("--duration", default=5, type=click.IntRange(4, 15), help="Duration in seconds")
@click.option("--ratio", default="adaptive", help="Aspect ratio")
@click.option("--first-frame", default=None, help="First frame image URL or local file path")
@click.option("--last-frame", default=None, help="Last frame image URL or local file path")
@click.option("--reference-images", default=None, help="Comma-separated reference image URLs or local file paths")
@click.option("--reference-videos", default=None, help="Comma-separated reference video URLs")
@click.option("--reference-audios", default=None, help="Comma-separated reference audio URLs")
@click.option("--wait", is_flag=True, help="Wait for completion")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def minimax_video(
    prompt: str,
    model: str,
    resolution: str,
    duration: int,
    ratio: str,
    first_frame: str | None,
    last_frame: str | None,
    reference_images: str | None,
    reference_videos: str | None,
    reference_audios: str | None,
    wait: bool,
    output: str,
) -> None:
    """Generate videos using MiniMax API."""
    async def _minimax_video(prompt, model, resolution, duration, ratio, first_frame, last_frame, reference_images, reference_videos, reference_audios, wait, output):
        imgs = [
            u.strip() for u in reference_images.split(",") if u.strip()
        ] if reference_images else None
        vids = [
            u.strip() for u in reference_videos.split(",") if u.strip()
        ] if reference_videos else None
        auds = [
            u.strip() for u in reference_audios.split(",") if u.strip()
        ] if reference_audios else None

        result = await minimax_create_video(
            prompt,
            model=model,
            resolution=resolution,
            duration=duration,
            ratio=ratio,
            first_frame=first_frame,
            last_frame=last_frame,
            reference_images=imgs,
            reference_videos=vids,
            reference_audios=auds,
        )

        if output == "json":
            _print_json(result)
            return

        task_id = result.get("task_id", "")
        console.print("[bold]MiniMax Video Generation[/bold]")
        console.print(f"  Model: {model}")
        console.print(f"  Task ID: {task_id}")
        console.print(f"  Status: {result.get('status', 'pending')}")

        if wait and task_id:
            console.print("[dim]Waiting for completion...[/dim]")
            try:
                final = await minimax_poll_video(task_id, max_wait_seconds=600)
                console.print(f"  Final Status: {final.get('status')}")
                if final.get("url"):
                    console.print(f"[green]  URL: {final['url']}[/green]")
                if final.get("error"):
                    console.print(f"[red]  Error: {final['error']}[/red]")
            except TimeoutError:
                console.print("[yellow]⚠ Generation timed out. Check status manually.[/yellow]")
                console.print("  Use: brandly minimax-jobs to view pending tasks")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        else:
            console.print("[dim]Tip: Use 'brandly minimax-jobs' to check status[/dim]")
    asyncio.run(_minimax_video(prompt, model, resolution, duration, ratio, first_frame, last_frame, reference_images, reference_videos, reference_audios, wait, output))


@cli.command()
@click.option("--status", default=None,
              help="Filter by status (queued, running, succeeded, failed, cancelled)")
@click.option("-n", "--limit", default=20, help="Max number of jobs to show")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def minimax_jobs(status: str | None, limit: int, output: str) -> None:
    """List recent MiniMax video generation jobs."""
    async def _minimax_jobs(status, limit, output):
        job_list = await minimax_list_jobs(status=status, limit=limit)
        if output == "json":
            _print_json(job_list)
            return
        if not job_list:
            console.print("[dim]No MiniMax jobs found.[/dim]")
            return
        table = Table(title=f"MiniMax Video Jobs ({len(job_list)})")
        table.add_column("Task ID", style="cyan", max_width=18)
        table.add_column("Status", style="green")
        table.add_column("Model", style="dim")
        table.add_column("Resolution", style="dim")
        table.add_column("Duration", style="dim")
        table.add_column("Created", style="dim")
        table.add_column("URL", style="blue", max_width=35)
        for j in job_list:
            table.add_row(
                j["task_id"][:18],
                j["status"],
                j.get("model", ""),
                j.get("resolution", ""),
                f"{j.get('duration', '?')}s",
                (j.get("created_at") or "")[:16],
                (j.get("url") or "")[:35],
            )
        console.print(table)
    asyncio.run(_minimax_jobs(status, limit, output))


# ---------------------------------------------------------------------------
# Ark commands (BytePlus — Seedream images + Seedance videos)
# ---------------------------------------------------------------------------


@cli.command(name="ark-image")
@click.option("--prompt", "-p", required=True, help="Image generation prompt")
@click.option(
    "--model",
    default="seedream-4.0",
    type=click.Choice(["seedream-4.0", "seedream-3.5"]),
    help="Seedream model (default: seedream-4.0)",
)
@click.option("--size", default="16:9", help="Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)")
@click.option("--n", default=1, help="Number of images to generate (1-4)")
@click.option(
    "--style-preset",
    default=None,
    type=click.Choice(STYLE_PRESET_OPTIONS),
    help="Style preset to enhance prompt",
)
@click.pass_context
def ark_image(
    ctx: click.Context,
    prompt: str,
    model: str,
    size: str,
    n: int,
    style_preset: str | None,
) -> None:
    """Generate image via BytePlus Ark (Seedream)."""
    console.print(f"[dim]Generating image with {model}...[/dim]")
    try:
        result = asyncio.run(
            ark_generate_image(prompt, model=model, size=size, n=n, style_preset=style_preset)
        )
    except Exception as e:
        console.print(f"[red]Error generating image: {e}[/red]")
        sys.exit(1)

    urls = result.get("urls", [])
    if urls:
        console.print("[green]✓ Image(s) generated:[/green]")
        for url in urls:
            console.print(f"  {url}")
        # Save first URL to disk
        if urls and ctx.obj.get("root"):
            root = Path(ctx.obj["root"])
            saved = _save_artifact(
                urls[0],
                "ark",
                "images",
                root=root,
                prompt_hint=prompt,
                category="general",
            )
            if saved:
                console.print(f"  Saved → {saved}")
    else:
        console.print("[yellow]⚠ No URLs in response[/yellow]")
    _print_json(result)


@cli.command(name="ark-video")
@click.argument("project_id")
@click.option("--prompt", "-p", required=True, help="Video generation prompt")
@click.option(
    "--model",
    default="seedance-1.0-t2v",
    type=click.Choice(["seedance-1.0-t2v", "seedance-1.0-i2v"]),
    help="Seedance model (default: seedance-1.0-t2v)",
)
@click.option("--duration", "-d", default=5, help="Duration in seconds (default: 5)")
@click.option("--aspect-ratio", default="16:9", help="Aspect ratio")
@click.option(
    "--reference-images",
    "-r",
    default=None,
    help="Comma-separated image URLs or local file paths for i2v mode",
)
@click.option("--wait", is_flag=True, help="Poll until generation completes")
@click.option("--max-wait", default=300, help="Max wait seconds (default: 300)")
@click.pass_context
def ark_video(
    ctx: click.Context,
    project_id: str,
    prompt: str,
    model: str,
    duration: int,
    aspect_ratio: str,
    reference_images: str | None,
    wait: bool,
    max_wait: int,
) -> None:
    """Generate video via BytePlus Ark (Seedance)."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)

    imgs = (
        [u.strip() for u in reference_images.split(",") if u.strip()]
        if reference_images
        else []
    )

    console.print(f"[dim]Creating video task with {model}...[/dim]")
    try:
        task = asyncio.run(
            ark_create_video_task(
                prompt,
                model=model,
                duration=duration,
                aspect_ratio=aspect_ratio,
                reference_images=imgs if imgs else None,
            )
        )
    except Exception as e:
        console.print(f"[red]Error creating video task: {e}[/red]")
        sys.exit(1)

    task_id = task["task_id"]
    console.print(f"[green]✓ Task created:[/green] {task_id}")
    console.print(f"  Status: {task['status']}  Progress: {task.get('progress', 0)}%")

    if wait:
        console.print(f"[dim]Polling (max {max_wait}s)...[/dim]")
        try:
            result = asyncio.run(ark_poll_video(task_id, max_wait_seconds=max_wait))
        except TimeoutError as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print(f"[dim]Video ID: {task_id} - check status manually[/dim]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error polling video: {e}[/red]")
            sys.exit(1)

        url = result.get("url") or ""
        console.print(f"[green]✓ Video ready:[/green] {url or 'no URL'}")
        if url:
            root = _get_root(ctx)
            saved = _save_artifact(
                url, project_id, "videos", root=root, prompt_hint=prompt, category="scenes"
            )
            if saved:
                console.print(f"  Saved → {saved}")

    _print_json(task)


@cli.command(name="ark-jobs")
@click.option("--status", default=None, help="Filter by status")
@click.option("-n", "--limit", default=20, help="Max number of jobs to show")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def ark_jobs(status: str | None, limit: int, output: str) -> None:
    """List recent BytePlus Ark (Seedance) video jobs."""
    async def _ark_jobs(status, limit, output):
        job_list = await ark_list_jobs(status=status, limit=limit)
        if output == "json":
            _print_json(job_list)
            return
        if not job_list:
            console.print("[dim]No Ark jobs found.[/dim]")
            return
        table = Table(title=f"Ark Video Jobs ({len(job_list)})")
        table.add_column("Task ID", style="cyan", max_width=18)
        table.add_column("Status", style="green")
        table.add_column("Model", style="dim")
        table.add_column("Created", style="dim")
        table.add_column("URL", style="blue", max_width=40)
        for j in job_list:
            table.add_row(
                j["task_id"][:18],
                j["status"],
                j.get("model", ""),
                (j.get("created_at") or "")[:16],
                (j.get("url") or "")[:40],
            )
        console.print(table)
    asyncio.run(_ark_jobs(status, limit, output))


@cli.command(name="ark-cancel")
@click.argument("task_id")
def ark_cancel(task_id: str) -> None:
    """Cancel an in-progress BytePlus Ark video generation job."""
    async def _ark_cancel(task_id):
        result = await ark_cancel_job(task_id)
        console.print(f"Status: {result['status']}")
        if result.get("error"):
            console.print(f"[red]Error: {result['error']}[/red]")
    asyncio.run(_ark_cancel(task_id))



# ---------------------------------------------------------------------------
# Post-production commands (v0.3.x)
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("clips", nargs=-1, required=True)
@click.argument("output")
@click.option("--transition", default="fade", help="Transition type (fade, dissolve, wipe, slide)")
@click.option("--transition-duration", default=0.5, help="Transition duration in seconds")
@click.option(
    "--color-grade", default="cinematic",
    help="Color grade (cinematic, warm, cool, desaturated, none)",
)
@click.option("--root", default=None, help="Working directory")
def stitch(
    clips: tuple[str, ...],
    output: str,
    transition: str,
    transition_duration: float,
    color_grade: str,
    root: str | None,
) -> None:
    """Stitch multiple video clips with transitions and color grading."""
    from brandly_cli.stitch import stitch_videos
    clip_paths = [Path(c) for c in clips]
    output_path = Path(output)
    console.print(f"[bold]Stitching[/bold] {len(clip_paths)} clips → {output_path}")
    result = asyncio.run(
        stitch_videos(
            clip_paths,
            output_path,
            transition=transition,
            transition_duration=transition_duration,
            color_grade=color_grade,
        )
    )
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Output:[/green] {result['output_path']}")
    console.print(
        f"  Duration: {result['duration_seconds']:.1f}s | Size: {result['size_bytes']//1024}KB"
    )
    console.print(f"  Transitions: {', '.join(result['transitions_applied']) or 'none'}")
    console.print(f"  Color grade: {result['color_grade']}")


@cli.command()
@click.argument("project_id")
@click.option(
    "--platforms", multiple=True,
    help="Target platforms (tiktok, instagram_reel, youtube_standard, etc.)",
)
@click.option("--output", default=None, help="Output directory")
@click.option("--root", default=None, help="Working directory")
def export_platforms(project_id, platforms, output, root):
    """Export project to platform-optimized formats."""
    from brandly_cli.export_platforms import export_for_platform

    if not platforms:
        platforms = ("tiktok", "youtube_standard")
    proj_dir = layout.resolve_project_dir(Path(root or "."), project_id)
    if not proj_dir.exists():
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)
    videos_root = proj_dir / "videos"
    video_file = next((videos_root.rglob("*.mp4")), None)
    if not video_file:
        console.print("[yellow]No video found in project[/yellow]")
        sys.exit(1)
    out_dir = Path(output) if output else proj_dir / "export"
    for platform in platforms:
        console.print(f"Exporting for [bold]{platform}[/bold]...")
        result = asyncio.run(export_for_platform(video_file, platform, out_dir, root=root))
        if "error" in result:
            console.print(f"[red]  Error: {result['error']}[/red]")
        else:
            console.print(f"  ✓ {result['output_path']} ({result['duration_seconds']:.1f}s)")


@cli.command()
@click.argument("project_id")
@click.option("--count", default=5, help="Number of thumbnails to generate")
@click.option("--style", default="commercial", help="Style preset (commercial, minimal, bold)")
@click.option("--root", default=None, help="Working directory")
def thumbnail(project_id: str, count: int, style: str, root: str | None) -> None:
    """Generate thumbnails from project video."""
    from brandly_cli.thumbnails import generate_thumbnails
    proj_dir = layout.resolve_project_dir(Path(root or "."), project_id)
    videos_root = proj_dir / "videos"
    video_file = next((videos_root.rglob("*.mp4")), None)
    if not video_file:
        console.print(f"[red]No video found in project: {project_id}[/red]")
        sys.exit(1)
    output_dir = layout.media_dir(proj_dir, "images", "general")
    result = asyncio.run(
        generate_thumbnails(
            video_file, output_dir, count=count, style_preset=style,
            root=Path(root) if root else None,
        )
    )
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Generated {result['count']} thumbnails[/green]")
    for thumb in result.get("thumbnails", []):
        console.print(f"  {thumb.get('path', thumb)}")


@cli.command(name="voice-match")
@click.argument("video_path")
@click.option("--source", default="en", help="Source language code")
@click.option(
    "--target", required=True,
    help="Target language code (en, es, fr, de, ja, ko, zh, pt, ar, hi)",
)
@click.option("--voice-style", default="professional", help="Voice style")
@click.option("--output", default=None, help="Output path")
@click.option("--root", default=None, help="Working directory")
def voice_match(
    video_path: str, source: str, target: str, voice_style: str,
    output: str | None, root: str | None,
) -> None:
    """Dub a video to a target language."""
    from brandly_cli.dubbing import dub_video
    result = asyncio.run(
        dub_video(
            Path(video_path), source, target,
            voice_style=voice_style,
            output_path=Path(output) if output else None,
            root=Path(root) if root else None,
        )
    )
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Dubbed to {result['target_lang']}[/green]")
    console.print(f"  Output: {result['output_path']}")
    console.print(f"  Duration: {result['duration_seconds']:.1f}s")


@cli.command(name="beat-sync")
@click.argument("video_path")
@click.argument("audio_path")
@click.option("--output", required=True, help="Output video path")
@click.option("--threshold", default=0.5, help="Beat detection threshold")
@click.option("--min-duration", default=1.0, help="Minimum clip duration")
@click.option("--root", default=None, help="Working directory")
def beat_sync(
    video_path: str, audio_path: str, output: str,
    threshold: float, min_duration: float, root: str | None,
) -> None:
    """Cut video to match beat positions in audio."""
    from brandly_cli.beat_sync import beat_sync as bs_sync
    result = asyncio.run(
        bs_sync(
            Path(video_path), Path(audio_path), Path(output),
            beat_threshold=threshold,
            min_clip_duration=min_duration,
            root=Path(root) if root else None,
        )
    )
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Beat-synced {result['clips_created']} segments[/green]")
    console.print(f"  Beats detected: {result['beats_detected']}")
    console.print(f"  Output: {result['output_path']}")


@cli.command()
@click.argument("category", default=None, required=False)
@click.option("--platforms", multiple=True, help="Filter by platforms")
@click.option("--json", is_flag=True, help="Output as JSON")
def trend(category: str | None, platforms: tuple[str, ...], json: bool) -> None:
    """Research trending video formats."""
    from brandly_cli.trends import list_categories, research_trends
    cats = list_categories()
    if not category:
        console.print("[bold]Available categories:[/bold]")
        for c in cats:
            console.print(f"  {c}")
        return
    if category not in cats:
        console.print(f"[red]Unknown category: {category}. Available: {cats}[/red]")
        sys.exit(1)
    result = asyncio.run(research_trends(category, list(platforms) if platforms else None))
    if json:
        _print_json(result)
        return
    console.print(f"[bold]{category.capitalize()} Trending Formats[/bold]")
    console.print(f"  Recommended: {result['recommended_format']}")
    console.print()
    for fmt in result["trending_formats"]:
        console.print(f"  • {fmt['name']} — {fmt['description']} (virality: {fmt['virality']:.0%})")


@cli.command()
@click.argument("video_path")
@click.option("--script", default=None, help="Script text for hook analysis")
@click.option("--style", default="cinematic", help="Visual style")
@click.option("--root", default=None, help="Working directory")
def analyze(video_path: str, script: str | None, style: str, root: str | None) -> None:
    """Analyze video performance prediction."""
    from brandly_cli.analyzer import analyze_video
    result = asyncio.run(
        analyze_video(
            Path(video_path), script=script, style=style,
            root=Path(root) if root else None,
        )
    )
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print("[bold]Video Performance Analysis[/bold]")
    console.print(f"  Overall Score: [green]{result['overall_score']}[/green]/10")
    console.print(f"  Hook Strength:   {result['hook_strength']}/10")
    console.print(f"  Pacing Score:    {result['pacing_score']}/10")
    console.print(f"  Visual Quality:  {result['visual_quality']}/10")
    console.print(f"  CTR Prediction:  {result['ctr_prediction']}/10")
    console.print(f"  Platform Fit:    {result['platform_fit']}/10")
    if result["recommendations"]:
        console.print()
        console.print("[bold]Recommendations:[/bold]")
        for rec in result["recommendations"]:
            console.print(f"  • {rec}")


@cli.command()
@click.argument("name")
@click.option("--style", default="ugc", help="Style preset")
@click.option("--shots", default=5, help="Number of shots")
@click.option("--duration", default=30, help="Duration in seconds")
@click.option("--budget", default=300, help="Budget in credits")
@click.option("--platforms", multiple=True, help="Target platforms")
@click.option("--save", is_flag=True, help="Save as custom template")
@click.option("--root", default=None, help="Working directory")
def template(
    name: str, style: str, shots: int, duration: int, budget: int,
    platforms: tuple[str, ...], save: bool, root: str | None,
) -> None:
    """Create or manage project templates."""
    from brandly_cli.templates import create_from_template, save_template
    if save:
        config = {
            "style": style, "shots": shots, "duration": duration,
            "budget": budget, "platforms": list(platforms) or ["tiktok"],
        }
        asyncio.run(save_template(name, config, root=Path(root) if root else None))
        console.print(f"[green]✓ Template saved: {name}[/green]")
    else:
        console.print(f"[bold]Template: {name}[/bold]")
        config = asyncio.run(create_from_template(name))
        for k, v in config.items():
            console.print(f"  {k}: {v}")


@cli.command(name="template-list")
@click.option("--root", default=None, help="Working directory")
def template_list(root: str | None) -> None:
    """List available templates."""
    from brandly_cli.templates import list_custom_templates, list_templates
    builtins = asyncio.run(list_templates())
    customs = asyncio.run(list_custom_templates(root=Path(root) if root else None))
    console.print("[bold]Built-in Templates[/bold]")
    for t in builtins:
        console.print(f"  • {t}")
    if customs:
        console.print()
        console.print("[bold]Custom Templates[/bold]")
        for t in customs:
            console.print(f"  ★ {t}")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host address")
@click.option("--port", default=8080, type=int, help="Port number")
@click.pass_context
def webhook(ctx: click.Context, host: str, port: int) -> None:
    """Start webhook server for CI/CD integration."""
    import importlib.util

    if (
        importlib.util.find_spec("fastapi") is None
        or importlib.util.find_spec("uvicorn") is None
    ):
        console.print("[red]FastAPI/uvicorn not installed. Run: pip install fastapi uvicorn[/red]")
        sys.exit(1)
    console.print(f"[bold]Starting webhook server[/bold] at http://{host}:{port}")
    console.print(
        "[dim]Endpoints: POST /webhook/generate, "
        "GET /webhook/jobs/{id}, POST /webhook/jobs/{id}/cancel[/dim]"
    )


@cli.command()
@click.argument("file_path")
@click.option("--provider", default="local", help="Share provider (local, s3)")
@click.option("--root", default=None, help="Working directory")
def share(file_path: str, provider: str, root: str | None) -> None:
    """Upload file to cloud for sharing."""
    from brandly_cli.sharing import share_file
    result = asyncio.run(
        share_file(
            Path(file_path), provider=provider,
            root=Path(root) if root else None,
        )
    )
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print("[green]✓ Shared[/green]")
    console.print(f"  URL: {result.get('share_url', 'N/A')}")
    console.print(f"  Provider: {result.get('provider', provider)}")
    if result.get("file_size_bytes"):
        console.print(f"  Size: {(result['file_size_bytes']//1024)}KB")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# report — submit an issue to GitHub with user consent
# ---------------------------------------------------------------------------


@cli.command(name="report")
@click.option(
    "--error", "-e", default=None,
    help="Error message to report (otherwise interactive prompt)",
)
@click.option(
    "--project", "-p", default=None, help="Project ID to attach context to",
)
@click.option(
    "--root", default=None, help="Brandly root directory",
)
@click.option(
    "--dry-run", is_flag=True, help="Show issue body without submitting",
)
@click.option(
    "--auto", is_flag=True, help="Submit without asking (requires prior consent or GITHUB_TOKEN)",
)
def report(
    error: str | None,
    project: str | None,
    root: str | None,
    dry_run: bool,
    auto: bool,
) -> None:
    """Report a bug or feature request to the GitHub issues tracker.

    Prints a preview of the issue body and asks for confirmation before
    submitting — unless --auto is passed (or auto-consent was previously
    granted via a prior interactive report).
    """
    from brandly_cli.issue_tracker import (
        ask_permission,
        collect_context,
        format_issue_body,
        submit_issue,
    )

    root_path = Path(root) if root else _get_root(click.get_current_context(silent=True) or click.Context(cli))
    exc = None
    if error:
        exc = RuntimeError(error)
    ctx = collect_context(error=exc, project_id=project, root=root_path)
    body = format_issue_body(ctx)

    if dry_run:
        console.print("[bold]Issue preview (dry run):[/bold]")
        console.print(body)
        return

    if auto:
        console.print("[dim]Submitting issue to GitHub...[/dim]")
        result = submit_issue(ctx, body)
        if result.get("ok"):
            console.print(f"[green]✓ Issue opened: {result['url']}[/green]")
            console.print(f"  Number: #{result.get('number')}")
        else:
            console.print(
                f"[red]Report failed: {result.get('error') or result}[/red]"
            )
        return

    if ask_permission(ctx, body):
        console.print("[dim]Submitting issue to GitHub...[/dim]")
        result = submit_issue(ctx, body)
        if result.get("ok"):
            console.print(f"[green]✓ Issue opened: {result['url']}[/green]")
            console.print(f"  Number: #{result.get('number')}")
        else:
            console.print(
                f"[red]Report failed: {result.get('error') or result}[/red]"
            )
    else:
        console.print("[dim]Issue report skipped.[/dim]")

