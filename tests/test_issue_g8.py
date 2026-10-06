"""Contract test: G8 - Continuation take - reconcile a short clip instead of shipping it short.

RED test for the continuation take increment. When a clip comes up short beyond
tolerance, spend a bounded extra request to finish the action rather than
shipping a truncated shot.

This suite pins:
1. Tiered reconcile: within tolerance -> accept; beyond tolerance -> continuation
   take for the shortfall only, then head+tail stitch
2. Bounded: max N continuations per shot (default 2), then mark SHORT and
   record the real duration
3. Continuation prompt carries the shot identity anchor so the seam is not a
   visible jump cut
4. Every continuation attempt is recorded in the shot record
"""

from __future__ import annotations

from pathlib import Path

from brandly_cli import shot_runner

REPO_ROOT = Path(__file__).resolve().parent.parent
SHOT_RUNNER = REPO_ROOT / "src" / "brandly_cli" / "shot_runner.py"


class TestContinuationTake:
    """Core continuation take contract."""

    def test_continuation_constants_exist(self):
        """Continuation constants must exist."""
        assert hasattr(shot_runner, "DEFAULT_MAX_CONTINUATIONS"), "DEFAULT_MAX_CONTINUATIONS must exist"
        assert shot_runner.DEFAULT_MAX_CONTINUATIONS == 2
        assert hasattr(shot_runner, "CONTINUATION_STATUS"), "CONTINUATION_STATUS must exist"

    def test_shot_model_has_continuation_fields(self):
        """Shot model must have continuation tracking fields."""
        shot = shot_runner.Shot(
            id="test-shot",
            act="test",
            style="cinematic",
            folder="scenes",
            prompt="test prompt",
            duration=6,
        )
        assert hasattr(shot, "continuation_attempts"), "Shot must have continuation_attempts field"
        assert hasattr(shot, "continuation_parent_id"), "Shot must have continuation_parent_id field"
        assert hasattr(shot, "is_continuation"), "Shot must have is_continuation field"

    def test_continuation_status_value(self):
        """CONTINUATION status must be 'continuation'."""
        assert shot_runner.CONTINUATION_STATUS == "continuation"

    def test_should_trigger_continuation(self):
        """Determine if a continuation is needed based on measured vs requested."""
        assert shot_runner.should_trigger_continuation(requested=6, measured=5.5) is False
        assert shot_runner.should_trigger_continuation(requested=10, measured=9.5) is False

        assert shot_runner.should_trigger_continuation(requested=6, measured=4.5) is True
        assert shot_runner.should_trigger_continuation(requested=10, measured=8.5) is True
        assert shot_runner.should_trigger_continuation(requested=5, measured=3.5) is True

    def test_continuation_shortfall_calculation(self):
        """Calculate the shortfall duration for the continuation take."""
        assert shot_runner.continuation_shortfall(requested=6, measured=4.5) == 1.5
        assert shot_runner.continuation_shortfall(requested=10, measured=7.0) == 3.0
        assert shot_runner.continuation_shortfall(requested=5, measured=3.0) == 2.0

        assert shot_runner.continuation_shortfall(requested=6, measured=5.5) == 0
        assert shot_runner.continuation_shortfall(requested=10, measured=9.5) == 0

    def test_max_continuations_enforced(self):
        """Max continuations per shot must be enforced."""
        assert shot_runner.max_continuations_reached(attempts=0, max_continuations=2) is False
        assert shot_runner.max_continuations_reached(attempts=1, max_continuations=2) is False
        assert shot_runner.max_continuations_reached(attempts=2, max_continuations=2) is True
        assert shot_runner.max_continuations_reached(attempts=3, max_continuations=2) is True

    def test_continuation_prompt_preserves_identity_anchor(self):
        """Continuation prompt must carry the shot identity anchor for seamless stitch."""
        shot = shot_runner.Shot(
            id="test-shot",
            act="test",
            style="cinematic",
            folder="scenes",
            prompt="test prompt with identity anchor",
            duration=6,
            character="hero character",
        )
        continuation_prompt = shot_runner.build_continuation_prompt(shot, shortfall_s=1.5)

        assert "hero character" in continuation_prompt
        assert "continuation" in continuation_prompt.lower() or "CONTINUITY" in continuation_prompt
        assert "1.5" in continuation_prompt or "1.5s" in continuation_prompt


class TestContinuationRecording:
    """Continuation attempts must be recorded in the shot record."""

    def test_shot_record_includes_continuation_history(self):
        """Shot record should track all continuation attempts."""
        shot = shot_runner.Shot(
            id="test-shot",
            act="test",
            style="cinematic",
            folder="scenes",
            prompt="test prompt",
            duration=6,
        )
        assert hasattr(shot, "continuation_history"), "Shot must have continuation_history field"

    def test_cost_tracker_attributes_continuation(self):
        """Cost tracker must attribute the extra continuation request."""
        from brandly_cli import cost_tracker

        assert hasattr(cost_tracker.CostTracker, "record_continuation"), \
            "CostTracker must have record_continuation method"


# Constants that don't exist yet - RED
assert hasattr(shot_runner, "DEFAULT_MAX_CONTINUATIONS"), "DEFAULT_MAX_CONTINUATIONS must exist"
assert hasattr(shot_runner, "CONTINUATION_STATUS"), "CONTINUATION_STATUS must exist"
assert hasattr(shot_runner, "should_trigger_continuation"), "should_trigger_continuation function must exist"
assert hasattr(shot_runner, "continuation_shortfall"), "continuation_shortfall function must exist"
assert hasattr(shot_runner, "max_continuations_reached"), "max_continuations_reached function must exist"
assert hasattr(shot_runner, "build_continuation_prompt"), "build_continuation_prompt function must exist"
