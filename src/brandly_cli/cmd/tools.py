"""Commands for the ``brandly tools`` group.
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
from rich.panel import Panel
from rich.table import Table

from brandly_cli import __version__, layout
from brandly_cli.cli import (
    _ffmpeg_available,
    _ffprobe_available,
    console,
)
from brandly_cli.sync import SYNC_HANDLERS, TOOLS, detect_tools, sync_keys
from brandly_cli.utils import (
    _read_production_plan_rows,
    production_plan_path,
)


@click.command()
@click.option(
    "--tools", default=None, help="Comma-separated tool names to sync (default: all detected)"
)
@click.option("--dry-run", is_flag=True, help="Show what would be synced without writing")
@click.option(
    "--legacy-provider-keys",
    "legacy_provider_keys",
    is_flag=True,
    default=False,
    help="Write AGNES/MINIMAX API keys into AI-tool config files (opt-in; "
    "AI tools should use `brandly mcp serve` instead)",
)
@click.pass_context
def sync(
    ctx: click.Context, tools: str | None, dry_run: bool, legacy_provider_keys: bool
) -> None:
    """Auto-detect AI-tool configs; write Brandly API keys ONLY on explicit opt-in.

    Default (safe): nothing secret is written — AI tools should connect through
    `brandly mcp serve` / `brandly tools --json`, which keeps the pipeline
    (naming, references, retries, gates, cost tracking) in charge.

    \b
    With --legacy-provider-keys: reads AGNES_API_KEY and MINIMAX_API_KEY from the
    environment and writes them into supported AI-tool config files.
    Supported tools: qwen, claude, gemini, codex, pi, opencode
    """

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

    messages = sync_keys(
        tools=selected,
        include_dotenv=not dry_run,
        legacy_provider_keys=legacy_provider_keys,
    )
    if messages:
        console.print(Panel("\n".join(messages), title="Sync Result"))
    else:
        console.print("[dim]Nothing to sync.[/dim]")

@click.command()
@click.option(
    "--json",
    "json_out",
    is_flag=True,
    help="Emit the full tool manifest as machine-readable JSON (Goal 1)",
)
def tools(json_out: bool) -> None:
    """List the agent-callable tool surface (manifest for AI tools / MCP clients).

    \b
    Examples:
      brandly tools --json          # manifest for an AI tool to consume
      brandly tools                 # human-readable list
    """
    from brandly_cli import agent_surface

    manifest = agent_surface.tool_manifest()
    if json_out:
        # Printed raw (not through rich) so stdout parses as exactly one document.
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return

    table = Table(title=f"Brandly agent tools ({len(manifest['tools'])})")
    table.add_column("Tool", style="cyan")
    table.add_column("Kind", style="dim")
    table.add_column("Access", style="white")
    table.add_column("Command", style="dim")
    table.add_column("Description", style="white")
    for entry in manifest["tools"]:
        table.add_row(
            entry["name"],
            entry["kind"],
            "read-only" if entry["read_only"] else "write",
            entry["command"] or "-",
            entry["description"],
        )
    console.print(table)


@click.group()
def mcp() -> None:
    """Model Context Protocol server — let an AI tool drive brandly directly."""


@mcp.command()
@click.option(
    "--root",
    default=None,
    help="Working directory (default: walk up from cwd looking for .brandly)",
)
def serve(root: str | None) -> None:
    """Serve the brandly tool surface over stdio as JSON-RPC 2.0 (newline-delimited).

    \b
    Configure your AI tool with:
      command: brandly
      args:    ["mcp", "serve"]

    Exposes exactly what `brandly tools --json` lists: the real pipeline
    (produce, stitch, export-platforms, job-poll, image) plus read-only state.
    \b
    Examples:
      brandly mcp serve
      brandly mcp serve --root /path/to/brandly-home
    """
    from brandly_cli import mcp_server

    mcp_server.serve_stdio(sys.stdin, sys.stdout, root=root)


@click.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold]brandly-cli[/bold] v{__version__}")
    console.print(f"  Python: {sys.version.split()[0]}")
    console.print(f"  Platform: {sys.platform}")
    ffmpeg_ok = _ffmpeg_available()
    ffprobe_ok = _ffprobe_available()
    console.print(f"  FFmpeg: {'✓' if ffmpeg_ok else '✗ (install for edit/captions/concat)'}")
    console.print(f"  FFprobe: {'✓' if ffprobe_ok else '✗ (install for analyze)'}")

@click.command()
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

@click.command()
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


@click.command()
@click.argument("project_id")
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def analyze_project(ctx: click.Context, project_id: str, root: str | None) -> None:
    """Analyze a project: what exists vs what the screenplay/plan requires."""
    from brandly_cli.cli import _get_root
    from brandly_cli.project_manager import ProjectManager

    root_path = Path(root) if root else _get_root(ctx)
    pm = ProjectManager(root_path)
    proj = asyncio.run(pm.read(project_id))
    if not proj:
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)

    console.print(f"[bold]Project Analysis: {proj.name or project_id}[/bold]")
    console.print(f"  Style: {proj.style} | Shots: {proj.shot_count} | Status: {proj.status}")
    console.print()

    # --- Production plan rows ---
    plan_path = production_plan_path(project_id, root=root_path)
    rows = _read_production_plan_rows(plan_path) if plan_path.exists() else {}

    if not rows:
        console.print("[yellow]No production plan found. Run `brandly director` first.[/yellow]")
        console.print()
        _print_missing_assets_summary(root_path, project_id, proj)
        return

    # --- Group by asset type ---
    by_type: dict[str, list[dict[str, str]]] = {}
    for _, info in rows.items():
        asset = info.get("asset", "")
        by_type.setdefault(asset, []).append(info)

    # --- Render per-type tables ---
    for asset_type, items in sorted(by_type.items()):
        table = Table(title=f"{asset_type.title()} Assets ({len(items)})")
        table.add_column("Plan File", style="cyan")
        table.add_column("Shot ID", style="dim")
        table.add_column("Status", style="white")
        table.add_column("Created", style="dim")
        for info in items:
            status = info.get("status", "?")
            status_style = {
                "COMPLETED": "green",
                "PENDING": "yellow",
                "FAILED": "red",
                "RUNNING": "blue",
            }.get(status, "white")
            table.add_row(
                info.get("asset", ""),
                info.get("shot_id", ""),
                f"[{status_style}]{status}[/]",
                info.get("updated", "")[:10],
            )
        console.print(table)

    # --- Missing assets check ---
    console.print()
    _print_missing_assets_summary(root_path, project_id, proj)


def _print_missing_assets_summary(root: Path, project_id: str, proj: Any) -> None:
    """Check what media files exist vs what the project needs."""
    images_dir = layout.resolve_media_root(root, project_id, "images")
    videos_dir = layout.resolve_media_root(root, project_id, "videos")
    audio_dir = layout.resolve_media_root(root, project_id, "audio")

    # Count existing assets
    image_files = list(images_dir.rglob("*")) if images_dir.exists() else []
    image_files = [f for f in image_files if f.is_file()]
    video_files = list(videos_dir.rglob("*.mp4")) if videos_dir.exists() else []
    audio_files = list(audio_dir.rglob("*")) if audio_dir.exists() else []
    audio_files = [f for f in audio_files if f.is_file()]

    shot_count = getattr(proj, "shot_count", 0) or 5

    console.print("[bold]Asset Summary[/bold]")
    console.print(f"  Images (plates):   {len(image_files)} found")
    console.print(f"  Videos (clips):    {len(video_files)} found (need ~{shot_count})")
    console.print(f"  Audio:             {len(audio_files)} found")

    missing_videos = max(0, shot_count - len(video_files))
    if missing_videos > 0:
        console.print(f"  [yellow]⚠ {missing_videos} video clip(s) still needed[/yellow]")

    has_references = any(f.name.startswith("reference_") for f in image_files)
    if not has_references and image_files:
        console.print("  [yellow]⚠ No primary reference image found — run `brandly reference`[/yellow]")
    elif not image_files:
        console.print("  [yellow]⚠ No reference images found — run `brandly reference` first[/yellow]")

    console.print()
    console.print("[dim]Tip: Run `brandly produce <id> --shots shots.json` to generate missing clips.[/dim]")


def register(cli) -> None:
    cli.add_command(sync)
    cli.add_command(tools)
    cli.add_command(mcp)
    cli.add_command(version)
    cli.add_command(webhook)
    cli.add_command(share)
    cli.add_command(analyze_project)
