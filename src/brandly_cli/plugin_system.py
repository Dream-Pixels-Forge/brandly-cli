"""Plugin system for brandly-cli extensibility.

Discovers, loads, and manages plugins that extend brandly-cli functionality.
Plugins can register new CLI commands, hooks, and extensions.

Plugin structure:
    .brandly/plugins/
        plugin_name/
            __init__.py
            plugin.py
            commands/
                command1.py
                command2.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import click

from brandly_cli.cli import _get_root, console


class PluginError(Exception):
    """Base exception for plugin-related errors."""
    pass


class PluginNotFoundError(PluginError):
    """Raised when a plugin is not found."""
    pass


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""
    pass


def get_plugins_dir(root: str | Path | None = None) -> Path:
    """Get the plugins directory path."""
    # Handle the case where we're outside a CLI context (e.g., in tests)
    try:
        ctx = click.get_current_context(silent=True)
        if ctx is not None:
            root_dir = Path(root) if root else _get_root(ctx)
        else:
            # No CLI context available
            root_dir = Path(root) if root else Path.cwd()
    except Exception:
        # Fallback for testing contexts or other issues
        root_dir = Path(root) if root else Path.cwd()
    return root_dir / ".brandly" / "plugins"


def list_available_plugins(root: str | Path | None = None) -> list[str]:
    """List all available plugins in the plugins directory."""
    plugins_dir = get_plugins_dir(root)
    if not plugins_dir.exists():
        return []

    plugins = []
    for item in plugins_dir.iterdir():
        if item.is_dir() and (item / "plugin.py").exists():
            plugins.append(item.name)

    return sorted(plugins)


def load_plugin(plugin_name: str, root: str | Path | None = None) -> Any:
    """Load a plugin by name.

    Args:
        plugin_name: Name of the plugin to load
        root: Optional root directory

    Returns:
        The loaded plugin module

    Raises:
        PluginNotFoundError: If plugin directory doesn't exist
        PluginLoadError: If plugin fails to load
    """
    plugins_dir = get_plugins_dir(root)
    plugin_dir = plugins_dir / plugin_name

    if not plugin_dir.exists():
        raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")

    plugin_file = plugin_dir / "plugin.py"
    if not plugin_file.exists():
        raise PluginNotFoundError(f"Plugin '{plugin_name}' is missing plugin.py")

    # Store original sys.path to restore later
    original_path = list(sys.path)

    try:
        # Add the plugin directory to sys.path for imports
        plugin_path_str = str(plugin_dir)
        if plugin_path_str not in sys.path:
            sys.path.insert(0, plugin_path_str)

        # Import the plugin module
        plugin_module = importlib.import_module("plugin")

        # Call the plugin's register function if it exists
        if hasattr(plugin_module, "register"):
            plugin_module.register()

        return plugin_module

    except (ImportError, SyntaxError) as e:
        # Catch import-related errors
        raise PluginLoadError(f"Failed to load plugin '{plugin_name}': {e}") from e
    except Exception as e:
        # Re-raise as PluginLoadError with context
        raise PluginLoadError(f"Failed to load plugin '{plugin_name}': {e}") from e
    finally:
        # Restore original sys.path
        sys.path[:] = original_path


def load_all_plugins(root: str | Path | None = None) -> dict[str, Any]:
    """Load all available plugins.

    Returns:
        Dictionary mapping plugin names to loaded modules
    """
    plugins = {}
    plugin_names = list_available_plugins(root)

    for plugin_name in plugin_names:
        try:
            plugin_module = load_plugin(plugin_name, root)
            plugins[plugin_name] = plugin_module
            console.print(f"[green]✓ Loaded plugin:[/green] {plugin_name}")
        except PluginError:
            # Silently skip failed plugins in load_all_plugins
            pass
        except Exception:
            # Silently skip any other errors
            pass

    return plugins


def get_plugin_commands(plugin_name: str, root: str | Path | None = None) -> list[str]:
    """Get list of CLI commands provided by a plugin.

    Args:
        plugin_name: Name of the plugin
        root: Optional root directory

    Returns:
        List of command names provided by the plugin
    """
    try:
        plugin_module = load_plugin(plugin_name, root)
        if hasattr(plugin_module, "get_commands"):
            return plugin_module.get_commands()
        return []
    except PluginError:
        return []
    except Exception:
        return []


def create_plugin_structure(plugin_name: str, root: str | Path | None = None) -> Path:
    """Create the directory structure for a new plugin.

    Args:
        plugin_name: Name of the plugin to create
        root: Optional root directory

    Returns:
        Path to the created plugin directory
    """
    plugins_dir = get_plugins_dir(root)
    plugins_dir.mkdir(parents=True, exist_ok=True)

    plugin_dir = plugins_dir / plugin_name
    plugin_dir.mkdir(exist_ok=True)

    # Create basic plugin.py file
    plugin_py_content = f'''"""Plugin: {plugin_name}

A brandly-cli plugin that extends functionality.
"""

from __future__ import annotations

import click
from brandly_cli.cli import _get_root, console


def register() -> None:
    """Register plugin commands and hooks.

    This function is called when the plugin is loaded.
    """
    # Register CLI commands here
    # Example:
    # @click.group()
    # def {plugin_name}():
    #     """{plugin_name} commands."""
    #     pass
    #
    # # Add commands to the group
    # # from brandly_cli.cli import cli
    # # cli.add_command({plugin_name})
    pass


def get_commands() -> list[str]:
    """Get list of command names provided by this plugin.

    Returns:
        List of command names
    """
    return []


# Example command (commented out):
# @click.command()
# def hello():
#     """Say hello from the {plugin_name} plugin."""
#     console.print(f"[green]Hello from {plugin_name} plugin![/green]")


'''

    plugin_py_file = plugin_dir / "plugin.py"
    plugin_py_file.write_text(plugin_py_content)

    # Create commands directory
    commands_dir = plugin_dir / "commands"
    commands_dir.mkdir(exist_ok=True)

    # Create __init__.py files
    (plugin_dir / "__init__.py").write_text("")
    (commands_dir / "__init__.py").write_text("")

    return plugin_dir
