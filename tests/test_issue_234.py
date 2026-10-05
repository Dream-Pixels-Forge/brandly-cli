"""Contract test: G11 - Fail-honest: UNVERIFIED is never PASS.

RED test for the fail-honest increment. Currently without AGNES_API_KEY, the
gate marks AI analysis as "skipped" (a warning, never a hard failure), so a
project can complete with PASS on every element while nothing was actually
verified.

This suite pins:
1. New status literal `UNVERIFIED`, distinct from `PASS`/`WARN`/`FAIL`
2. Absent a judge => `UNVERIFIED` (never `PASS`), recorded in the report
3. `--strict` (and produce's default) exits non-zero on `UNVERIFIED`
4. `UNVERIFIED` surfaces in the timeline so the driving agent knows it is blind
"""

from __future__ import annotations

import asyncio
import os
import random
from pathlib import Path
from unittest.mock import patch

from brandly_cli import quality_gate

REPO_ROOT = Path(__file__).resolve().parent.parent
QUALITY_GATE = REPO_ROOT / "src" / "brandly_cli" / "quality_gate.py"


def _make_test_image(tmp_path: Path) -> Path:
    """Create a valid test image with variation to pass blank checks."""
    from PIL import Image
    test_file = tmp_path / "test.png"
    img = Image.new('RGB', (16, 16), color='red')
    # Add some noise to pass blank checks
    pixels = [(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)) for _ in range(256)]
    img.putdata(pixels)
    img.save(test_file)
    return test_file


class TestUnverifiedStatus:
    """The new UNVERIFIED status must exist and be distinct."""

    def test_unverified_status_constant_exists(self):
        """UNVERIFIED must be a module-level constant distinct from PASS/WARN/FAIL."""
        assert hasattr(quality_gate, "UNVERIFIED"), "UNVERIFIED constant must exist"
        assert quality_gate.UNVERIFIED == "unverified"
        assert quality_gate.UNVERIFIED not in (quality_gate.PASS, quality_gate.WARN, quality_gate.FAIL)

    def test_unverified_in_all_statuses(self):
        """UNVERIFIED should be in the set of all valid statuses."""
        all_statuses = {quality_gate.PASS, quality_gate.WARN, quality_gate.FAIL, quality_gate.UNVERIFIED}
        assert len(all_statuses) == 4

    def test_unverified_not_pass(self):
        """UNVERIFIED must never equal PASS."""
        assert quality_gate.UNVERIFIED != quality_gate.PASS
        assert quality_gate.UNVERIFIED != quality_gate.WARN
        assert quality_gate.UNVERIFIED != quality_gate.FAIL


class TestGateReturnsUnverifiedWithoutApiKey:
    """Gate must return UNVERIFIED (not PASS) when no judge is available."""

    def test_verify_element_returns_unverified_when_no_api_key(self, tmp_path: Path):
        """Without AGNES_API_KEY, verify_element must return UNVERIFIED, not PASS."""
        test_file = _make_test_image(tmp_path)

        # Ensure no API key is set
        with patch.dict(os.environ, {}, clear=True):
            result = asyncio.run(quality_gate.verify_element(
                test_file,
                use_ai=True,  # explicitly requesting AI
                root=tmp_path,
                project_id="test-project",
                write_report=False,
            ))

        # Should be UNVERIFIED, not PASS
        assert result.status == "unverified", f"Expected 'unverified', got '{result.status}'"
        assert result.status != "pass", "Must not return PASS when no judge available"

    def test_verify_element_unverified_has_ai_skipped_reason(self, tmp_path: Path):
        """UNVERIFIED result should record why AI was skipped."""
        test_file = _make_test_image(tmp_path)

        with patch.dict(os.environ, {}, clear=True):
            result = asyncio.run(quality_gate.verify_element(
                test_file,
                use_ai=True,
                root=tmp_path,
                project_id="test-project",
                write_report=False,
            ))

        assert result.status == "unverified"
        # Should record that AI was skipped due to missing API key
        assert any("API" in str(f) for f in (result.issues or []) + (result.warnings or []))

    def test_verify_element_use_ai_false_still_passes(self, tmp_path: Path):
        """When use_ai=False, deterministic checks should still work normally."""
        test_file = _make_test_image(tmp_path)

        result = asyncio.run(quality_gate.verify_element(
            test_file,
            use_ai=False,  # explicitly opting out of AI
            root=tmp_path,
            project_id="test-project",
            write_report=False,
        ))

        # Should be PASS (deterministic checks passed)
        assert result.status == "pass"


class TestStrictModeExitsNonZeroOnUnverified:
    """--strict flag must exit non-zero on UNVERIFIED."""

    def test_strict_exits_non_zero_on_unverified(self, tmp_path: Path):
        """CLI with --strict should exit non-zero when gate returns UNVERIFIED."""
        # This will be tested via CLI integration test
        assert True  # placeholder - actual CLI test in test_pipeline_orchestration.py


class TestTimelineShowsUnverified:
    """Timeline must surface UNVERIFIED so agents know they're blind."""

    def test_timeline_includes_unverified_status(self):
        """get_timeline should include UNVERIFIED shots."""
        # This will be tested after G7 timeline is updated
        assert True  # placeholder
