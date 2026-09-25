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

from brandly_cli import __version__, layout
from brandly_cli.cost_tracker import CostTracker, record_media_spend
from brandly_cli.gates import (
    human_review_gate,
    print_gate_report,
    write_review_note,
)
from brandly_cli.io import save_artifact
from brandly_cli.project_manager import ProjectManager
from brandly_cli.reference_prompts import (  # noqa: F401  # re-exported for cmd modules
    REFERENCE_PROMPT_TEMPLATES,
    REFERENCE_SUBJECTS,
    build_reference_prompt,
)

console = Console()

# Deprecated re-exports — moved helpers keep their old names so the
# ``cmd/*`` imports (``from brandly_cli.cli import _record_media_spend`` …)
# keep working until the cmd modules switch to the new modules.
_record_media_spend = record_media_spend
_save_artifact = save_artifact
_print_gate_report = print_gate_report
_human_review_gate = human_review_gate
_write_review_note = write_review_note


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


class _LazyCommandGroup(click.Group):
    """Root group that registers the ``cmd.*`` groups on first command lookup.

    Registration is deliberately deferred instead of happening at import time:
    every ``brandly_cli.cmd.<module>`` imports its shared helpers from this
    module, so importing the ``cmd`` package here would close a cycle and make
    ``import brandly_cli.cmd.<module>`` fail on a partially-initialized package.
    Deferring keeps every import order working — ``brandly_cli.cli``,
    ``brandly_cli.cmd.<module>``, ``python -m brandly_cli`` and
    ``python -m brandly_cli.cli`` all behave identically.
    """

    def _ensure_registered(self) -> None:
        if self.commands:
            return
        from brandly_cli.cmd import register

        register(self)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        self._ensure_registered()
        return super().get_command(ctx, cmd_name)

    def list_commands(self, ctx: click.Context) -> list[str]:
        self._ensure_registered()
        return super().list_commands(ctx)


@click.group(cls=_LazyCommandGroup)
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
    root_proj = Path(root)
    missing: list[tuple[str, Path]] = []

    if phase == "asset":
        videos = list((root_proj / "production" / project_id / "videos").rglob("*.mp4"))
        images = list((root_proj / "pre-production" / project_id).rglob("*"))
        images = [p for p in images if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
        if not videos and not images:
            missing.append(("video or image", root_proj / "production" / project_id / "videos"))

    elif phase == "audio":
        audios = list((root_proj / "production" / project_id / "audio").rglob("*"))
        audios = [p for p in audios if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg")]
        # A silent-track-only project is still acceptable if there are videos (voiceover optional)
        if not audios:
            videos = list((root_proj / "production" / project_id / "videos").rglob("*.mp4"))
            if not videos:
                missing.append(("audio file", root_proj / "production" / project_id / "audio"))

    elif phase == "re_edit":
        videos = list((root_proj / "production" / project_id / "videos").rglob("*.mp4"))
        if not videos:
            missing.append(("video clip", root_proj / "production" / project_id / "videos"))

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


def _print_scene_report(report: dict[str, Any]) -> None:
    """Human-readable scene completeness (+ quality) matrix (Goal 3).

    Accepts either a single-scene report (``gate --scene``) or the full
    matrix (``scenes status`` / ``gate --all-scenes``).
    """
    entries = report.get("scenes") or [report]
    table = Table(title=f"Scene completeness — {report.get('project_id', '')}")
    table.add_column("Scene", style="cyan")
    table.add_column("#", justify="right")
    table.add_column("Act")
    table.add_column("Clips", justify="right")
    table.add_column("Missing", justify="right")
    table.add_column("Stale", justify="right")
    table.add_column("Verdict")
    for entry in entries:
        table.add_row(
            entry.get("id", "?"),
            str(entry.get("scene", "")),
            entry.get("act") or "—",
            f"{entry.get('present', 0)}/{entry.get('expected', 0)}",
            str(len(entry.get("missing", []))),
            str(len(entry.get("stale", []))),
            entry.get("verdict", "?"),
        )
    console.print(table)
    for entry in entries:
        for item in entry.get("missing", []):
            console.print(f"  [red]✗ missing[/red] {item['id']} — {item['clip']}")
        for item in entry.get("stale", []):
            console.print(
                f"  [red]✗ stale[/red] {item['id']} — {', '.join(item['files'])}"
            )
        quality = entry.get("quality")
        if quality:
            if quality.get("skipped"):
                console.print("  [dim]quality: skipped (--no-quality)[/dim]")
            else:
                for failure in quality.get("failures", []):
                    console.print(
                        f"  [red]✗ quality[/red] {failure['id']} — "
                        f"{failure['clip']}: {failure['status']}"
                    )
                console.print(
                    f"  [dim]quality: {quality.get('checked', 0)} checked, "
                    f"{len(quality.get('failures', []))} flagged[/dim]"
                )
    verdict = report.get("verdict", "fail")
    color = {"pass": "green", "warn": "yellow", "fail": "red"}.get(verdict, "red")
    console.print(f"[{color}]Scene gate: {verdict.upper()}[/{color}]")


if __name__ == "__main__":
    main()


# NOTE: the command groups live in ``brandly_cli.cmd.*`` and are attached by
# ``_LazyCommandGroup`` on first command lookup — see that class for why
# registration is not performed at import time (cli ⇄ cmd import cycle).
