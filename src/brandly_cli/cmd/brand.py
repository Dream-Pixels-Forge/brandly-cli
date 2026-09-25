"""G7 PR 1 (issue #98): `brandly brand` — project-level brand kit.

* `brand init` writes `.brandly/<project>/brand.json` (palette + claims +
  style lock + logo/overlay spec) — project-level only, never user config.
* `brand verify` is fail-closed: a missing or malformed kit exits 1.
* `brand show` renders the kit (text or `--json`).

The gate-layer claim check and export logo overlay ship in G7 PR 2.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from brandly_cli import layout
from brandly_cli.brand_kit import OVERLAY_CORNERS
from brandly_cli.cli import _get_root, console
from brandly_cli.constants import STYLE_PRESET_OPTIONS
from brandly_cli.io import is_valid_project_id


def _resolve(ctx, root, project_id: str) -> Path:
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root_dir = Path(root) if root else _get_root(ctx)
    proj_dir = layout.resolve_project_dir(root_dir, project_id)
    if not proj_dir.is_dir():
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)
    return proj_dir


@click.group("brand")
def brand() -> None:
    """G7: brand-kit enforcement (logo / colour / claim lock)."""


@brand.command("init")
@click.argument("project_id")
@click.option("--logo", default="", help="Brand mark path (project-relative or absolute)")
@click.option("--color", "colors", multiple=True, help="Hex colour, repeatable")
@click.option("--claim", "claims", multiple=True, help="Allowed on-screen claim, repeatable")
@click.option(
    "--style",
    "style",
    default="cinematic",
    show_default=True,
    type=click.Choice(STYLE_PRESET_OPTIONS),
)
@click.option(
    "--overlay-corner",
    "corner",
    default="bottom-right",
    show_default=True,
    type=click.Choice(OVERLAY_CORNERS),
)
@click.option("--overlay-safe-zone", "safe_zone", default=0.1, show_default=True, type=float)
@click.option("--overlay-opacity", "opacity", default=1.0, show_default=True, type=float)
@click.option("--force", is_flag=True, help="Overwrite an existing brand.json")
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def brand_init(
    ctx: click.Context,
    project_id: str,
    logo: str,
    colors: tuple[str, ...],
    claims: tuple[str, ...],
    style: str,
    corner: str,
    safe_zone: float,
    opacity: float,
    force: bool,
    root: str | None,
) -> None:
    """Create the project's brand kit from flags (validates fail-closed)."""
    from brandly_cli import brand_kit

    proj_dir = _resolve(ctx, root, project_id)
    existing = proj_dir / brand_kit.BRAND_FILE
    if existing.is_file() and not force:
        console.print(
            f"[red]Brand kit already exists at {existing} — pass --force to overwrite.[/red]"
        )
        sys.exit(1)
    raw = {
        "version": brand_kit.SCHEMA_VERSION,
        "logo": logo,
        "colors": list(colors),
        "claims": list(claims),
        "style_lock": style,
        "overlay": {"corner": corner, "safe_zone": safe_zone, "opacity": opacity},
    }
    try:
        kit = brand_kit.parse_brand_kit(raw)
    except ValueError as e:
        console.print(f"[red]Invalid brand kit: {e}[/red]")
        sys.exit(1)
    path = brand_kit.save_brand_kit(proj_dir, kit)
    console.print(f"[green]✓ Brand kit written:[/green] {path}")


@brand.command("verify")
@click.argument("project_id")
@click.option("--json", "json_out", is_flag=True, help="Emit the report as JSON")
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def brand_verify(
    ctx: click.Context,
    project_id: str,
    json_out: bool,
    root: str | None,
) -> None:
    """Verify the project's brand kit (fail-closed; exit 1 on any issue)."""
    from brandly_cli import brand_kit

    proj_dir = _resolve(ctx, root, project_id)
    report: dict = {"project_id": project_id, "valid": False, "issues": []}
    kit = None
    try:
        kit = brand_kit.load_brand_kit(proj_dir)
    except ValueError as e:
        report["issues"].append(f"malformed brand.json: {e}")
    if kit is None and not report["issues"]:
        report["issues"].append("no brand.json — run `brandly brand init`")
    elif kit is not None:
        report["issues"].extend(brand_kit.verify_kit(kit, proj_dir))
    report["valid"] = not report["issues"]
    if json_out:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        if report["valid"]:
            console.print(f"[green]✓ brand kit valid:[/green] {project_id}")
        for issue in report["issues"]:
            console.print(f"[red]✗ {issue}[/red]")
    sys.exit(0 if report["valid"] else 1)


@brand.command("show")
@click.argument("project_id")
@click.option("--json", "json_out", is_flag=True, help="Emit the kit as JSON")
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def brand_show(
    ctx: click.Context,
    project_id: str,
    json_out: bool,
    root: str | None,
) -> None:
    """Show the project's brand kit."""
    from brandly_cli import brand_kit

    proj_dir = _resolve(ctx, root, project_id)
    try:
        kit = brand_kit.load_brand_kit(proj_dir)
    except ValueError as e:
        console.print(f"[red]malformed brand.json: {e}[/red]")
        sys.exit(1)
    if kit is None:
        console.print(f"[yellow]No brand kit for {project_id} — run `brandly brand init`.[/yellow]")
        sys.exit(1)
    if json_out:
        print(json.dumps(kit.to_dict(), indent=2, ensure_ascii=False))
        return
    console.print(f"[bold]{project_id}[/bold] — {kit.style_lock} lock")
    console.print(f"  colors: {', '.join(kit.colors)}")
    console.print(f"  claims: {'; '.join(kit.claims)}")
    console.print(f"  logo: {kit.logo or '—'}")
    ov = kit.overlay
    console.print(f"  overlay: {ov.corner} safe_zone={ov.safe_zone} opacity={ov.opacity}")


def register(cli) -> None:  # type: ignore[no-untyped-def]
    cli.add_command(brand)
