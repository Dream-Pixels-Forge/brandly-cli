"""Issue #113: duplicate shot ids silently corrupt progress-file resumability.

Progress logs (storyboard_progress.txt / produce_progress.txt) match by bare
shot id, so two shots sharing an id alias each other: the first OK line marks
every same-id shot done and FAIL lines become ambiguous. flatten_shots must
fail closed on id collisions instead of returning an aliased list.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from brandly_cli import shot_runner


def _structured(colliding: bool) -> dict:
    second_id = "shot01" if colliding else "scene2-shot01"
    return {
        "acts": {
            "scene1": {
                "prefix": "p1 ",
                "shots": [{"id": "shot01", "prompt": "a", "duration": 4}],
            },
            "scene2": {
                "prefix": "p2 ",
                "shots": [{"id": second_id, "prompt": "b", "duration": 4}],
            },
        }
    }


def test_structured_duplicate_ids_raise(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as exc:
        shot_runner.flatten_shots(_structured(colliding=True), tmp_path / "images")
    msg = str(exc.value)
    assert "shot01" in msg
    assert "duplicate" in msg.lower()


def test_flat_duplicate_ids_raise(tmp_path: Path) -> None:
    data = [
        {"id": "shot01", "prompt": "a", "duration": 4},
        {"id": "shot01", "prompt": "b", "duration": 4},
    ]
    with pytest.raises(ValueError) as exc:
        shot_runner.flatten_shots(data, tmp_path / "images")
    assert "shot01" in str(exc.value)


def test_unique_ids_pass(tmp_path: Path) -> None:
    shots = shot_runner.flatten_shots(_structured(colliding=False), tmp_path / "images")
    assert [s.id for s in shots] == ["shot01", "scene2-shot01"]


def test_error_suggests_act_qualified_ids(tmp_path: Path) -> None:
    with pytest.raises(ValueError) as exc:
        shot_runner.flatten_shots(_structured(colliding=True), tmp_path / "images")
    assert "<act>" in str(exc.value)


def test_completed_ids_ignores_unknown_and_duplicates(tmp_path: Path) -> None:
    """completed_ids stays idempotent when the known set itself has duplicates."""
    log = shot_runner.ProgressLog(tmp_path / "progress.txt")
    log.record("shot01", "OK", 0)
    done = log.completed_ids(["shot01", "shot01", "shot02"])
    assert done == {"shot01"}
