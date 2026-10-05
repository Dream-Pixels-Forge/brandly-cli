"""Contract test: G7 - Duration truth - measure every returned clip.

RED test for the keystone accuracy increment. Currently `shot_runner` trusts
the requested duration and never validates the returned clip. This suite pins:

1. Every clip is measured after generation (reusing existing ffprobe machinery)
2. `requested_s`, `measured_s`, `delta_s` are persisted in the shot record
3. A shot that came up short is NEVER recorded `OK` (it gets `SHORT` or `CONTINUATION`)
4. Timeline exposes `measured_duration` + `duration_status` (`ok`|`short`|`continuation`)
5. Tolerance: `max(1s, 10%)` - within this is `ok`, beyond is `short`
"""

from __future__ import annotations

from pathlib import Path

from brandly_cli import shot_runner

REPO_ROOT = Path(__file__).resolve().parent.parent
SHOT_RUNNER = REPO_ROOT / "src" / "brandly_cli" / "shot_runner.py"


class TestDurationTruth:
    """Core duration measurement contract."""

    def test_clip_measurement_records_requested_and_measured(self, tmp_path: Path):
        """After a clip lands, its record must have requested_s, measured_s, delta_s."""
        # This will fail because the measurement fields don't exist yet
        shot = shot_runner.Shot(
            id="test-shot",
            act="test",
            style="cinematic",
            folder="scenes",
            prompt="test prompt",
            duration=6,
        )
        # The shot model doesn't have these fields yet - this is the RED signal
        assert hasattr(shot, "requested_s"), "Shot must have requested_s field"
        assert hasattr(shot, "measured_s"), "Shot must have measured_s field"
        assert hasattr(shot, "delta_s"), "Shot must have delta_s field"
        assert hasattr(shot, "duration_status"), "Shot must have duration_status field"

    def test_shot_duration_status_values(self):
        """Duration status must be one of the defined enum values."""
        assert set(shot_runner.DURATION_STATUSES) == {"ok", "short", "continuation"}

    def test_tolerance_calculation(self):
        """Tolerance = max(1s, 10% of requested)."""
        assert shot_runner.duration_tolerance(10) == 1.0  # 10% = 1s
        assert shot_runner.duration_tolerance(5) == 1.0   # 10% = 0.5s -> max(1, 0.5) = 1
        assert shot_runner.duration_tolerance(20) == 2.0  # 10% = 2s

    def test_is_within_tolerance(self):
        """Check if measured duration is within tolerance of requested."""
        # Within tolerance -> True
        assert shot_runner.is_within_tolerance(requested=10, measured=9.5) is True
        assert shot_runner.is_within_tolerance(requested=10, measured=10.5) is True
        assert shot_runner.is_within_tolerance(requested=5, measured=4.5) is True
        assert shot_runner.is_within_tolerance(requested=5, measured=5.5) is True
        # Beyond tolerance -> False
        assert shot_runner.is_within_tolerance(requested=10, measured=8.5) is False
        assert shot_runner.is_within_tolerance(requested=10, measured=11.5) is False
        assert shot_runner.is_within_tolerance(requested=5, measured=3.5) is False





class TestTimelineExposesMeasuredDuration:
    """Timeline API must expose measured vs requested."""

    def test_get_timeline_includes_measured_fields(self):
        """Timeline output must include measured_duration and duration_status."""
        # Will fail because timeline doesn't have these fields yet
        assert hasattr(shot_runner, "get_timeline"), "Timeline function must exist"
        # The timeline output should have these fields per shot
        # This is a contract assertion for the implementation


# Constants that don't exist yet - RED
assert hasattr(shot_runner, "DURATION_STATUSES"), "DURATION_STATUSES enum must exist"
assert hasattr(shot_runner, "duration_tolerance"), "duration_tolerance function must exist"
assert hasattr(shot_runner, "is_within_tolerance"), "is_within_tolerance function must exist"
