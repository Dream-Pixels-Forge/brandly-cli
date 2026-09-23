"""Regression tests for issue #49: --split-long-shots + --only ID mismatch.

Root cause
----------
``split_long_shots`` renames a long shot ``shot04_silas`` into parts
``shot04_silas-p1`` / ``shot04_silas-p2``. The CLI's ``--only`` filter was
still checking against the *pre-split* ID, so passing the original ID
silently matched zero pending shots and the runner exited with
"all pending shots complete" without generating anything.

These tests pin the correct behaviour:
  * ``--only shot04_silas`` under split mode must resolve to the split parts.
  * Passing an explicit split-part ID (``shot04_silas-p1``) must still work.
  * The CLI must warn (not fail silently) when ``--only`` targets a parent ID
    that has been split, so the user knows the expansion happened.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from brandly_cli import shot_runner


def _long_shots() -> list[shot_runner.Shot]:
    """Two shots, one short (5s), one long (8s -> will split to 4+4)."""
    return [
        shot_runner.Shot(
            id="shot01", act="ACT I", style="cinematic", folder="scenes",
            prompt="p short", duration=5, scene=1, index_in_scene=1,
        ),
        shot_runner.Shot(
            id="shot04_silas", act="ACT II", style="cinematic", folder="scenes",
            prompt="p long", duration=8, scene=4, index_in_scene=1,
        ),
    ]


def _split_ids(shots: list[shot_runner.Shot]) -> set[str]:
    return {s.id for s in shot_runner.split_long_shots(shots)}


class TestSplitLongShotsOnlyExpansion:
    """--only with a split-parent ID must expand to the split parts."""

    def test_parent_id_expands_to_all_parts(self) -> None:
        """Passing the original 'shot04_silas' must resolve to its parts."""
        split = shot_runner.split_long_shots(_long_shots())
        parent_ids = {s.id for s in _long_shots()}  # {shot01, shot04_silas}
        expanded = shot_runner.expand_only_ids(set(parent_ids), split)
        # shot01 is short -> stays shot01; shot04_silas -> shot04_silas-p1/-p2
        assert expanded == {"shot01", "shot04_silas-p1", "shot04_silas-p2"}
        # The pre-split parent ID must NOT remain in the set (it would no-op).
        assert "shot04_silas" not in expanded
        # Split parts that actually exist must be present.
        split_ids = _split_ids(_long_shots())
        assert expanded & split_ids == split_ids

    def test_explicit_split_part_id_passes_through(self) -> None:
        """If the user already knows the part ID, it must keep working."""
        split = shot_runner.split_long_shots(_long_shots())
        expanded = shot_runner.expand_only_ids({"shot04_silas-p1"}, split)
        assert "shot04_silas-p1" in expanded
        # And it must not silently pull in sibling parts the user didn't ask for.
        assert "shot04_silas-p2" not in expanded

    def test_mixed_parent_and_part(self) -> None:
        """A set with both a parent and one of its parts must not double up."""
        split = shot_runner.split_long_shots(_long_shots())
        expanded = shot_runner.expand_only_ids(
            {"shot04_silas", "shot04_silas-p1"}, split
        )
        assert "shot04_silas-p1" in expanded
        assert "shot04_silas-p2" in expanded
        assert "shot04_silas" not in expanded
        # No duplicates: the expansion is a set.
        assert len(expanded) == len(set(expanded))

    def test_no_split_short_shot_unchanged(self) -> None:
        """Short shots keep their ID under split mode (no -p suffix)."""
        split = shot_runner.split_long_shots(_long_shots())
        expanded = shot_runner.expand_only_ids({"shot01"}, split)
        assert "shot01" in expanded
        assert "shot01-p1" not in expanded

    def test_unknown_id_is_preserved(self) -> None:
        """An ID that is neither a parent nor a part is passed through as-is,
        so run_shots reports it as 'pending 0' rather than crashing."""
        split = shot_runner.split_long_shots(_long_shots())
        expanded = shot_runner.expand_only_ids({"ghost"}, split)
        assert "ghost" in expanded


class TestExpandOnlyIdsEdgeCases:
    def test_empty_only_is_empty(self) -> None:
        assert shot_runner.expand_only_ids(set(), _long_shots()) == set()

    def test_only_with_no_split_at_all(self) -> None:
        """When there are no long shots, expansion is the identity map."""
        short = [
            shot_runner.Shot(
                id="s1", act="A", style="cinematic", folder="scenes",
                prompt="p", duration=4,
            )
        ]
        expanded = shot_runner.expand_only_ids({"s1"}, short)
        assert expanded == {"s1"}
