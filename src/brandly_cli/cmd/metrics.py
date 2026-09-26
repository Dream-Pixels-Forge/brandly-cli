"""G8 (issue #99): `brandly metrics` — platform metrics ingest.

* `metrics import <file> --platform youtube [--project <id>]` — CSV/JSON
  snapshot import, fail-closed on unknown platform or malformed rows (G8 PR 1).
* `metrics show [--project <id>]` — latest ingested snapshot per platform.
* `metrics ingest --platform youtube --property <id> [--dry-run]` — G8 PR 2:
  credential-gated YouTube Analytics API pull (dry-run-first, G6 pattern);
  writes the same project-local snapshot files as `import`.

Credentials live in the user config store (`brandly config set
youtube:analytics <token>`), never in project files or `.env` (F2).
TikTok/IG analytics adapters are planned follow-ups (DEV-G8-003).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from brandly_cli import layout
from brandly_cli import youtube_analytics as ya
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


@metrics.command("ingest")
@click.option(
    "--platform", default="youtube", show_default=True, type=click.Choice(SUPPORTED_PLATFORMS)
)
@click.option(
    "--property",
    "property_id",
    default=None,
    help="YouTube Analytics property id (channel) — required",
)
@click.option(
    "--days", default=28, show_default=True, type=int, help="Lookback window for the report"
)
@click.option("--project", "project_id", default=None, help="Project id (default: latest project)")
@click.option("--dry-run", is_flag=True, help="Render the exact request; never call the API")
@click.option("--json", "json_out", is_flag=True, help="Emit the ingest record as JSON")
@click.option(
    "--token",
    default=None,
    help=f"Analytics credential — or store it once with "
    f"`brandly config set {ya.CREDENTIAL_KEY} <token>`",
)
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def metrics_ingest(
    ctx: click.Context,
    platform: str,
    property_id: str | None,
    days: int,
    project_id: str | None,
    dry_run: bool,
    json_out: bool,
    token: str | None,
    root: str | None,
) -> None:
    """Pull real metrics from the YouTube Analytics API (dry-run first)."""
    import brandly_cli.metrics as m
    from brandly_cli import config_store

    if not property_id:
        console.print(
            "[red]Missing --property: pass the YouTube Analytics property "
            "(channel) id, e.g. `--property UC…`.[/red]"
        )
        sys.exit(1)

    adapter = ya.YouTubeAnalyticsAdapter()
    request = adapter.build_request(property_id, days=days)

    if dry_run:
        record = {
            "dry_run": True,
            "platform": platform,
            "request": request,
            "note": "dry-run: no API call was made",
        }
        if json_out:
            print(json.dumps(record, indent=2, ensure_ascii=False))
        else:
            console.print(
                f"[green]✓ dry-run:[/green] exact {request['method']} request "
                f"rendered (nothing was sent)"
            )
            console.print_json(data=request)
        return

    live_token = token or config_store.get_credential(ya.CREDENTIAL_KEY)
    if not live_token:
        console.print(
            f"[red]No {ya.CREDENTIAL_KEY} credential — this would call the "
            f"YouTube Analytics API live, so it fails closed.[/red]\n"
            f"[dim]Store one: `brandly config set {ya.CREDENTIAL_KEY} <token>`, "
            f"or preview without calling: add `--dry-run`.[/dim]"
        )
        sys.exit(1)

    try:
        payload = adapter.execute(request, live_token)
    except Exception as e:
        console.print(f"[red]YouTube Analytics call failed: {e}[/red]")
        sys.exit(1)

    rows = ya.rows_from_report(payload)
    if not rows:
        console.print("[yellow]No metric rows in the report (empty window?)[/yellow]")
        sys.exit(1)

    proj_dir = _resolve_project(ctx, root, project_id)
    try:
        written = m.import_rows(rows, platform, proj_dir)
    except ValueError as e:
        console.print(f"[red]Ingest validation failed: {e}[/red]")
        sys.exit(1)
    for path in written:
        console.print(f"[green]✓ {path.name}[/green] ({platform})")
    console.print(
        f"[green]✓ ingested {len(written)} snapshot(s) for {platform} "
        f"into {proj_dir / m.METRICS_DIR}[/green]"
    )


def register(cli) -> None:  # type: ignore[no-untyped-def]
    cli.add_command(metrics)
