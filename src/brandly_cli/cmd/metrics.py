"""G8 PR 1 (issue #99): `brandly metrics` — project-local metrics ingest.

* `metrics import <file> --platform youtube [--project <id>]` — CSV/JSON
  snapshot import, fail-closed on unknown platform or malformed rows.
* `metrics show [--project <id>]` — latest ingested snapshot per platform.

No network, no credentials in this command group; the YouTube Analytics
API adapter (`metrics ingest`) is G8 PR 2.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from brandly_cli import layout
from brandly_cli.cli import _get_root, console
from brandly_cli.io import is_valid_project_id
from brandly_cli.metrics import SUPPORTED_PLATFORMS


def _resolve_project(ctx, root: str | None, project_id: str | None) -> Path:
    """Resolve a project: explicit id (fail-closed) or the latest project."""
    root_dir = Path(root) if root else _get_root(ctx)
    if project_id:
        if not is_valid_project_id(project_id):
            console.print("[red]Invalid project ID format.[/red]")
            sys.exit(1)
        proj_dir = layout.resolve_project_dir(root_dir, project_id)
        if not proj_dir.is_dir():
            console.print(f"[red]Project not found: {project_id}[/red]")
            sys.exit(1)
        return proj_dir
    projects = (
        [p for p in layout.brandly_dir(root_dir).iterdir() if p.is_dir()]
        if layout.brandly_dir(root_dir).is_dir()
        else []
    )
    if not projects:
        console.print(
            "[red]No projects found — pass --project <id> or run `brandly init` first.[/red]"
        )
        sys.exit(1)

    def _mtime(p: Path) -> float:
        pj = p / "project.json"
        return pj.stat().st_mtime if pj.is_file() else 0.0

    return max(projects, key=_mtime)


@click.group("metrics")
def metrics() -> None:
    """G8: platform metrics ingest (CSV/JSON import; no network yet)."""


@metrics.command("import")
@click.argument("file", metavar="METRICS_FILE")
@click.option(
    "--platform", default="youtube", show_default=True, type=click.Choice(SUPPORTED_PLATFORMS)
)
@click.option("--project", "project_id", default=None, help="Project id (default: latest project)")
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def metrics_import(
    ctx: click.Context,
    file: str,
    platform: str,
    project_id: str | None,
    root: str | None,
) -> None:
    """Import a CSV/JSON metrics file into the project's snapshot store."""
    from brandly_cli import metrics as m

    proj_dir = _resolve_project(ctx, root, project_id)
    try:
        written = m.import_metrics(file, platform, proj_dir)
    except ValueError as e:
        console.print(f"[red]Import failed: {e}[/red]")
        sys.exit(1)
    for path in written:
        console.print(f"[green]✓ {path.name}[/green] ({platform})")
    for path in written:
        console.print(f"[green]✓ {path.name}[/green] ({platform})")
    console.print(
        f"[green]✓ imported {len(written)} snapshot(s) for {platform} "
        f"into {proj_dir / m.METRICS_DIR}[/green]"
    )


@metrics.command("show")
@click.option("--project", "project_id", default=None, help="Project id (default: latest project)")
@click.option("--json", "json_out", is_flag=True, help="Emit the summary as JSON")
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def metrics_show(
    ctx: click.Context,
    project_id: str | None,
    json_out: bool,
    root: str | None,
) -> None:
    """Show the latest ingested metrics snapshot per platform."""
    from brandly_cli import metrics as m

    proj_dir = _resolve_project(ctx, root, project_id)
    summary = m.summarize(proj_dir)
    if json_out:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        if not summary:
            console.print(
                "[yellow]No ingested metrics for this project — run "
                "`brandly metrics import` first.[/yellow]"
            )
            sys.exit(1)
        for platform, info in summary.items():
            row = info["latest_row"] or {}
            console.print(
                f"[bold]{platform}[/bold] — {info['date']} "
                f"({info['row_count']} row{'s' if info['row_count'] != 1 else ''})"
            )
            console.print(
                f"  views={row.get('views')} likes={row.get('likes')} "
                f"watch_time_s={row.get('watch_time_seconds')} "
                f"ctr_pct={row.get('ctr_pct')}"
            )


def register(cli) -> None:  # type: ignore[no-untyped-def]
    cli.add_command(metrics)
