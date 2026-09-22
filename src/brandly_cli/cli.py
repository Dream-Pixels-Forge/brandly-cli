"""Thin registration module for the brandly CLI.

Command bodies live in ``brandly_cli.cmd.*``; this module keeps the
root group, the shared helpers the cmd modules import, and the
registration call.
"""

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
from rich.table import Table

from brandly_cli import __version__, layout, shot_runner
from brandly_cli.cost_tracker import CostTracker
from brandly_cli.project_manager import ProjectManager
from brandly_cli.reference_prompts import (  # noqa: F401  # re-exported for cmd modules
    REFERENCE_PROMPT_TEMPLATES,
    REFERENCE_SUBJECTS,
    build_reference_prompt,
)
from brandly_cli.utils import (
    download_file,
    now_iso,
    sanitize_filename,
)

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_root(ctx: click.Context) -> Path:
    root = ctx.obj.get("root")
    if root:
        return Path(root)

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
    filename: str | None = None,
) -> Path | None:
    """Download a generated asset and save it under
    .brandly/{project_id}/{images|videos|audio}/{category}/.

    ``category`` routes the file into a sub-folder (e.g. 'scenes' for video,
    'prop' for object references, 'soundtrack' for music). Omit it to use
    the 'general' default.

    ``filename`` overrides the default ``<type>_<timestamp>_<hint>`` name (used
    for the deterministic ``Scene-XX-Shot-X-Y.mp4`` clip convention).
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
    fname = filename or f"{type_label}_{ts}_{hint}{ext}"
    dest = artifacts_dir / fname
    try:
        asyncio.run(download_file(url, dest))
        return dest
    except Exception as e:
        console.print(f"[yellow]⚠ Could not save artifact: {e}[/yellow]")
        return None


def _standardize_reference_format(saved: Path, target: str) -> Path:
    """Standardize a reference plate's format + dedupe + resolution sanity (issue #41).

    * Converts the plate to ``target`` (``jpg``/``png``) when it differs —
      dropping the now-duplicate original so a plate never exists as both
      .png and .jpg twins.
    * Removes pre-existing duplicate twins (same stem, other extension).
    * Warns when the plate is under 512px on the short side (reference
      quality check — small plates confuse Agnes keyframe mode).

    Never raises: a conversion failure keeps the original file.
    """
    from PIL import Image

    target_ext = ".jpg" if target.lower().startswith("j") else ".png"

    def _remove_twins(p: Path) -> None:
        for twin in p.parent.glob(f"{p.stem}.*"):
            if twin.suffix.lower() in (".png", ".jpg", ".jpeg") and twin != p:
                twin.unlink(missing_ok=True)
                console.print(f"[dim]Removed duplicate-format twin: {twin.name}[/dim]")

    # Normalize .jpeg to the .jpg standard (the on-disk file, not just the path).
    if saved.suffix.lower() == ".jpeg":
        moved = saved.with_suffix(".jpg")
        if moved.exists():
            moved.unlink()
        if saved.exists():
            saved.rename(moved)
        saved = moved

    if saved.suffix.lower() != target_ext:
        try:
            with Image.open(saved) as im:
                mode = "RGBA" if (target_ext == ".png" and "A" in im.getbands()) else "RGB"
                out = saved.with_suffix(target_ext)
                if target_ext == ".jpg":
                    im.convert(mode).save(out, "JPEG", quality=92)
                else:
                    im.convert(mode).save(out, "PNG")
            saved.unlink()
            saved = out
            console.print(f"[dim]Standardized format → {saved.name}[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not convert to {target}: {e} — keeping original[/yellow]")
    _remove_twins(saved)

    # Resolution sanity: reference plates too small degrade Agnes keyframes.
    try:
        with Image.open(saved) as im:
            w, h = im.size
            if min(w, h) < 512:
                console.print(
                    f"[yellow]⚠ Reference plate is small ({w}x{h}) — consider a "
                    "higher-resolution source for reliable identity locking.[/yellow]"
                )
    except Exception:
        pass
    return saved


def _print_project_summary(proj: dict[str, Any]) -> None:

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
# budget check (shared by cmd modules)
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




# ---------------------------------------------------------------------------
# Reference prompt helpers
# ---------------------------------------------------------------------------

# Re-exported at module level (see imports above): REFERENCE_SUBJECTS,
# REFERENCE_PROMPT_TEMPLATES, build_reference_prompt — definitions live
# in brandly_cli.reference_prompts.

# ---------------------------------------------------------------------------
# produce — shot-by-shot generation driven by the production plan
# (issue #22, per production directive: NO batch generation. The production
# plan is the source of truth: every shot is prepared on it first, then
# generation is pulled from the plan one shot at a time at the Agnes
# rate limit of 1 request per minute.)
# ---------------------------------------------------------------------------


def _presence_character(shot: dict[str, Any]) -> str | None:
    """Character anchor from a flat shot dict (issue #38): explicit
    ``character`` wins; else the shot's ``characters`` presence declaration
    (list or comma-separated string)."""
    if shot.get("character"):
        return str(shot["character"])
    chars = shot.get("characters")
    if isinstance(chars, str):
        chars = [c.strip() for c in chars.split(",") if c.strip()]
    if isinstance(chars, (list, tuple)) and chars:
        return ", ".join(str(c) for c in chars)
    return None


def _generate_shot(
    project_id: str,
    shot: dict[str, Any],
    *,
    ctx: click.Context,
    root: Path,
    auto_refs_enabled: bool = True,
    allow_referenceless: bool = False,
    max_wait: int = 600,
    scene: int | None = None,
    shot_number: int | None = None,
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
        from brandly_cli.cmd.generation import video

        ctx.invoke(
            video,
            project_id=project_id,
            prompt=str(shot.get("prompt", "")),
            duration=int(shot.get("duration", 5)),
            style=str(shot.get("style", "cinematic")),
            reference_images=references or None,
            # Issue #38: presence-declared characters only — either a single
            # string anchor or the shot's comma-separated/listed roster.
            character=_presence_character(shot),
            wait=True,
            max_wait=max_wait,
            require_reference=False,
            auto_refs_enabled=auto_refs_enabled,
            allow_referenceless=allow_referenceless,
            scene=scene,
            shot_number=shot_number,
        )
    except SystemExit as exc:
        return exc.code in (0, None)
    return True




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
    *,
    retries: int = 0,
    split_long_shots: bool = False,
    aspect_ratio: str | None = None,
    no_plan: bool = False,
) -> None:
    """Progress-file runner path for ``brandly produce`` (see produce())."""
    project_dir = layout.resolve_project_dir(root, project_id)
    # v2-aware roots (issue #43): migrated projects keep media next to
    # .brandly/ — pre-production/<p>/ for plates, production/<p>/videos/ for clips.
    images_dir = layout.resolve_media_root(root, project_id, "images")
    videos_root = layout.resolve_media_root(root, project_id, "videos")
    scenes_dir = videos_root / "scenes"
    progress = shot_runner.ProgressLog(
        layout.docs_dir(project_dir, "tmp") / shot_runner.PROGRESS_FILENAME
    )
    shots = shot_runner.flatten_shots(data, images_dir, character=character)

    # Issue #35: duration validation at plan time. Agnes clamps every take
    # to ~5-6s regardless of the requested duration, so shots longer than
    # one segment burn full credits for a clamped result. --split-long-shots
    # slices them instead of letting the model silently clamp them.
    over = [
        s for s in shots if s.duration > shot_runner.SPLIT_SEGMENT_DURATION
    ]
    if over:
        console.print(
            f"[yellow]⚠ {len(over)} shot(s) exceed {shot_runner.SPLIT_SEGMENT_DURATION}s and "
            f"will be silently clamped to ~5-6s by the Agnes model: "
            f"{', '.join(s.id for s in over[:8])}" + ("…" if len(over) > 8 else "")
        )
        if not split_long_shots:
            console.print(
                "[dim]  Re-run with --split-long-shots to slice them into "
                f"≤{shot_runner.SPLIT_SEGMENT_DURATION}s parts instead of burning full "
                "credits on clamped takes.[/dim]"
            )
    if split_long_shots:
        shots = shot_runner.split_long_shots(shots)
        if over:
            console.print(
                f"[green]✓ Split over-long shots → {len(shots)} total shots.[/green]"
            )

    # Issue #36: keep project.json live as production progresses.
    def _sync_project(status: str) -> None:
        from brandly_cli.project_manager import sync_production_state

        result = sync_production_state(
            root,
            project_id,
            status=status,
            current_phase="video",
            shot_count=len(shots),
        )
        if result is not None:
            console.print(
                f"[dim]project.json synced: status={status} "
                f"shot_count={len(shots)}[/dim]"
            )

    _sync_project("in_progress")

    # Issue #37: register every shot on the production plan with its shot ID
    # so a reviewer can match plan files to shots without opening them.
    plan_files: dict[str, Path] = {}
    if not no_plan:
        from brandly_cli.utils import write_generation_plan

        model = "agnes-video-2.5-flash"
        for shot in shots:
            plan, _ = write_generation_plan(
                project_id,
                "video",
                root=root,
                prompt=shot.prompt,
                model=model,
                style=shot.style,
                extra_config={
                    "Shot": shot.id,
                    "Duration": f"{shot.duration}s",
                    "Act": shot.act or "—",
                    "Role": "shot",
                },
                source="brandly produce",
                shot_id=shot.id,
                scene=shot.scene,
                act=shot.act or None,
            )
            plan_files[shot.id] = plan

    def _on_shot_done(shot: shot_runner.Shot, ok: bool) -> None:
        # Issue #37: update the plan row; Issue #36: sync project.json.
        plan = plan_files.get(shot.id)
        if plan is not None:
            from brandly_cli.utils import upsert_production_plan

            upsert_production_plan(
                project_id,
                root=root,
                plan_file=str(plan),
                asset_type="video",
                model="agnes-video-2.5-flash",
                status="COMPLETED" if ok else "FAILED",
                source="brandly produce",
                shot_id=shot.id,
            )
        _sync_project("in_progress")

    def generate_one(shot: shot_runner.Shot) -> tuple[bool, int, str]:
        ok = _generate_shot(
            project_id,
            {**shot.to_video_kwargs(), "character": shot.character},
            ctx=ctx,
            root=root,
            auto_refs_enabled=not no_auto_refs,
            allow_referenceless=allow_referenceless,
            max_wait=max_wait,
            # Names the download Scene-XX-Shot-X-Y.mp4 at save time.
            scene=shot.scene,
            shot_number=shot.index_in_scene,
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
        retries=retries,
        on_shot_done=_on_shot_done,
        aspect_ratio=aspect_ratio,
    )
    rc = shot_runner.run_shots(config)
    _sync_project("complete" if rc == 0 else "failed")
    sys.exit(rc)


# ---------------------------------------------------------------------------
# storyboard (issue #33 — cheap keyframe gate before video credits)
# ---------------------------------------------------------------------------

STORYBOARD_INSTRUCTION = (
    "[KEYFRAME] Render a single still frame capturing this exact moment — "
    "composition, lighting, and character placement exactly as directed. "
    "This frame is a storyboard keyframe for pre-visualizing the shot."
)




# ---------------------------------------------------------------------------
# media spend + phase-artifact helpers (shared by cmd modules)
# ---------------------------------------------------------------------------



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
# gate (quality verification before the next step)
# ---------------------------------------------------------------------------




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




# ---------------------------------------------------------------------------
# jobs helpers (shared by cmd modules)
# ---------------------------------------------------------------------------




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






# ---------------------------------------------------------------------------
# ffmpeg availability helpers
# ---------------------------------------------------------------------------




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


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Command groups (structural split — commands live in brandly_cli.cmd.*)
# ---------------------------------------------------------------------------
from brandly_cli.cmd import register  # noqa: E402

register(cli)
