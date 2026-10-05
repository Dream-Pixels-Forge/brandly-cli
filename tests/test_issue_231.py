"""Contract test: G8 - Continuation take: reconcile a short clip instead of shipping it short.

RED test for the continuation take increment. When a clip comes up short beyond
tolerance, brandly should spend a bounded extra request to finish the action
rather than shipping a truncated shot.

The credit is already spent whether or not we retry, so a continuation costs
latency, not credits. `split_long_shots` (`shot_runner.py:699`) already splits
over-long shots into 6s parts and attaches a `[CONTINUITY]` directive — the
vocabulary for a continuation take already exists.
"""

from __future__ import annotations

from pathlib import Path

from brandly_cli import shot_runner

REPO_ROOT = Path(__file__).resolve().parent.parent
SHOT_RUNNER = REPO_ROOT / "src" / "brandly_cli" / "shot_runner.py"


class TestContinuationTake:
    """Core continuation take contract."""

    def test_shot_record_has_continuation_fields(self):
        """Shot must have fields for continuation tracking."""
        shot = shot_runner.Shot(
            id="test-shot",
            act="test",
            style="cinematic",
            folder="scenes",
            prompt="test prompt",
            duration=6,
        )
        assert hasattr(shot, "continuation_of"), "Shot must have continuation_of field"
        assert hasattr(shot, "continuation_attempt"), "Shot must have continuation_attempt field"
        assert hasattr(shot, "continuation_parent"), "Shot must have continuation_parent field"

    def test_tolerance_constants(self):
        """Tolerance constants must exist for continuation logic."""
        assert hasattr(shot_runner, "DURATION_TOLERANCE_FACTOR")
        assert hasattr(shot_runner, "DURATION_TOLERANCE_MIN")
        assert hasattr(shot_runner, "RELIABLE_MAX_SHOT_DURATION")
        assert hasattr(shot_runner, "MAX_CONTINUATION_ATTEMPTS")
        assert shot_runner.MAX_CONTINUATION_ATTEMPTS == 2

    def test_needs_continuation(self):
        """Determine if a clip needs a continuation take."""
        # Within tolerance -> no continuation needed
        assert shot_runner.needs_continuation(requested_s=6, measured_s=5.5) is False
        assert shot_runner.needs_continuation(requested_s=6, measured_s=5.0) is False
        # Beyond tolerance -> continuation needed
        assert shot_runner.needs_continuation(requested_s=6, measured_s=4.5) is True
        assert shot_runner.needs_continuation(requested_s=12, measured_s=5.0) is True


