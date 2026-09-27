"""Issue #116: surface quality-gate scores in produce; --gate-threshold.

Gate scores previously printed once and vanished - non-interactive runs
auto-approve, so a 5/100 take sailed into the film. Now:
- every shot's OK line carries its gate score (gate=N/100)
- --gate-threshold N prints an end-of-run block listing every below-threshold
  take with its --only re-run command (flag mode: clips are kept, exit code
  unchanged)
"""

from __future__ import annotations

from brandly_cli.cli import cli
from brandly_cli.cmd.generation import _gate_note, _print_gate_threshold_summary


def test_gate_note_formats_score() -> None:
    assert _gate_note(42) == "gate=42/100"
    assert _gate_note(0) == "gate=0/100"
    assert _gate_note(None) == ""


def test_threshold_summary_lists_below_threshold_only() -> None:
    scores = {"s1": 92, "s2": 5, "s3": 59, "s4": 60}
    below = _print_gate_threshold_summary(scores, threshold=60)
    assert below == ["s2", "s3"]  # 60 itself passes; 59 and 5 flagged


def test_threshold_summary_noop_without_below() -> None:
    assert _print_gate_threshold_summary({"s1": 100}, threshold=60) == []


def test_produce_has_gate_threshold_option() -> None:
    cmd = cli.get_command(None, "produce")
    assert any(p.name == "gate_threshold" for p in cmd.params)
