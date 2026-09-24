"""Commands for the ``brandly gate`` group.
Moved from cli.py (structural split, no behavioral change).
Shared helpers and state still live in ``brandly_cli.cli``.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import click
from rich.table import Table

from brandly_cli import __version__
from brandly_cli.cli import (
    _get_root,
    _human_review_gate,
    _latest_project_media,
    _load_project_reference,
    _print_gate_report,
    _print_json,
    _print_scene_report,
    _write_review_note,
    cli,
    console,
)
from brandly_cli.cost_tracker import CostTracker
from brandly_cli.memory import UserPreferences
from brandly_cli.project_manager import ProjectManager
from brandly_cli.utils import (
    is_valid_project_id,
)


@click.command()
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

@click.command(name="gate")
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
    "--threshold",
    type=int,
    default=None,
    help=(
        "Quality-score floor (0-100). The gate FAILs when the AI quality_score is "
        "below this value, even if the model's own verdict is pass. Default: no "
        "floor — the gate enforces only deterministic pre-checks plus artifact "
        "cutoffs (distortion>=6/10, slop>=7/10, drift>=6/10)."
    ),
)
@click.option(
    "--lenient",
    is_flag=True,
    help=(
        "Lenient mode: raise artifact fail cutoffs by +2 and demote the model's "
        "own 'fail' verdict to a warning. Deterministic pre-checks still fail the "
        "gate. Use to approve borderline takes."
    ),
)
@click.option(
    "-o",
    "--output",
    type=click.Choice(["text", "json"]),
    default="text",
)
@click.option(
    "--scene",
    "scene_ref",
    default=None,
    help=(
        "Scene mode: gate ONE scene by id (S01) or unique scene number "
        "instead of an element (completeness + per-clip quality)."
    ),
)
@click.option(
    "--all-scenes",
    "all_scenes",
    is_flag=True,
    help="Scene mode: gate every scene of the project manifest.",
)
@click.option(
    "--no-quality",
    "no_quality",
    is_flag=True,
    help="Scene mode: completeness only — skip the per-clip quality gate.",
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
    threshold: int | None,
    lenient: bool,
    output: str,
    scene_ref: str | None,
    all_scenes: bool,
    no_quality: bool,
) -> None:
    """Verify a generated element before proceeding (anti-slop/drift gate).

    Runs cheap offline pre-checks and a multimodal model analysis of the
    candidate (and optional reference). Exits 0 for pass, 1 for warn,
    2 for fail.

    POLICY (issue #34): the gate fails on (1) any deterministic pre-check
    failure, (2) artifact cutoffs distortion>=6/10, slop>=7/10, drift>=6/10,
    or (3) a configured --threshold score floor. --strict promotes warnings
    to failures; --lenient raises the artifact cutoffs and demotes the
    model's 'fail' verdict to a warning. The active policy + score comparison
    are written into the gate report (docs/tmp/gate_*.md).
    """
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)

    root = _get_root(ctx)

    # Scene mode (Goal 3, audit F7): completeness from scenes.json + per-clip
    # quality pre-checks. Independent of the element argument.
    if scene_ref is not None or all_scenes:
        if scene_ref is not None and all_scenes:
            console.print("[red]Use --scene or --all-scenes, not both.[/red]")
            sys.exit(1)
        _run_scene_gate(root, project_id, scene_ref, all_scenes, no_quality, output)
        return  # unreachable — the helper sys.exit()s

    from brandly_cli import quality_gate

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

    if threshold is not None and not (0 <= threshold <= 100):
        console.print("[red]--threshold must be between 0 and 100.[/red]")
        sys.exit(1)

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
            threshold=threshold,
            lenient=lenient,
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


def _run_scene_gate(
    root: Path,
    project_id: str,
    scene_ref: str | None,
    all_scenes: bool,
    no_quality: bool,
    output: str,
) -> None:
    """Scene completeness + quality gate (Goal 3, audit F7). Always sys.exit()s.

    Completeness comes from the scene manifest (missing/stale takes); the
    deterministic quality pre-checks run per present clip unless
    ``--no-quality``. Exits 0 pass / 1 warn / 2 fail — the same contract as
    the element gate.
    """
    from brandly_cli import quality_gate, scenes

    gate_runner = None
    if not no_quality:

        def gate_runner(clip: Path) -> str:  # noqa: F811 — shadows the None above
            result = asyncio.run(
                quality_gate.verify_element(
                    clip,
                    use_ai=False,
                    root=root,
                    project_id=project_id,
                    write_report=False,
                )
            )
            return result.status

    try:
        if all_scenes:
            report = scenes.evaluate_all(project_id, root=root, gate_runner=gate_runner)
        else:
            report = scenes.evaluate(
                project_id, scene_ref or "", root=root, gate_runner=gate_runner
            )
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    if output == "json":
        # Plain print: console.print would wrap/mangle long JSON lines.
        print(json.dumps(report, indent=2))
    else:
        _print_scene_report(report)
    sys.exit({"pass": 0, "warn": 1, "fail": 2}[report["verdict"]])


@click.command()
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

@click.command()
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

@click.command()
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

@click.command()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Show current configuration (API keys status, root dir)."""
    root = _get_root(ctx)

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

@click.command(name="report")
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

def register(cli) -> None:
    cli.add_command(validate)
    cli.add_command(gate)
    cli.add_command(memory)
    cli.add_command(cost)
    cli.add_command(record_cost)
    cli.add_command(config)
    cli.add_command(report)
