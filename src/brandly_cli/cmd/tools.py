"""Commands for the ``brandly tools`` group.
Moved from cli.py (structural split, no behavioral change).
Shared helpers and state still live in ``brandly_cli.cli``.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import click
from rich.panel import Panel
from rich.table import Table

from brandly_cli import __version__
from brandly_cli.cli import (
    _ffmpeg_available,
    _ffprobe_available,
    console,
)
from brandly_cli.sync import SYNC_HANDLERS, TOOLS, detect_tools, sync_keys


@click.command()
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

def register(cli) -> None:
    cli.add_command(sync)
    cli.add_command(version)
    cli.add_command(webhook)
    cli.add_command(share)
