"""Human/quality gate helpers (moved out of cli.py — testable module, P2-8).

``utils.py``-era shared helpers that cli.py re-exports as
``_human_review_gate`` / ``_print_gate_report`` / ``_write_review_note``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from rich.console import Console

from brandly_cli import layout, quality_gate
from brandly_cli.io import now_iso

console = Console()


def human_review_gate(stage: str, label: str, default: bool = True) -> tuple[bool, str]:
    """Human-in-the-loop gate: ask up to 3 questions before continuing.

    Confirms the generated result matches what's expected. In
    non-interactive mode (EOF on stdin) the defaults are used, so piped
    runs auto-approve unless input is provided.

    Returns:
        (approved, note) — ``approved`` is False when the result was
        rejected, ``note`` carries the optional free-text issue.
    """
    try:
        q1 = click.confirm(
            f"[{stage} gate] Does {label} match what you expected?", default=default
        )
    except click.exceptions.Abort:
        q1 = default
    if q1:
        try:
            q2 = click.confirm(
                f"[{stage} gate] Approve {label} and continue to the next step?",
                default=True,
            )
        except click.exceptions.Abort:
            q2 = True
        return q2, ""
    try:
        note = click.prompt(
            f"[{stage} gate] What didn't match? (short note)",
            default="no note",
            show_default=False,
        )
    except click.exceptions.Abort:
        note = "no note (non-interactive)"
    return False, note


def write_review_note(
    root: Path, project_id: str, stage: str, note: str, extra: str = ""
) -> Path:
    """Save a human-gate review note under ``docs/tmp`` for the record."""
    docs_dir = layout.docs_dir(layout.project_dir(root, project_id), "tmp")
    docs_dir.mkdir(parents=True, exist_ok=True)
    ts = now_iso().replace(":", "-").replace(".", "_")
    note_path = docs_dir / f"review_{stage}_{ts}.md"
    note_path.write_text(
        f"# Human Gate Review: {stage}\n\n"
        f"**Status:** REJECTED\n"
        f"**Note:** {note}\n\n"
        f"{extra}\n",
        encoding="utf-8",
    )
    return note_path


def print_gate_report(result: Any) -> None:
    color = {
        quality_gate.PASS: "green",
        quality_gate.WARN: "yellow",
        quality_gate.FAIL: "red",
    }
    mark = {quality_gate.PASS: "✓", quality_gate.WARN: "⚠", quality_gate.FAIL: "✗"}
    console.print(
        f"[{color[result.status]}]{mark[result.status]} GATE {result.status.upper()}"
        f"[/] [{result.score}/100] {result.kind} → {result.element}"
    )
    if result.issues:
        console.print(f"[red]Failures ({len(result.issues)}):[/red]")
        for i in result.issues:
            console.print(f"  [red]✗ {i}[/red]")
    if result.warnings:
        console.print(f"[yellow]Warnings ({len(result.warnings)}):[/yellow]")
        for w in result.warnings:
            console.print(f"  [yellow]⚠ {w}[/yellow]")
    if result.ai:
        console.print(
            f"[dim]AI verdict: {result.ai.get('verdict', '?')} — "
            f"{result.ai.get('notes', '')}[/dim]"
        )
    console.print(
        "[dim]Report: .brandly/<project>/docs/tmp/ (gate_<kind>_<ts>.md)[/dim]"
    )
