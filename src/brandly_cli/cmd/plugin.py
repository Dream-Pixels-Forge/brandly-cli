"""G8 PR 3/3: `brandly plugin` — plugin system for extensibility.

* `brandly plugin list` — list available plugins
* `brandly plugin load` — load a plugin
* `brandly plugin create` — create a new plugin skeleton
* `brandly plugin info` — show plugin information
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from brandly_cli.cli import _get_root, console
from brandly_cli.plugin_system import (
    PluginError,
    PluginLoadError,
    PluginNotFoundError,
    create_plugin_structure,
    get_plugin_commands,
    get_plugins_dir,
    list_available_plugins,
    load_plugin,
)


def _resolve_plugin_ctx(ctx: click.Context | None, plugin_name: str) -> Path:
    """Resolve plugin name to plugin directory path."""
    plugins_dir = get_plugins_dir(_get_root(ctx) if ctx else None)
    plugin_dir = plugins_dir / plugin_name

    if not plugin_dir.exists():
        console.print(f"[red]Plugin not found:[/red] {plugin_name}")
        sys.exit(1)

    if not (plugin_dir / "plugin.py").exists():
        console.print(f"[red]Invalid plugin:[/red] {plugin_name} (missing plugin.py)")
        sys.exit(1)

    return plugin_dir


@click.group("plugin")
def plugin_group() -> None:
    """🔌 Plugin system for extensibility."""


@plugin_group.command("list")
@click.option("--json", "json_out", is_flag=True, help="Emit machine-readable JSON")
def plugin_list(json_out: bool) -> None:
    """List available plugins."""
    plugins = list_available_plugins()

    if json_out:
        plugin_data = []
        for plugin_name in plugins:
            try:
                cmds = get_plugin_commands(plugin_name)
            except PluginError:
                cmds = []
            plugin_data.append({
                "name": plugin_name,
                "commands": cmds,
            })
        print(json.dumps(plugin_data, indent=2, ensure_ascii=False))
        return

    if not plugins:
        console.print("[yellow]No plugins found.[/yellow]")
        console.print("Create a plugin with: [code]brandly plugin create <name>[/code]")
        return

    from rich.table import Table

    table = Table(title="Available Plugins")
    table.add_column("Plugin Name")
    table.add_column("Status")
    table.add_column("Commands", style="dim")

    for plugin_name in plugins:
        try:
            commands = get_plugin_commands(plugin_name)
            table.add_row(plugin_name, "available", str(len(commands)))
        except PluginError:
            table.add_row(plugin_name, "error", "0")

    console.print(table)


@plugin_group.command("load")
@click.argument("plugin_name")
def plugin_load(plugin_name: str) -> None:
    """Load a plugin."""
    try:
        load_plugin(plugin_name)
        console.print(f"[green]✓ Plugin loaded:[/green] {plugin_name}"
        )
    except PluginNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    except PluginLoadError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error loading plugin:[/red] {e}")
        sys.exit(1)


@plugin_group.command("create")
@click.argument("plugin_name")
@click.option("--description", default="", help="Plugin description")
def plugin_create(
    plugin_name: str,
    description: str,
) -> None:
    """Create a new plugin skeleton."""
    try:
        plugin_dir = create_plugin_structure(plugin_name)
        console.print(f"[green]✓ Plugin created:[/green] {plugin_name}")
        console.print(f"  Location: [dim]{plugin_dir}[/dim]")
        console.print(f"  Edit [code]{plugin_dir}/plugin.py[/code] to implement your plugin")
        console.print(f"  Add commands to [code]{plugin_dir}/commands/[/code]")
        if description:
            console.print(f"  Description: {description}")
    except Exception as e:
        console.print(f"[red]Failed to create plugin:[/red] {e}")
        sys.exit(1)


@plugin_group.command("info")
@click.argument("plugin_name")
def plugin_info(plugin_name: str) -> None:
    """Show information about a plugin."""
    try:
        plugin_dir = _resolve_plugin_ctx(None, plugin_name)

        # Read plugin.py to extract basic info
        plugin_py = plugin_dir / "plugin.py"
        content = plugin_py.read_text() if plugin_py.exists() else ""

        console.print(f"[bold]Plugin:[/bold] {plugin_name}")
        console.print(f"  Location: [dim]{plugin_dir}[/dim]")

        # Try to extract description from docstring
        if '"""' in content:
            # Simple extraction of first docstring
            start = content.find('"""')
            end = content.find('"""', start + 3)
            if start != -1 and end != -1:
                description = content[start+3:end].strip()
                if description:
                    console.print(f"  Description: {description}")

        console.print(f"  Has plugin.py: {'✓' if plugin_py.exists() else '✗'}")
        console.print(f"  Has commands dir: {'✓' if (plugin_dir / 'commands').exists() else '✗'}")

        # Try to get commands
        try:
            commands = get_plugin_commands(plugin_name)
            if commands:
                console.print(f"  Commands: {', '.join(commands)}")
            else:
                console.print("  Commands: [dim]None (see plugin.py)[/dim]")
        except PluginError:
            console.print("  Commands: [red]Error loading plugin[/red]")

    except PluginError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)


def register(cli) -> None:  # type: ignore[no-untyped-def]
    cli.add_command(plugin_group)
