"""Validate command for brandly-cli."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from brandly_cli import __version__
from brandly_cli.agnes_client import (
    cancel_job,
    create_video_task,
    generate_image,
    list_jobs,
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
    return Path.cwd()


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
) -> Path | None:
    """Download a generated asset and save it under
    .brandly/projects/{id}/artifacts/{type_label}/{timestamp}_{hash}.{ext}."""
    if not url:
        return None
    artifacts_dir = root / ".brandly" / "projects" / project_id / "artifacts" / type_label
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
    ct = CostTracker(root / ".brandly" / "projects")
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
        "Professional product reference sheet, 16:9, multi-view grid layout.\n"
        "Subject: {subject}.\n"
        "Layout: split the 16:9 frame into a 3-column grid. "
        "Left column: front three-quarter view. "
        "Middle column: pure side profile. "
        "Right column: rear three-quarter view. "
        "All three views show the same {subject} at the same scale, "
        "on a single continuous clean neutral background, "
        "studio product lighting (soft key from camera-left, fill from camera-right, "
        "rim from behind to separate subject from background), "
        "sharp focus across the entire subject in every panel, no motion, "
        "no people, no environment context, single product only, "
        "thin white separator lines between the three views.\n"
        "Style: commercial product photography, 8K, high-end catalog aesthetic."
    ),
    "character": (
        "Character reference sheet, 16:9, multi-view grid layout.\n"
        "Subject: {subject}.\n"
        "Layout: split the 16:9 frame into a 3-column grid. "
        "Left column: front view (head and upper torso). "
        "Middle column: pure side profile. "
        "Right column: three-quarter view. "
        "All three views show the same character at the same scale, "
        "consistent studio lighting from the same direction in all three "
        "(key from camera-left, fill from camera-right, subtle rim from behind), "
        "clean neutral background, full color and material details, no motion, "
        "thin white separator lines between the three views.\n"
        "Style: cinematic character design sheet, 8K, neutral grading."
    ),
    "location": (
        "Location reference sheet, 16:9, full-frame single image.\n"
        "Subject: {subject}.\n"
        "Layout: ONE wide establishing frame filling the entire 16:9 canvas, "
        "no grid, no split panels, no insets. "
        "No people. "
        "Consistent lighting and time of day across the whole frame. "
        "Clean composition with clear architectural or environmental reference points, "
        "no text overlays, no UI elements.\n"
        "Style: cinematic location design sheet, 8K, color-graded reference frame."
    ),
    "vehicle": (
        "Vehicle reference sheet, 16:9, multi-view grid layout.\n"
        "Subject: {subject}.\n"
        "Layout: split the 16:9 frame into a 3-column grid. "
        "Left column: front three-quarter view. "
        "Middle column: pure side profile. "
        "Right column: rear three-quarter view. "
        "All three views show the same vehicle at the same scale, "
        "consistent outdoor lighting, sharp focus, clean background, "
        "no people, "
        "thin white separator lines between the three views.\n"
        "Style: automotive design sheet, 8K, commercial photography."
    ),
    "animal": (
        "Animal reference sheet, 16:9, multi-view grid layout.\n"
        "Subject: {subject}.\n"
        "Layout: split the 16:9 frame into a 3-column grid. "
        "Left column: full body side profile. "
        "Middle column: head close-up (face/eyes detail). "
        "Right column: three-quarter body view. "
        "All three views show the same animal at consistent scale, "
        "consistent natural lighting, habitat hints, sharp focus, no people, "
        "thin white separator lines between the three views.\n"
        "Style: nature reference sheet, 8K, wildlife photography aesthetic."
    ),
    "plant": (
        "Plant reference sheet, 16:9, multi-view grid layout.\n"
        "Subject: {subject}.\n"
        "Layout: split the 16:9 frame into a 3-column grid. "
        "Left column: full plant overview. "
        "Middle column: leaf detail close-up. "
        "Right column: stem/trunk/bark detail. "
        "All three views show the same plant at consistent scale, "
        "consistent soft daylight, clean background, sharp focus, no people, "
        "thin white separator lines between the three views.\n"
        "Style: botanical reference sheet, 8K, scientific photography aesthetic."
    ),
    "mecha": (
        "Mecha reference sheet, 16:9, multi-view grid layout.\n"
        "Subject: {subject}.\n"
        "Layout: split the 16:9 frame into a 3-column grid. "
        "Left column: front three-quarter view. "
        "Middle column: pure side profile. "
        "Right column: detail close-up of distinctive mechanical features. "
        "All three views show the same mecha at consistent scale, "
        "consistent studio lighting, clean background, sharp focus, no people, "
        "thin white separator lines between the three views.\n"
        "Style: technical design sheet, 8K, industrial photography."
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
) -> None:
    """Generate the primary reference image for a project.

    The primary reference is a GOLD-grade image that locks the appearance of a
    key asset (object, character, location, etc.) across all subsequent
    `brandly video` generations. Should be the FIRST generation step.

    The generated image is saved to .brandly/projects/<id>/artifacts/images/
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

    plan = write_generation_plan(
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
    )
    console.print(f"[dim]Plan written: {plan}[/dim]")

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
            docs_dir = root / ".brandly" / "projects" / project_id / "docs"
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
        sys.exit(1)

    url = result.get("url") or ""
    if not url:
        console.print(
            "[yellow]Reference generated (base64 returned) — no URL to save[/yellow]"
        )
        sys.exit(1)

    from brandly_cli.utils import write_generation_doc

    saved = _save_artifact(
        url,
        project_id,
        "images",
        root=root,
        prompt_hint=f"reference_{subject_type}_{subject}",
    )
    if saved:
        # Rename the saved file to reference_<subject_type>_<timestamp>.<ext>
        timestamp = now_iso().replace(":", "-").replace(".", "_")
        ext = saved.suffix or ".png"
        new_name = f"reference_{subject_type}_{timestamp}{ext}"
        new_path = saved.parent / new_name
        try:
            saved.rename(new_path)
        except OSError:
            new_path = saved  # fall back to original name if rename fails
        console.print(f"[green]✓ Reference image saved:[/green] {new_path}")
        write_generation_doc(
            project_id,
            "reference",
            new_path,
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
        )

        # Persist the primary reference metadata on the project so downstream
        # tools (e.g. `brandly video`) can read it.
        reference_meta = {
            "subject_type": subject_type,
            "skill": subject_skill,
            "subject": subject,
            "image_path": str(new_path),
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
        console.print(
            f"\n[bold]Next:[/bold] run [cyan]brandly video {project_id} ...[/cyan] — the "
            f"primary reference image will be auto-injected as a reference image."
        )
    else:
        console.print("[yellow]⚠ Could not save reference artifact[/yellow]")
        sys.exit(1)


# Backwards-compatible alias for the previous name.
@cli.command(name="anchor", hidden=True)
@click.argument("project_id")
@click.option(
    "--sheet",
    "subject_type",
    required=True,
    type=click.Choice(list(REFERENCE_SUBJECTS.keys())),
    help="Deprecated: use --subject-type",
)
@click.option(
    "--description",
    "-d",
    "subject",
    required=True,
    help="Deprecated: use --subject",
)
@click.option("--style-preset", default="commercial", type=click.Choice(STYLE_PRESET_OPTIONS))
@click.option("--size", default="2K")
@click.option("--ratio", default="16:9")
@click.option("--model", default="agnes-image-2.1-flash")
@click.pass_context
def anchor(
    ctx: click.Context,
    project_id: str,
    subject_type: str,
    subject: str,
    style_preset: str,
    size: str,
    ratio: str,
    model: str,
) -> None:
    """DEPRECATED: use `brandly reference` instead. Kept for backwards compatibility."""
    console.print(
        "[yellow]⚠ 'brandly anchor' is deprecated, use 'brandly reference' instead.[/yellow]"
    )
    ctx.forward(reference)


# ---------------------------------------------------------------------------
# image
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--project-id", default=None, help="Optional project UUID")
@click.option("--prompt", "-p", required=True, help="Image generation prompt")
@click.option("--model", default="agnes-image-2.1-flash", help="Agnes image model")
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
    if project_id:
        from brandly_cli.utils import write_generation_plan

        plan = write_generation_plan(
            project_id,
            "image",
            root=root,
            prompt=prompt,
            model=model,
            style=style_preset or "default",
            extra_config={"size": size, "ratio": ratio},
        )
        console.print(f"[dim]Plan written: {plan}[/dim]")

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

            docs_dir = Path(f".brandly/projects/{project_id}/docs")
            docs_dir.mkdir(parents=True, exist_ok=True)
            fail_doc = docs_dir / f"image_fail_{now_iso().replace(':', '-').replace('.', '_')}.md"
            fail_doc.write_text(
                f"# Image Generation Failed\n\n"
                f"**Error:** {e}\n\n**Prompt:** {prompt}\n\n**Status:** FAILED\n",
                encoding="utf-8",
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

    _print_json(result)


# ---------------------------------------------------------------------------
# video
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("project_id")
@click.option("--prompt", "-p", required=True, help="Video generation prompt")
@click.option(
    "--model",
    default="agnes-video-v2.0",
    help="Agnes video model (v2.0 recommended; 2.5-flash is free but rate-limited to 1/min)",
)
@click.option(
    "--style",
    default="cinematic",
    type=click.Choice(list_video_styles()),
    help="Video style preset for consistent output",
)
@click.option(
    "--mode",
    default="text",
    type=click.Choice(["text", "keyframe", "reference"]),
    help="Generation mode: text-to-video, keyframe transition, or reference-based",
)
@click.option("--duration", "-d", default=10, help="Duration in seconds (default: 10)")
@click.option("--aspect-ratio", default="16:9", help="Aspect ratio")
@click.option("--first-frame", default=None, help="First frame image URL (keyframe mode)")
@click.option("--last-frame", default=None, help="Last frame image URL (keyframe mode)")
@click.option(
    "--reference-images",
    "-r",
    default=None,
    help="Comma-separated image URLs for character/object consistency (reference mode)",
)
@click.option(
    "--character",
    "-c",
    default=None,
    help="Character description for identity locking (e.g. 'woman in red dress, blonde hair')",
)
@click.option("--wait", is_flag=True, help="Poll until generation completes")
@click.option("--max-wait", default=300, help="Max wait seconds (default: 300)")
@click.option(
    "--require-reference/--no-require-reference",
    "require_reference",
    default=False,
    help="If set, fail when project has no primary reference image.",
)
@click.option(
    "--require-anchor/--no-require-anchor",
    "require_reference",
    default=None,
    hidden=True,
    help="DEPRECATED: use --require-reference / --no-require-reference.",
)
@click.option(
    "--allow-referenceless",
    "allow_referenceless",
    is_flag=True,
    help="Bypass the require-reference check (escape hatch for re-runs/edge cases).",
)
@click.option(
    "--allow-anchorless",
    "allow_referenceless",
    is_flag=True,
    hidden=True,
    help="DEPRECATED: use --allow-referenceless.",
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
) -> None:
    """Generate an AI video via Agnes AI.

    For best results, the project should have a primary reference image
    generated first via `brandly reference`. The reference is auto-injected
    as the FIRST reference image (strongest influence). Use --require-reference
    to fail if the reference is missing.
    """
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)

    # Auto-detect project artifacts as additional reference images
    root = _get_root(ctx)
    auto_refs = get_reference_image_urls(project_id, root)

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
    # Note: v2.0 is reliable; 2.5-flash is free but rate-limited (1 req/min)
    console.print(f"[dim]Model: {model} | Style: {style} | Mode: {mode}[/dim]")
    if character:
        console.print(f"[dim]Character anchor: {character[:60]}...[/dim]")
    if imgs:
        console.print(f"[dim]Reference images: {len(imgs)}[/dim]")
    if sheet_hint:
        console.print(f"[dim]Loaded sheet reference: {loaded_skill}[/dim]")

    # Write pre-generation plan BEFORE API call
    from brandly_cli.utils import write_generation_plan

    plan = write_generation_plan(
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
    )
    console.print(f"[dim]Plan written: {plan}[/dim]")

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
            )
        )
    except Exception as e:
        console.print(f"[red]Error creating video task: {e}[/red]")
        sys.exit(1)

    video_id = task["video_id"]
    console.print(f"[green]✓ Task created:[/green] {video_id}")
    console.print(f"  Status: {task['status']}  Progress: {task['progress']}%")

    if wait:
        console.print(f"[dim]Polling (max {max_wait}s)...[/dim]")
        try:
            result = asyncio.run(poll_video(video_id, max_wait_seconds=max_wait))
        except TimeoutError as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print(f"[dim]Video ID: {video_id} - check status manually[/dim]")
            # Update plan to show timeout
            from brandly_cli.utils import write_generation_doc

            write_generation_doc(
                project_id,
                "video",
                Path("timeout"),
                root=root,
                prompt=enhanced,
                model=model,
                style=style,
                metadata={"video_id": video_id, "status": "timeout", "error": str(e)},
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
            root = _get_root(ctx)
            saved = _save_artifact(url, project_id, "videos", root=root, prompt_hint=prompt)
            if saved:
                console.print(f"  Saved → {saved}")
                # Write generation document
                from brandly_cli.utils import write_generation_doc

                write_generation_doc(
                    project_id,
                    "video",
                    saved,
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
                )
                console.print(f"  Doc → {saved.parent.parent / 'docs'}")
            else:
                console.print("[yellow]⚠ Could not save artifact, but URL is available[/yellow]")

    # Persist to project
    root = _get_root(ctx)
    pm = ProjectManager(root)
    asyncio.run(pm.update(project_id, {"current_phase": "asset"}))

    _print_json(task)


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
        saved = _save_artifact(url, pid, "audio", root=root, prompt_hint=prompt)
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
@click.pass_context
def tts(
    ctx: click.Context, project_id: str | None, text: str, model: str, voice_id: str, speed: float
) -> None:
    """Generate voiceover via MiniMax TTS."""
    console.print(f"[dim]Generating TTS ({model}, voice={voice_id})...[/dim]")
    result = asyncio.run(generate_tts(text, model=model, voice_id=voice_id, speed=speed))
    url = result.get("url") or ""
    if url:
        console.print(f"[green]✓ Voiceover generated:[/green] {url}")
        # Save to disk
        pid = project_id or ""
        root = _get_root(ctx)
        saved = _save_artifact(url, pid, "audio", root=root, prompt_hint=text[:60])
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
    help="Output directory (default: .brandly/projects/{id}/export/)",
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

    out_dir = Path(output) if output else root / ".brandly" / "projects" / project_id / "export"

    # Files in the project root that are bookkeeping, not user-facing artifacts.
    # These are excluded from the export.
    internal_files = {"project.json", "cost.json"}

    artifact_count = 0
    media_count = 0
    media_exts = {".png", ".jpg", ".jpeg", ".mp4", ".webm", ".mp3", ".wav", ".mpga"}
    for search_dir in [
        root / ".brandly" / "projects" / project_id / "artifacts",
        root / ".brandly" / "projects" / project_id,
    ]:
        if not search_dir.exists():
            continue
        for f in search_dir.rglob("*"):
            if not f.is_file():
                continue
            # Skip files inside the export output directory to avoid recursion
            try:
                f.relative_to(out_dir)
                continue
            except ValueError:
                pass
            # Skip bookkeeping files at the project root
            if f.parent == root / ".brandly" / "projects" / project_id and f.name in internal_files:
                continue
            ext = f.suffix.lower()
            rel = f.relative_to(search_dir)
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
    ct = CostTracker(root / ".brandly" / "projects")
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
    ct = CostTracker(root / ".brandly" / "projects")
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
    table.add_row("MINIMAX_BASE_URL", os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1"))
    table.add_row("Version", __version__)
    console.print(table)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for brandly CLI."""
    cli()


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


# ---------------------------------------------------------------------------
# jobs — list/cancel async video jobs
# ---------------------------------------------------------------------------


@cli.command()
@click.option("-s", "--status", default=None, help="Filter by status (pending, completed, failed)")
@click.option("-n", "--limit", default=20, help="Max number of jobs to show")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
async def jobs(status: str | None, limit: int, output: str) -> None:
    """List recent video generation jobs from the API."""
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
    console.print("[dim]Tip: Use 'brandly job resume <id>' to poll for completion[/dim]")


@cli.command()
@click.argument("video_id")
def job_resume(video_id: str) -> None:
    """Poll and wait for a video generation job to complete."""
    from brandly_cli.agnes_client import get_video_status

    console.print(f"[dim]Checking status for {video_id}...[/dim]")
    result = asyncio.run(get_video_status(video_id))
    status = result.get("status", "unknown")
    console.print(f"  Status: {status}")
    console.print(f"  Progress: {result.get('progress', 0)}%")
    if result.get("url"):
        console.print(f"[green]  URL: {result['url']}[/green]")
    if result.get("error"):
        console.print(f"[red]  Error: {result['error']}[/red]")


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
async def edit(
    input: str,
    output: str,
    start: float,
    end: float | None,
    duration: float | None,
    codec: str,
    preset: str,
) -> None:
    """Trim a video to a segment."""
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


@cli.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--width", default=None, type=int, help="Target width in pixels")
@click.option("--height", default=None, type=int, help="Target height in pixels")
@click.option("--aspect", default=None, help="Aspect ratio (16:9, 9:16, 1:1, 4:3)")
@click.option("--codec", default="libx264", help="Video codec")
async def resize(
    input: str,
    output: str,
    width: int | None,
    height: int | None,
    aspect: str | None,
    codec: str,
) -> None:
    """Resize a video to given dimensions or aspect ratio."""
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


@cli.command()
@click.argument("inputs", nargs=-1, required=True, type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--codec", default="libx264", help="Video codec")
async def concat(inputs: tuple[str, ...], output: str, codec: str) -> None:
    """Concatenate multiple videos into one."""
    result = await concatenate_videos(list(inputs), output, codec=codec)
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(
        f"[green]✓ Concatenated {result.get('input_count', len(inputs))} "
        f"videos → {output}[/green]"
    )
    console.print(f"  Duration: {result.get('duration_seconds', '?')}s")


@cli.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--format", "fmt", default="mp3", help="Audio format (mp3, wav, m4a)")
@click.option("--bitrate", default="192k", help="Audio bitrate")
async def audio(input: str, output: str, fmt: str, bitrate: str) -> None:
    """Extract audio track from a video file."""
    result = await extract_audio(input, output, format=fmt, bitrate=bitrate)
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Audio extracted to {output}[/green]")
    console.print(f"  Format: {fmt}")
    console.print(f"  Bitrate: {bitrate}")


@cli.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.argument("text")
@click.option("--font-size", default=24, type=int)
@click.option("--position", default="bottom", type=click.Choice(["top", "middle", "bottom"]))
@click.option("--codec", default="libx264")
async def captions(
    input: str,
    output: str,
    text: str,
    font_size: int,
    position: str,
    codec: str,
) -> None:
    """Add burned-in subtitles to a video."""
    result = await add_subtitles(
        input, output, text,
        font_size=font_size, position=position, codec=codec,
    )
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Subtitles added to {output}[/green]")


@cli.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.argument("speed", type=float)
@click.option("--codec", default="libx264")
async def speed(
    input: str, output: str, speed: float, codec: str
) -> None:
    """Change video playback speed."""
    result = await change_speed(input, output, speed, codec=codec)
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Speed changed to {speed}x → {output}[/green]")


# ---------------------------------------------------------------------------
# analyze — video metadata analysis
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("input", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def analyze(input: str, output: str) -> None:
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
@click.option("--model", default="agnes-video-v2.0", help="Model to use")
@click.option("-n", "--count", default=3, help="Number of variants to generate")
@click.option("--wait", is_flag=True, help="Wait for each generation to complete")
@click.option("--character", default=None, help="Character description for consistency")
@click.option("--reference-images", default=None, help="Comma-separated reference image URLs")
@click.pass_context
async def batch(
    ctx: click.Context,
    project_id: str,
    base_prompt: str,
    style: str,
    model: str,
    count: int,
    wait: bool,
    character: str | None,
    reference_images: str | None,
) -> None:
    """Generate multiple video variants from a base prompt."""
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
        variant_prompt = f"{base_prompt}"
        if count > 1:
            variant_prompt += f"\n\nVariation {i + 1}: Unique camera angle and composition."
        console.print(f"[dim]Generating variant {i + 1}/{count}...[/dim]")
        task = await create_video_task(
            variant_prompt,
            model=model,
            duration=5,
            aspect_ratio="16:9",
            reference_images=imgs,
        )
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
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
async def minimax_image(
    prompt: str,
    model: str,
    ratio: str,
    width: int | None,
    height: int | None,
    count: int,
    subject: str | None,
    output: str,
) -> None:
    """Generate images using MiniMax API."""
    subject_ref = None
    if subject:
        subject_ref = [{"type": "character", "image_file": subject}]

    result = await minimax_generate_image(
        prompt,
        model=model,
        aspect_ratio=ratio,
        width=width,
        height=height,
        n=count,
        subject_reference=subject_ref,
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


@cli.command()
@click.argument("prompt")
@click.option("--model", default="MiniMax-H3", help="Model (MiniMax-H3 or MiniMax-H3-Max)")
@click.option("--resolution", default="768P", help="Resolution (480P, 768P, 2K)")
@click.option("--duration", default=5, type=click.IntRange(4, 15), help="Duration in seconds")
@click.option("--ratio", default="adaptive", help="Aspect ratio")
@click.option("--first-frame", default=None, help="First frame image URL")
@click.option("--last-frame", default=None, help="Last frame image URL")
@click.option("--reference-images", default=None, help="Comma-separated reference image URLs")
@click.option("--reference-videos", default=None, help="Comma-separated reference video URLs")
@click.option("--reference-audios", default=None, help="Comma-separated reference audio URLs")
@click.option("--wait", is_flag=True, help="Wait for completion")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
async def minimax_video(
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


@cli.command()
@click.option("--status", default=None,
              help="Filter by status (queued, running, succeeded, failed, cancelled)")
@click.option("-n", "--limit", default=20, help="Max number of jobs to show")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
async def minimax_jobs(status: str | None, limit: int, output: str) -> None:
    """List recent MiniMax video generation jobs."""
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
            saved = _save_artifact(urls[0], "ark", "images", root=root, prompt_hint=prompt)
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
    help="Comma-separated image URLs for i2v mode",
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
            saved = _save_artifact(url, project_id, "videos", root=root, prompt_hint=prompt)
            if saved:
                console.print(f"  Saved → {saved}")

    _print_json(task)


@cli.command(name="ark-jobs")
@click.option("--status", default=None, help="Filter by status")
@click.option("-n", "--limit", default=20, help="Max number of jobs to show")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
async def ark_jobs(status: str | None, limit: int, output: str) -> None:
    """List recent BytePlus Ark (Seedance) video jobs."""
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


@cli.command(name="ark-cancel")
@click.argument("task_id")
async def ark_cancel(task_id: str) -> None:
    """Cancel an in-progress BytePlus Ark video generation job."""
    result = await ark_cancel_job(task_id)
    console.print(f"Status: {result['status']}")
    if result.get("error"):
        console.print(f"[red]Error: {result['error']}[/red]")


    main()


# ---------------------------------------------------------------------------
# Post-production commands (v0.3.x)
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("clips", nargs=-1, required=True)
@click.argument("output")
@click.option("--transition", default="fade", help="Transition type (fade, dissolve, wipe, slide)")
@click.option("--transition-duration", default=0.5, help="Transition duration in seconds")
@click.option("--color-grade", default="cinematic", help="Color grade (cinematic, warm, cool, desaturated, none)")
@click.option("--root", default=None, help="Working directory")
def stitch(clips: tuple[str, ...], output: str, transition: str, transition_duration: float, color_grade: str, root: str | None) -> None:
    """Stitch multiple video clips with transitions and color grading."""
    from brandly_cli.stitch import stitch_videos
    clip_paths = [Path(c) for c in clips]
    output_path = Path(output)
    console.print(f"[bold]Stitching[/bold] {len(clip_paths)} clips → {output_path}")
    result = asyncio.run(stitch_videos(clip_paths, output_path, transition=transition, transition_duration=transition_duration, color_grade=color_grade))
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Output:[/green] {result['output_path']}")
    console.print(f"  Duration: {result['duration_seconds']:.1f}s | Size: {result['size_bytes']//1024}KB")
    console.print(f"  Transitions: {', '.join(result['transitions_applied']) or 'none'}")
    console.print(f"  Color grade: {result['color_grade']}")


@cli.command()
@click.argument("project_id")
@click.option("--platforms", multiple=True, help="Target platforms (tiktok, instagram_reel, youtube_standard, etc.)")
@click.option("--output", default=None, help="Output directory")
@click.option("--root", default=None, help="Working directory")
def export_platforms(project_id, platforms, output, root):
    """Export project to platform-optimized formats."""
    if not platforms:
        platforms = ("tiktok", "youtube_standard")
    proj_dir = Path(root or ".") / ".brandly" / "projects" / project_id
    if not proj_dir.exists():
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)
    video_file = next(proj_dir.glob("*.mp4"), None)
    if not video_file:
        console.print("[yellow]No video found in project[/yellow]")
        sys.exit(1)
    out_dir = Path(output) if output else proj_dir / "exports"
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
    proj_dir = Path(root or ".") / ".brandly" / "projects" / project_id
    video_file = next(proj_dir.glob("*.mp4"), None)
    if not video_file:
        console.print(f"[red]No video found in project: {project_id}[/red]")
        sys.exit(1)
    output_dir = proj_dir / "thumbnails"
    result = asyncio.run(generate_thumbnails(video_file, output_dir, count=count, style_preset=style, root=root))
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Generated {result['count']} thumbnails[/green]")
    for thumb in result.get("thumbnails", []):
        console.print(f"  {thumb.get('path', thumb)}")


@cli.command(name="voice-match")
@click.argument("video_path")
@click.option("--source", default="en", help="Source language code")
@click.option("--target", required=True, help="Target language code (en, es, fr, de, ja, ko, zh, pt, ar, hi)")
@click.option("--voice-style", default="professional", help="Voice style")
@click.option("--output", default=None, help="Output path")
@click.option("--root", default=None, help="Working directory")
def voice_match(video_path: str, source: str, target: str, voice_style: str, output: str | None, root: str | None) -> None:
    """Dub a video to a target language."""
    from brandly_cli.dubbing import dub_video
    result = asyncio.run(dub_video(Path(video_path), source, target, voice_style=voice_style, output_path=Path(output) if output else None, root=root))
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
def beat_sync(video_path: str, audio_path: str, output: str, threshold: float, min_duration: float, root: str | None) -> None:
    """Cut video to match beat positions in audio."""
    from brandly_cli.beat_sync import beat_sync as bs_sync
    result = asyncio.run(bs_sync(Path(video_path), Path(audio_path), Path(output), beat_threshold=threshold, min_clip_duration=min_duration, root=root))
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
    from brandly_cli.trends import research_trends, list_categories
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
    result = asyncio.run(analyze_video(Path(video_path), script=script, style=style, root=root))
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
def template(name: str, style: str, shots: int, duration: int, budget: int, platforms: tuple[str, ...], save: bool, root: str | None) -> None:
    """Create or manage project templates."""
    from brandly_cli.templates import save_template, create_from_template, list_templates
    if save:
        config = {"style": style, "shots": shots, "duration": duration, "budget": budget, "platforms": list(platforms) or ["tiktok"]}
        asyncio.run(save_template(name, config, root=root))
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
    from brandly_cli.templates import list_templates, list_custom_templates
    builtins = asyncio.run(list_templates())
    customs = asyncio.run(list_custom_templates(root=root))
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
    try:
        from fastapi import FastAPI
        from uvicorn import run
    except ImportError:
        console.print("[red]FastAPI/uvicorn not installed. Run: pip install fastapi uvicorn[/red]")
        sys.exit(1)
    console.print(f"[bold]Starting webhook server[/bold] at http://{host}:{port}")
    console.print("[dim]Endpoints: POST /webhook/generate, GET /webhook/jobs/{id}, POST /webhook/jobs/{id}/cancel[/dim]")


@cli.command()
@click.argument("file_path")
@click.option("--provider", default="local", help="Share provider (local, s3)")
@click.option("--root", default=None, help="Working directory")
def share(file_path: str, provider: str, root: str | None) -> None:
    """Upload file to cloud for sharing."""
    from brandly_cli.sharing import share_file
    result = asyncio.run(share_file(Path(file_path), provider=provider, root=root))
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Shared[/green]")
    console.print(f"  URL: {result.get('share_url', 'N/A')}")
    console.print(f"  Provider: {result.get('provider', provider)}")
    if result.get("file_size_bytes"):
        console.print(f"  Size: {(result['file_size_bytes']//1024)}KB")


if __name__ == "__main__":
    main()
