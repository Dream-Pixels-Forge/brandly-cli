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
from typing import Any

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
from brandly_cli.constants import DEFAULT_AGNES_TEXT_MODEL
from brandly_cli.cost_tracker import (
    NOMINAL_VIDEO_SECONDS_PER_DAY,
    CostTracker,
    video_seconds_today,
)
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


_EXPLAIN_SYSTEM = (
    "You are a pipeline failure analyst for brandly-cli. You receive a "
    "quality-gate result (status, score, issues, warnings, checks) and, when "
    "available, the shot's generation prompt and recent progress-log lines. "
    "Explain WHY the gate flagged this element and what to change. Reply "
    "with ONLY a JSON object, no prose:\n"
    '{"diagnoses": [{"shot_id": "...", "likely_cause": "...", '
    '"suggested_change": "...", "suggested_command": "..."}]}\n'
    "Rules:\n"
    "- One entry per distinct failure/warning theme (usually 1-3). Use the "
    "element name as shot_id when no shot id is given.\n"
    "- likely_cause: one concrete sentence mapping the gate issue (e.g. "
    "distortion/slop/drift/threshold/pre-check) to its meaning.\n"
    "- suggested_change: one sentence describing the actual prompt or "
    "generation-parameter change.\n"
    "- suggested_command: a copy-pasteable brandly CLI command, or an empty "
    "string when none fits. Only use the existing surface: re-generate with "
    "`brandly image` / `brandly video` (optionally --llm-enhance), re-check "
    "with `brandly gate <project> <element>` (flags: --strict, --lenient, "
    "--threshold N, --judge-model M, --judge-frames N), or edit the shot "
    "prompt in .brandly/<project>/shots.json. Never invent flags or "
    "subcommands.\n"
    '- "diagnoses" must be a list; use [] when there is nothing to explain.'
)


def _shot_context(
    root: Path, project_id: str, element: Path
) -> dict[str, Any]:
    """Matched shot prompt + recent progress lines (read-only, best-effort).

    Matches the element stem against shot ids in ``<proj>/shots.json``
    (flat list or ``acts``-structured) and collects the last progress-log
    lines mentioning the matched shot or the element itself. Any read
    error silently drops that context source.
    """
    from brandly_cli import layout

    proj = layout.resolve_project_dir(root, project_id)
    stem = element.stem.lower()
    matched_ids: list[str] = []
    shot_ctx: dict[str, Any] = {}

    shots_path = proj / "shots.json"
    if shots_path.is_file():
        try:
            raw = json.loads(shots_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = None
        entries: list[dict[str, Any]] = []
        if isinstance(raw, list):
            entries = [e for e in raw if isinstance(e, dict)]
        elif isinstance(raw, dict):
            acts = raw.get("acts") or {}
            if isinstance(acts, dict):
                for act in acts.values():
                    if isinstance(act, dict):
                        shots = act.get("shots") or []
                        if isinstance(shots, list):
                            entries.extend(s for s in shots if isinstance(s, dict))
        for shot in entries:
            sid = str(shot.get("id") or shot.get("name") or "")
            if not sid:
                continue
            low = sid.lower()
            if stem == low or stem in low or low in stem:
                prompt = shot.get("prompt", "")
                if not isinstance(prompt, str):
                    prompt = json.dumps(prompt, ensure_ascii=False)
                shot_ctx = {"id": sid, "prompt": prompt[:1500]}
                matched_ids.append(low)
                break

    lines: list[str] = []
    for name in ("produce_progress.txt", "storyboard_progress.txt"):
        path = layout.docs_dir(proj, "tmp") / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            line_l = line.lower()
            if stem in line_l or any(mid in line_l for mid in matched_ids):
                lines.append(line)

    ctx: dict[str, Any] = {}
    if shot_ctx:
        ctx["shot"] = shot_ctx
    if lines:
        ctx["progress_log"] = lines[-10:]
    return ctx


def _explain_gate(
    root: Path, project_id: str, element: Path, result: Any
) -> tuple[list[dict[str, str]], str | None]:
    """ONE text-model call turning the gate result into diagnoses.

    Returns ``(diagnoses, error)`` — on failure ``error`` names the reason
    and ``diagnoses`` is empty (fail-open: callers fall back to the plain
    report). Read-only: never writes files.
    """
    from brandly_cli.agnes_client import chat_completion

    context: dict[str, Any] = {
        "element": str(element),
        "gate_result": result.to_dict(),
    }
    context.update(_shot_context(root, project_id, element))
    messages = [
        {"role": "system", "content": _EXPLAIN_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(context, indent=2, ensure_ascii=False),
        },
    ]
    try:
        raw = asyncio.run(
            chat_completion(
                messages,
                model=DEFAULT_AGNES_TEXT_MODEL,
                response_format={"type": "json_object"},
            )
        )
        text = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        from brandly_cli import quality_gate

        parsed = quality_gate._parse_verdict(text or "")
        diags = parsed.get("diagnoses")
        if not isinstance(diags, list):
            return [], "malformed response (no diagnoses list)"
        clean: list[dict[str, str]] = []
        for d in diags:
            if not isinstance(d, dict):
                continue
            clean.append(
                {
                    "shot_id": str(d.get("shot_id") or element.name),
                    "likely_cause": str(d.get("likely_cause") or ""),
                    "suggested_change": str(d.get("suggested_change") or ""),
                    "suggested_command": str(d.get("suggested_command") or ""),
                }
            )
        return clean, None
    except Exception as e:  # noqa: BLE001 — fail-open by design (issue #173)
        return [], e.__class__.__name__


def _print_explanations(diags: list[dict[str, str]]) -> None:
    console.print("[bold]AI explanation:[/bold]")
    for d in diags:
        console.print(f"  [cyan]• {d['shot_id']}[/cyan]: {d['likely_cause']}")
        if d["suggested_change"]:
            console.print(f"      change: {d['suggested_change']}")
        if d["suggested_command"]:
            console.print(f"      try:   [green]{d['suggested_command']}[/green]")


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
@click.option(
    "--judge-model",
    "judge_model",
    default=None,
    help=(
        "Vision-judge model for the AI analysis (issue #170-adjacent: defaults "
        "to agnes-2.5-flash; use agnes-3.0-flash for the 512K-context judge)."
    ),
)
@click.option(
    "--judge-frames",
    "judge_frames",
    type=int,
    default=1,
    show_default=True,
    help=(
        "Multi-frame judging for videos (issue #171): send N (2-8) labeled "
        "frames of the clip in ONE model call with a cross-frame consistency "
        "verdict. Default 1 = single-frame path."
    ),
)
@click.option(
    "--explain",
    is_flag=True,
    help=(
        "After the report, ask a text model to explain failures/warnings and "
        "suggest concrete changes + copy-pasteable commands (issue #173). "
        "Read-only and fail-open; element mode only."
    ),
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
    judge_model: str | None,
    judge_frames: int,
    explain: bool,
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

    if not 1 <= judge_frames <= 8:
        console.print("[red]--judge-frames must be between 1 and 8.[/red]")
        sys.exit(1)

    root = _get_root(ctx)

    # Scene mode (Goal 3, audit F7): completeness from scenes.json + per-clip
    # quality pre-checks. Independent of the element argument.
    if scene_ref is not None or all_scenes:
        if scene_ref is not None and all_scenes:
            console.print("[red]Use --scene or --all-scenes, not both.[/red]")
            sys.exit(1)
        if explain:
            console.print(
                "[dim]--explain applies to the element gate only; "
                "showing the plain scene report.[/dim]"
            )
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
            model=judge_model or DEFAULT_AGNES_TEXT_MODEL,
            root=root,
            project_id=project_id,
            strict=strict,
            threshold=threshold,
            lenient=lenient,
            judge_frames=judge_frames,
        )
    )

    # Issue #173: opt-in failure diagnosis — one text-model call, only when
    # the flag is set AND there is something to explain. Fail-open: on API
    # error / malformed JSON the report output stays exactly as it was.
    explain_diags: list[dict[str, str]] = []
    explain_error: str | None = None
    explain_ran = False
    if explain and (result.issues or result.warnings):
        explain_ran = True
        explain_diags, explain_error = _explain_gate(
            root, project_id, element_path, result
        )

    if output == "json":
        payload = result.to_dict()
        if explain:
            if explain_error:
                payload["explain_error"] = explain_error
            else:
                payload["explain"] = explain_diags
        _print_json(payload)
    else:
        _print_gate_report(result)
        if explain:
            if explain_diags:
                _print_explanations(explain_diags)
            elif explain_error:
                console.print(
                    f"[dim]Explanation unavailable ({explain_error}) — "
                    "see the report above.[/dim]"
                )
            elif explain_ran:
                console.print(
                    "[dim]Model returned no distinct diagnosis for these "
                    "issues.[/dim]"
                )
            else:
                console.print(
                    "[dim]Nothing to explain (no issues or warnings).[/dim]"
                )

    exit_code = (
        0
        if result.status == quality_gate.PASS
        else (1 if result.status == quality_gate.WARN else 2)
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


def apply_brand_claim_gate(report: dict, texts: list[str], kit, project_id: str) -> None:
    """G7 PR 2 (DEV-G7-003): claim-lock hard-fail on the scene gate report.

    Deterministic allowlist check — any non-blank on-screen text outside the
    kit's claims drops the verdict to ``fail`` and records the violations
    under ``report["brand"]``. A compliant project records an empty list so
    the report always shows which layer was checked.
    """
    from brandly_cli import brand_kit

    violations = brand_kit.brand_claim_issues(texts, kit)
    report["brand"] = {
        "project_id": project_id,
        "claims_ok": not violations,
        "violations": violations,
    }
    if violations:
        report["verdict"] = "fail"


def collect_scene_text(manifest: dict | None) -> list[str]:
    """Gather registered on-screen text fields from a scene manifest.

    Forward-compatible: collects ``text_overlay`` / ``caption`` /
    ``captions`` values from every scene/shot entry; absent or blank values
    contribute nothing (they never block the gate).
    """
    texts: list[str] = []
    if not manifest:
        return texts
    entries = manifest.get("scenes", [])
    if not isinstance(entries, list):
        entries = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for key in ("text_overlay", "caption", "captions"):
            value = entry.get(key)
            if isinstance(value, str):
                texts.append(value)
            elif isinstance(value, list):
                texts.extend(str(v) for v in value)
    return texts


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

    # G7 PR 2: brand-kit claim lock — when the project has a kit, any
    # registered on-screen text outside the allowlist hard-fails the gate.
    from brandly_cli import brand_kit, layout

    proj_dir = layout.resolve_project_dir(root, project_id)
    try:
        kit = brand_kit.load_brand_kit(proj_dir)
    except ValueError:
        kit = None
    if kit is not None:
        manifest = scenes.load_scenes(project_id, root=root)
        apply_brand_claim_gate(report, collect_scene_text(manifest), kit, project_id)

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
    # Issue #118: local video-quota accounting (all projects, UTC today) -
    # the actionable number during provider 503/429 waves.
    quota = video_seconds_today(root)
    console.print(
        f"[dim]video-seconds today (UTC, all projects): {quota['seconds']}s / "
        f"{NOMINAL_VIDEO_SECONDS_PER_DAY}s nominal free quota "
        f"({quota['records']} generation(s))[/dim]"
    )


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


@click.group(invoke_without_command=True, name="config")
@click.pass_context
def config(ctx: click.Context) -> None:
    """Show current configuration and manage user-level credentials.

    Without a subcommand this shows the configuration table (legacy
    behavior); ``set``/``get``/``list`` manage publish credentials in the
    user config dir (G6 DEV-G6-001 — never project files, never ``.env``).
    """
    if ctx.invoked_subcommand is not None:
        return

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


@config.command(name="set")
@click.argument("platform")
@click.argument("secret")
def config_set(platform: str, secret: str) -> None:
    """Store a user-level credential (``brandly config set youtube <token>``).

    The secret goes to the user config dir (``~/.brandly/credentials.json``),
    never into project files or ``.env`` (F2).
    """
    from brandly_cli import config_store

    config_store.set_credential(platform, secret)
    console.print(
        f"[green]✓[/green] Stored {platform} credential in "
        f"{config_store._store_path()} (user-level; never written to project files)"
    )


@config.command(name="get")
@click.argument("platform")
def config_get(platform: str) -> None:
    """Show whether a credential is stored (the secret value is never shown)."""
    from brandly_cli import config_store

    state = "stored" if config_store.has_credential(platform) else "not stored"
    console.print(f"{platform}: {state}")


@config.command(name="list")
def config_list() -> None:
    """List platforms with stored credentials."""
    from brandly_cli import config_store

    names = config_store.credential_names()
    console.print(", ".join(names) if names else "[dim]No credentials stored.[/dim]")


@click.command(name="report")
@click.option(
    "--error",
    "-e",
    default=None,
    help="Error message to report (otherwise interactive prompt)",
)
@click.option(
    "--project",
    "-p",
    default=None,
    help="Project ID to attach context to",
)
@click.option(
    "--root",
    default=None,
    help="Brandly root directory",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show issue body without submitting",
)
@click.option(
    "--auto",
    is_flag=True,
    help="Submit without asking (requires prior consent or GITHUB_TOKEN)",
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

    root_path = (
        Path(root)
        if root
        else _get_root(click.get_current_context(silent=True) or click.Context(cli))
    )
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
            console.print(f"[red]Report failed: {result.get('error') or result}[/red]")
        return

    if ask_permission(ctx, body):
        console.print("[dim]Submitting issue to GitHub...[/dim]")
        result = submit_issue(ctx, body)
        if result.get("ok"):
            console.print(f"[green]✓ Issue opened: {result['url']}[/green]")
            console.print(f"  Number: #{result.get('number')}")
        else:
            console.print(f"[red]Report failed: {result.get('error') or result}[/red]")
    else:
        console.print("[dim]Issue report skipped.[/dim]")


_DRIFT_SYSTEM = (
    "You are a cross-shot consistency analyst for brandly-cli. You receive "
    "ALL shot prompts of one campaign (plus style/aspect context). Find "
    "prompt drift: places where a shot would break the campaign's visual "
    "continuity BEFORE any frames are generated.\n"
    "Reply with ONLY a JSON object, no prose:\n"
    '{"drifts": [{"shot_ids": ["..."], "dimension": '
    '"character|lighting|style|aspect|voice", "evidence": "...", '
    '"severity": "high|medium|low", "suggested_fix": "..."}]}\n'
    "Rules:\n"
    "- dimension: character (name/identity/wardrobe drift), lighting "
    "(key/fill/mood flips), style (off-preset look), aspect (mixed frame "
    "geometry), voice (narration/tone shifts).\n"
    "- severity high = would visibly break continuity for a viewer; "
    "medium = noticeable inconsistency; low = nitpick.\n"
    "- evidence quotes or paraphrases the exact prompt text that drifts.\n"
    "- suggested_fix is a copy-pasteable replacement phrase or sentence.\n"
    "- shot_ids must reference existing shot ids.\n"
    '- "drifts" must be a list; use [] when the campaign is consistent.'
)


def _campaign_shots(shots_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """ALL shots + style context from ``<proj>/shots.json`` (read-only).

    Accepts the flat list or the ``acts``-structured object form.
    Raises ``OSError``/``json.JSONDecodeError``/``ValueError`` on unreadable
    or structurally-invalid files — the caller turns those into exit 2.
    """
    raw = json.loads(shots_path.read_text(encoding="utf-8"))
    raw_shots: list[dict[str, Any]] = []
    meta: dict[str, Any] = {}
    if isinstance(raw, list):
        raw_shots = [s for s in raw if isinstance(s, dict)]
    elif isinstance(raw, dict):
        meta["campaign"] = {k: v for k, v in raw.items() if k != "acts"}
        acts = raw.get("acts") or {}
        if isinstance(acts, dict):
            acts_meta: list[dict[str, Any]] = []
            for act_name, act in acts.items():
                if not isinstance(act, dict):
                    continue
                acts_meta.append(
                    {
                        "name": act_name,
                        **{
                            k: act[k]
                            for k in ("style", "prefix", "folder", "scene")
                            if k in act
                        },
                    }
                )
                for s in act.get("shots") or []:
                    if isinstance(s, dict):
                        raw_shots.append(s)
            if acts_meta:
                meta["acts"] = acts_meta
    else:
        raise ValueError("shots.json must be a list or an object")

    shots: list[dict[str, Any]] = []
    for i, shot in enumerate(raw_shots, start=1):
        sid = str(shot.get("id") or shot.get("name") or f"shot-{i}")
        prompt = shot.get("prompt", "")
        if not isinstance(prompt, str):
            prompt = json.dumps(prompt, ensure_ascii=False)
        entry: dict[str, Any] = {"id": sid, "prompt": prompt[:4000]}
        for key in ("style", "aspect", "aspect_ratio", "camera"):
            if key in shot:
                entry[key] = shot[key]
        shots.append(entry)
    return shots, meta


def _print_drift_report(drifts: list[dict[str, Any]], total: int) -> None:
    if not drifts:
        console.print(f"[green]✓ No prompt drift across {total} shots.[/green]")
        return
    sev_color = {"high": "red", "medium": "yellow", "low": "dim"}
    table = Table(
        title=f"Prompt drift — {len(drifts)} finding(s) across {total} shots"
    )
    table.add_column("Shots", style="cyan")
    table.add_column("Dimension")
    table.add_column("Severity")
    table.add_column("Evidence")
    table.add_column("Suggested fix")
    for d in drifts:
        sev = str(d.get("severity", ""))
        table.add_row(
            ", ".join(str(s) for s in d.get("shot_ids", [])) or "—",
            str(d.get("dimension", "")),
            f"[{sev_color.get(sev, 'white')}]{sev}[/]",
            str(d.get("evidence", "")),
            str(d.get("suggested_fix", "")),
        )
    console.print(table)
    console.print(
        "[dim]Read-only: apply fixes to shots.json yourself, then "
        "re-generate.[/dim]"
    )


@click.command(name="gate-drift")
@click.argument("project_id")
@click.option(
    "--strict",
    is_flag=True,
    help="CI mode: exit 1 when any high-severity drift exists.",
)
@click.option(
    "-o",
    "--output",
    type=click.Choice(["text", "json"]),
    default="text",
)
@click.pass_context
def gate_drift(
    ctx: click.Context, project_id: str, strict: bool, output: str
) -> None:
    """Check ALL shot prompts for cross-shot drift BEFORE generation.

    One text-model call compares every shot against the campaign's
    character/lighting/style/aspect/voice baseline and prints the drifts
    as a table (issue #174). Read-only — never edits prompts.

    Exit codes: 0 = report (or none found), 1 = --strict with a
    high-severity drift, 2 = error (no shots, API failure, bad response).
    """
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(2)

    from brandly_cli import layout, quality_gate

    root = _get_root(ctx)
    shots_file = layout.resolve_project_dir(root, project_id) / "shots.json"
    if not shots_file.is_file():
        console.print(
            f"[red]No shots.json for project '{project_id}' "
            f"({shots_file}).[/red]"
        )
        sys.exit(2)
    try:
        shots, meta = _campaign_shots(shots_file)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        console.print(f"[red]Could not read shots.json: {e}[/red]")
        sys.exit(2)
    if not shots:
        console.print(
            f"[red]shots.json has no shots for project '{project_id}'.[/red]"
        )
        sys.exit(2)

    from brandly_cli.agnes_client import chat_completion

    context: dict[str, Any] = {"project_id": project_id, "shots": shots}
    context.update(meta)
    messages = [
        {"role": "system", "content": _DRIFT_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(context, indent=2, ensure_ascii=False),
        },
    ]
    try:
        raw = asyncio.run(
            chat_completion(
                messages,
                model=DEFAULT_AGNES_TEXT_MODEL,
                response_format={"type": "json_object"},
            )
        )
    except Exception as e:  # noqa: BLE001 — fail-open by design (issue #174)
        console.print(
            f"[red]Prompt-drift check failed: "
            f"{e.__class__.__name__}: {e}[/red]"
        )
        sys.exit(2)

    text = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
    parsed = quality_gate._parse_verdict(text or "")
    drifts = parsed.get("drifts") if isinstance(parsed, dict) else None
    if not isinstance(drifts, list):
        console.print(
            "[red]Prompt-drift check failed: response was not valid "
            "drift JSON.[/red]"
        )
        if text:
            console.print("[dim]Response tail:[/dim]")
            console.print(text[-400:])
        sys.exit(2)

    clean: list[dict[str, Any]] = []
    for d in drifts:
        if not isinstance(d, dict):
            continue
        clean.append(
            {
                "shot_ids": [
                    str(s) for s in d.get("shot_ids") or [] if s is not None
                ],
                "dimension": str(d.get("dimension") or ""),
                "evidence": str(d.get("evidence") or ""),
                "severity": str(d.get("severity") or "").lower(),
                "suggested_fix": str(d.get("suggested_fix") or ""),
            }
        )

    high = any(d["severity"] == "high" for d in clean)
    if output == "json":
        _print_json(
            {
                "project_id": project_id,
                "shots": len(shots),
                "drifts": clean,
                "high": high,
                "strict": strict,
            }
        )
    else:
        _print_drift_report(clean, len(shots))
    if strict and high:
        sys.exit(1)


def register(cli) -> None:
    cli.add_command(validate)
    cli.add_command(gate)
    cli.add_command(gate_drift)
    cli.add_command(memory)
    cli.add_command(cost)
    cli.add_command(record_cost)
    cli.add_command(config)
    cli.add_command(report)
