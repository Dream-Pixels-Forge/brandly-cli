"""Command groups (structural split of cli.py).

Each module defines its commands and a ``register(cli)`` entry point;
``cli.py`` calls :func:`register` at the end of the module so imports
resolve after the shared helpers are defined.
"""

from __future__ import annotations

import click

from brandly_cli.cmd import (
    capabilities,
    gate,
    generation,
    post,
    production,
    providers,
    publish,
    tools,
)


def register(cli: click.Group) -> None:
    """Attach every command group to the root ``cli`` group."""
    for module in (
        production,
        generation,
        gate,
        post,
        providers,
        tools,
        capabilities,
        publish,
    ):
        module.register(cli)
