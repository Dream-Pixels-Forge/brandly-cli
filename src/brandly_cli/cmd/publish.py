"""G6: `brandly publish` — credential-gated, dry-run-first publishing (DEV-G6-001).

* `--dry-run` (or no credential) renders the exact request payload; nothing
  is sent.
* Live posting requires a stored credential (`brandly config set <platform>
  <token>`) — missing credentials fail closed with an actionable message.
* Credentials live in the user config dir, never in project files or `.env`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from brandly_cli import layout
from brandly_cli.cli import _get_root, console
from brandly_cli.io import is_valid_project_id


@click.command()
@click.argument("project_id")
@click.option(
    "--platform", default="youtube", show_default=True,
    help="Target platform (first adapter: youtube; see dev-notes/DECISION-G6-PUBLISH-PATH.md)",
)
@click.option("--schedule", default=None, help="ISO-8601 schedule time (private post at that moment)")
@click.option("--dry-run", is_flag=True, help="Render the exact request payload; never post")
@click.option("--json", "json_out", is_flag=True, help="Emit the publish record as JSON")
@click.option("--title", default=None, help="Publish title (default: project ID)")
@click.option("--description", default=None, help="Publish description")
@click.option(
    "--token", default=None,
    help="Publish credential — or store it once with `brandly config set <platform> <token>`",
)
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def publish(
    ctx: click.Context,
    project_id: str,
    platform: str,
    schedule: str | None,
    dry_run: bool,
    json_out: bool,
    title: str | None,
    description: str | None,
    token: str | None,
    root: str | None,
) -> None:
    """Publish a project's exported video to a platform (dry-run first)."""
    from brandly_cli import config_store
    from brandly_cli import publish as pub

    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)

    root_dir = Path(root) if root else _get_root(ctx)
    proj_dir = layout.resolve_project_dir(root_dir, project_id)
    if not proj_dir.is_dir():
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)

    # The video to publish: prefer the per-platform export, then any clip.
    candidates = sorted(
        (proj_dir / "export").glob(f"*_{platform}.mp4"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        candidates = [p for p in (proj_dir / "videos").rglob("*.mp4") if p.is_file()]
    if not candidates:
        console.print(
            f"[yellow]No video found for {project_id} — run "
            f"`brandly stitch` / `export-platforms` first.[/yellow]"
        )
        sys.exit(1)
    video = candidates[0]

    try:
        adapter = pub.get_adapter(platform)
    except KeyError as e:
        console.print(f"[red]Unsupported platform: {e}[/red]")
        sys.exit(1)

    payload = adapter.build_payload(
        video,
        title=title or project_id,
        description=description or "",
        schedule_iso=schedule,
    )

    if dry_run:
        record = {
            "dry_run": True,
            "platform": platform,
            "project_id": project_id,
            "video": str(video),
            "payload": payload,
            "note": "dry-run: no request was sent",
        }
        if json_out:
            print(json.dumps(record, indent=2, ensure_ascii=False))
        else:
            console.print(
                f"[green]✓ dry-run:[/green] payload for {platform} built from {video.name} "
                f"(nothing was posted)"
            )
            console.print_json(data=payload)
        return

    live_token = token or config_store.get_credential(platform)
    if not live_token:
        console.print(
            f"[red]No publish credential for {platform} — this would post live, "
            f"so it fails closed.[/red]\n"
            f"[dim]Store one: `brandly config set {platform} <token>`, or preview "
            f"without posting: add `--dry-run`.[/dim]"
        )
        sys.exit(1)

    try:
        result = adapter.execute(payload, live_token)
    except Exception as e:
        console.print(f"[red]Live publish failed: {e}[/red]")
        sys.exit(1)

    if json_out:
        print(json.dumps(
            {"dry_run": False, "platform": platform, "project_id": project_id, "result": result},
            indent=2,
            ensure_ascii=False,
        ))
    else:
        console.print(f"[green]✓ Published to {platform}[/green] ({result})")


def register(cli) -> None:  # type: ignore[no-untyped-def]
    cli.add_command(publish)
