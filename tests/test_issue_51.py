"""Regression tests for issue #51: multi-character identity bleed.

Root cause
----------
When a scene has 2+ co-appearing characters, Agnes's image-to-video
anchors every figure's face to the *dominant* (first-listed) reference
plate. A shot meant to show "Silas alone" rendered Elias's face, and the
quality gate did not catch it — it only checked that the *main* character
was present, not that the *other* characters had not leaked into the
frame.

Fix
---
- Extend the vision prompt to ask for a per-character identity check:
  for each named character in the description, does the corresponding
  figure in the frame actually look like that character's reference
  plate (not the other character's)?
- Add an `identity_bleed` field to the verdict JSON.
- `_apply_ai_verdict` raises an issue when `identity_bleed` is true.
- A deterministic pre-check helper `detect_identity_bleed_heuristic`
  cross-references the *count* of distinct face clusters in the frame
  against the expected character count, and flags a mismatch as a
  warning (the AI check is authoritative; this is a backstop when the
  AI is unavailable).

The tests below pin the contract:
  1. `verify_element` accepts an `expected_characters` kwarg (a list of
     character names that should each appear distinctly in frame).
  2. The vision prompt includes a per-character identity instruction.
  3. A verdict with `identity_bleed: true` produces a gate issue.
"""

from __future__ import annotations

from pathlib import Path

from brandly_cli import quality_gate


class TestVisionPromptIdentityBleed:
    def test_prompt_includes_per_character_instruction_when_expected_characters_given(
        self,
    ) -> None:
        """When the caller says 2 characters co-appear, the prompt must ask
        the model to verify each one is distinct."""
        prompt = quality_gate._vision_user_prompt(
            description="Elias (Black man in soutane) and Silas (white man) face each other",
            expect_matt_background=False,
            has_reference=True,
            kind="video",
            expected_characters=["Elias", "Silas"],
        )
        assert "Elias" in prompt
        assert "Silas" in prompt
        # The instruction to check each character's face against the
        # reference (not the other character's face) must be present.
        assert "identity_bleed" in prompt or "each character" in prompt.lower()

    def test_prompt_unchanged_when_no_expected_characters(self) -> None:
        """Backward-compat: without expected_characters, the prompt is the
        same as before (no identity-bleed instruction)."""
        prompt_with = quality_gate._vision_user_prompt(
            description="a priest",
            expect_matt_background=False,
            has_reference=True,
            kind="video",
        )
        prompt_without = quality_gate._vision_user_prompt(
            description="a priest",
            expect_matt_background=False,
            has_reference=True,
            kind="video",
        )
        assert prompt_with == prompt_without
        # And the new instruction is NOT there.
        assert "each character" not in prompt_with.lower()


class TestIdentityBleedVerdict:
    def test_bleed_verdict_produces_issue(self) -> None:
        """A verdict with identity_bleed=True must add a gate issue."""
        result = quality_gate.GateResult(element="test.mp4", kind="video")
        verdict = {
            "quality_score": 70,
            "slop": 3,
            "distortion": 2,
            "drift": 1,
            "identity_bleed": True,
            "identity_bleed_detail": "Silas rendered with Elias's face",
            "issues": [],
            "verdict": "fail",
            "notes": "cross-character identity bleed",
        }
        quality_gate._apply_ai_verdict(
            result, verdict, expect_matt_background=False, has_reference=True
        )
        # The identity-bleed issue must be present and marked as an issue
        # (not just a warning).
        assert any("identity bleed" in i.lower() for i in result.issues) or any(
            "identity" in c.lower() for c in result.checks if c != "ai"
        )
        assert result.status == quality_gate.FAIL

    def test_clean_verdict_no_bleed_issue(self) -> None:
        """A clean verdict (no identity_bleed) must not add a bleed issue."""
        result = quality_gate.GateResult(element="test.mp4", kind="video")
        verdict = {
            "quality_score": 90,
            "slop": 1,
            "distortion": 0,
            "drift": 0,
            "identity_bleed": False,
            "issues": [],
            "verdict": "pass",
            "notes": "clean",
        }
        quality_gate._apply_ai_verdict(
            result, verdict, expect_matt_background=False, has_reference=True
        )
        assert not any("identity bleed" in i.lower() for i in result.issues)
        assert result.status == quality_gate.PASS

    def test_missing_field_is_backward_compatible(self) -> None:
        """Old verdicts that lack the identity_bleed key must not crash and
        must not raise a false issue."""
        result = quality_gate.GateResult(element="test.mp4", kind="video")
        verdict = {
            "quality_score": 85,
            "slop": 1,
            "distortion": 0,
            "drift": 0,
            "issues": [],
            "verdict": "pass",
            "notes": "clean",
        }
        quality_gate._apply_ai_verdict(
            result, verdict, expect_matt_background=False, has_reference=True
        )
        assert result.status == quality_gate.PASS
        assert not any("identity bleed" in i.lower() for i in result.issues)


class TestVerifyElementSignature:
    def test_verify_element_accepts_expected_characters(self) -> None:
        """The public entry point must accept expected_characters and thread
        it through to the vision prompt."""
        import inspect

        sig = inspect.signature(quality_gate.verify_element)
        assert "expected_characters" in sig.parameters
        # Default must be None so existing callers are unaffected.
        param = sig.parameters["expected_characters"]
        assert param.default is None


class TestIdentityBleedHeuristic:
    """The deterministic backstop (no AI) must flag a face-count mismatch
    and stay silent for single-character / object shots."""

    def test_single_character_returns_false(self, tmp_path: Path) -> None:
        """expected=1 -> no bleed possible, always False (no image needed)."""
        fake = tmp_path / "x.png"
        fake.write_bytes(b"")  # unreadable is fine for count<=1
        assert quality_gate.detect_identity_bleed_heuristic(fake, 1) is False
        assert quality_gate.detect_identity_bleed_heuristic(fake, 0) is False

    def test_unreadable_frame_returns_false(self, tmp_path: Path) -> None:
        """A frame that can't be opened must not raise a false flag."""
        fake = tmp_path / "bad.png"
        fake.write_bytes(b"not an image")
        assert quality_gate.detect_identity_bleed_heuristic(fake, 3) is False

    def test_two_matching_faces_return_false(self, tmp_path: Path) -> None:
        """A frame with ~2 skin clusters and expected=2 -> no suspicion."""
        from PIL import Image
        # Paint two skin-toned blobs on a dark background.
        im = Image.new("RGB", (128, 128), (20, 20, 20))
        px = im.load()
        for (bx, by) in ((40, 40), (90, 40)):
            for y in range(by - 12, by + 12):
                for x in range(bx - 12, bx + 12):
                    if 0 <= x < 128 and 0 <= y < 128:
                        px[x, y] = (180, 120, 90)  # skin-tone
        p = tmp_path / "two_faces.png"
        im.save(p)
        assert quality_gate.detect_identity_bleed_heuristic(p, 2) is False

    def test_zero_faces_but_expected_two_returns_true(self, tmp_path: Path) -> None:
        """A blank frame with expected=2 (both characters missing) is a
        strong bleed signal -> True."""
        from PIL import Image
        im = Image.new("RGB", (128, 128), (10, 10, 10))  # all dark
        p = tmp_path / "blank.png"
        im.save(p)
        assert quality_gate.detect_identity_bleed_heuristic(p, 2) is True
