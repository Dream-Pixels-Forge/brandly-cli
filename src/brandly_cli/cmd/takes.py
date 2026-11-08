"""``brandly takes`` — per-take prompt pack (v0.15.4).

Commands::

    brandly takes list   <project_id> [--scene N] [--json]
    brandly takes export <project_id> [--missing-only] [--force] [--prune] [--dry-run]
    brandly takes apply  <project_id> [--scene N] [--take N] [--clear S.T] [--force] [--dry-run]
    brandly takes status <project_id> [--json]

Exit codes follow the repo gate convention (see ``scenes.py``): ``pass`` → 0,
``warn`` → 1, ``fail`` → 2. ``export``/``apply`` exit 0 on ``pass``/``warn``
(they report what was skipped) and 2 when the operation itself was refused.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.table import Table

from brandly_cli import layout, take_prompts
from brandly_cli.cli import _get_root, console
from brandly_cli.io import is_valid_project_id

_VERDICT_EXIT = {"pass": 0, "warn": 1, "fail": 2}


@click.group(name="takes")
def takes() -> None:
    """Per-take prompt files (``prompts/Scene N/Scene N.T.md``)."""


def _report_exit(report: dict[str, Any], *, status: bool) -> int:
    """Exit code for a report.

    ``status`` maps the verdict to 0/1/2 (a CI gate). ``export``/``apply``
    report the resulting state but only fail when the operation was refused —
    a skipped edited file is ``warn``, not an error.
    """
    if status:
        return _VERDICT_EXIT.get(report.get("verdict", "fail"), 2)
    return 2 if report.get("error") else 0


def _load_shots(ctx: click.Context, project_id: str):
    """Validate the project and load ``shots.json`` (exits 1 on bad input)."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    try:
        return root, take_prompts.load_shots(project_id, root=root)
    except take_prompts.TakePromptError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print(
            "[dim]Run `brandly produce <project-id> --shots <file>` (or write "
            ".brandly/<project-id>/shots.json) first.[/dim]"
        )
        sys.exit(1)


def _print_offenders(report: dict[str, Any]) -> None:
    for entry in report.get("takes", []):
        if entry["state"] in {"in-sync", "unscripted", "unsupported"}:
            continue
        detail = f" — {entry['error']}" if entry.get("error") else ""
        console.print(
            f"  [yellow]{entry['state']}[/yellow] {entry['key']} "
            f"({entry.get('file') or 'no file'}){detail}"
        )
    for entry in report.get("orphans", []):
        console.print(f"  [red]orphan[/red] {entry['file']} — {entry['error']}")
    for entry in report.get("invalid", []):
        console.print(f"  [red]invalid[/red] {entry['file']} — {entry['error']}")


def _print_summary(report: dict[str, Any]) -> None:
    counts = report["counts"]
    parts = [f"{state}={count}" for state, count in counts.items() if count]
    console.print(f"[bold]Prompt pack:[/bold] {' · '.join(parts) or 'empty'}")
    _print_offenders(report)
    if report.get("error"):
        console.print(f"[red]{report['error']}[/red]")
    verdict = report.get("verdict", "fail")
    color = {"pass": "green", "warn": "yellow", "fail": "red"}.get(verdict, "red")
    console.print(f"[{color}]Prompt pack: {verdict.upper()}[/{color}]")


def _print_actions(actions: list[dict[str, Any]], root: Path) -> None:
    if not actions:
        console.print("[dim]No files written.[/dim]")
        return
    for action in actions:
        path = Path(action["path"])
        shown = path.relative_to(root) if path.is_relative_to(root) else path
        console.print(f"[green]{action['action']}[/green] {action['key']} — {shown}")


def _first_line(text: str | None) -> str:
    if not text:
        return ""
    return text.strip().splitlines()[0][:60]


def _file_prompts(root: Path, project_id: str, entries: list[dict[str, Any]]) -> dict[str, str]:
    """Read the first prompt line for every take that has a file on disk."""
    pack = layout.prompts_dir(root, project_id)
    previews: dict[str, str] = {}
    for entry in entries:
        rel = entry.get("file")
        if not rel:
            continue
        try:
            previews[entry["key"]] = _first_line(
                (pack / rel).read_text(encoding="utf-8", errors="replace")
            )
        except OSError:
            previews[entry["key"]] = ""
    return previews


@takes.command(name="status")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Emit the raw matrix as JSON")
@click.pass_context
def takes_status(ctx: click.Context, project_id: str, as_json: bool) -> None:
    """Report drift between the take files and shots.json (exit 0/1/2)."""
    root, data = _load_shots(ctx, project_id)
    report = take_prompts.status(project_id, data, root=root)
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        _print_summary(report)
    sys.exit(_report_exit(report, status=True))


@takes.command(name="list")
@click.argument("project_id")
@click.option("--scene", type=int, default=None, help="Only takes of this scene folder")
@click.option("--json", "as_json", is_flag=True, help="Emit the take inventory as JSON")
@click.pass_context
def takes_list(ctx: click.Context, project_id: str, scene: int | None, as_json: bool) -> None:
    """List takes with their state, clip and prompt preview."""
    root, data = _load_shots(ctx, project_id)
    report = take_prompts.status(project_id, data, root=root)
    entries = report["takes"]
    if scene is not None:
        entries = [entry for entry in entries if entry["scene"] == scene]
        report = {**report, "takes": entries}
    if as_json:
        previews = _file_prompts(root, project_id, entries)
        shot_prompts = {
            take.key: take.prompt for take in take_prompts.iter_takes(data)
        }
        for entry in entries:
            entry["prompt"] = previews.get(entry["key"]) or _first_line(
                shot_prompts.get(entry["key"])
            )
        print(json.dumps(report, indent=2))
        return

    previews = _file_prompts(root, project_id, entries)
    shot_prompts = {take.key: take.prompt for take in take_prompts.iter_takes(data)}

    table = Table(title=f"Prompt pack — {project_id}")
    table.add_column("Take")
    table.add_column("State")
    table.add_column("Scene")
    table.add_column("Clip")
    table.add_column("Prompt")
    table.add_column("File")
    for entry in entries:
        preview = previews.get(entry["key"]) or _first_line(shot_prompts.get(entry["key"]))
        table.add_row(
            f"Scene {entry['key']}",
            entry["state"],
            entry.get("scene_id", ""),
            entry.get("clip", ""),
            preview or "—",
            entry.get("file") or "—",
        )
    console.print(table)
    console.print("[dim]Use --json for the machine-readable inventory.[/dim]")


@takes.command(name="export")
@click.argument("project_id")
@click.option("--missing-only", is_flag=True, help="Only write takes with no file")
@click.option("--force", is_flag=True, help="Overwrite edited/conflicting files")
@click.option("--prune", is_flag=True, help="Delete orphan take files (requires --force)")
@click.option("--dry-run", is_flag=True, help="Print planned writes, write nothing")
@click.pass_context
def takes_export(
    ctx: click.Context,
    project_id: str,
    missing_only: bool,
    force: bool,
    prune: bool,
    dry_run: bool,
) -> None:
    """Create/refresh take files from shots.json prompts."""
    root, data = _load_shots(ctx, project_id)
    if prune and not force:
        console.print("[red]--prune deletes files; it requires --force.[/red]")
        sys.exit(2)
    report = take_prompts.export(
        project_id,
        data,
        root=root,
        force=force,
        missing_only=missing_only,
        prune=prune,
        dry_run=dry_run,
    )
    _print_actions(report.get("actions", []), root)
    if not dry_run:
        _print_summary(report)
    console.print(f"[dim]Resolved pack: {layout.prompts_dir(root, project_id)}[/dim]")
    sys.exit(_report_exit(report, status=False))


@takes.command(name="apply")
@click.argument("project_id")
@click.option("--scene", type=int, default=None, help="Only apply takes of this scene folder")
@click.option("--take", "take_number", type=int, default=None, help="Only apply this take number")
@click.option("--clear", "clear_key", default=None, help="Clear one take by key, e.g. 1.2")
@click.option("--force", is_flag=True, help="Let the take file win a conflict")
@click.option("--dry-run", is_flag=True, help="Print planned writes, write nothing")
@click.pass_context
def takes_apply(
    ctx: click.Context,
    project_id: str,
    scene: int | None,
    take_number: int | None,
    clear_key: str | None,
    force: bool,
    dry_run: bool,
) -> None:
    """Write take-file bodies back into shots.json."""
    root, data = _load_shots(ctx, project_id)
    if clear_key is not None and (scene is not None or take_number is not None):
        console.print("[red]--clear cannot be combined with --scene/--take.[/red]")
        sys.exit(1)
    try:
        report = take_prompts.apply(
            project_id,
            data,
            root=root,
            force=force,
            clear=clear_key,
            scene=scene,
            take=take_number,
            dry_run=dry_run,
        )
    except take_prompts.TakePromptError as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(1)
    _print_actions(report.get("actions", []), root)
    if dry_run:
        console.print("[dim]Dry run — shots.json unchanged.[/dim]")
        if report.get("error"):
            console.print(f"[red]{report['error']}[/red]")
    else:
        _print_summary(report)
    sys.exit(_report_exit(report, status=False))


def register(cli) -> None:  # type: ignore[no-untyped-def]
    cli.add_command(takes)
