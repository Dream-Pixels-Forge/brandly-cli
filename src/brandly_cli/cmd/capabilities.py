"""G5: `brandly capabilities` — the capability matrix, human- and machine-readable.

Renders the single source list from :mod:`brandly_cli.capabilities`; the
README "What is Brandly?" section is checked against the same list by
``tests/test_capabilities.py``.
"""
from __future__ import annotations

import json

import click
from rich.table import Table

from brandly_cli.capabilities import (
    STATUSES,
    capabilities_by_status,
    capability_matrix,
)
from brandly_cli.cli import console

_STATUS_STYLE = {
    "supported": "green",
    "partial": "yellow",
    "planned": "cyan",
    "absent": "red",
}


@click.command()
@click.option("--json", "json_out", is_flag=True, help="Emit machine-readable JSON")
def capabilities(json_out: bool) -> None:
    """What brandly can do today, per persona (G5 capability matrix)."""
    if json_out:
        print(json.dumps(capability_matrix(), indent=2, ensure_ascii=False))
        return

    rows = capabilities_by_status()
    for status in STATUSES:
        caps = rows[status]
        if not caps:
            continue
        table = Table(title=f"{status.upper()} ({len(caps)}")
        table.add_column("Capability", style="bold")
        table.add_column("Persona")
        table.add_column("Command / where")
        table.add_column("Note")
        for cap in caps:
            table.add_row(
                cap["id"],
                cap["persona"],
                cap.get("command", "—"),
                cap["note"],
            )
        console.print(f"[{_STATUS_STYLE[status]}]{status}[/]")
        console.print(table)
    console.print(
        "[dim]Gaps and planned work: dev-notes/AUDIT-AGENTIC-PIPELINE.md "
        "(single source of truth for open gaps).[/dim]"
    )


def register(cli) -> None:  # type: ignore[no-untyped-def]
    cli.add_command(capabilities)
