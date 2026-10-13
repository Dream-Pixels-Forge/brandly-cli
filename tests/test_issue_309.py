"""Issue #309: the reference gate must not fail its own multi-view grid output.

The reference-sheet prompts (``reference_prompts.py``) ask for "subtle thin
grey divider lines" between panels — by design. The vision judge may list
those by-design lines in its free-text ``issues[]``; ``GateResult.finalize()"
maps ANY issue to FAIL even when the model's own verdict is ``pass`` at
90/100. Because promotion to ``primary_reference`` happens only after a
passing gate (#275), the whole "reference is the first step" flow broke.

Ruling (option 3 of the issue + prompt guidance):
1. the vision user prompt tells the model divider lines on a multi-view
   reference board are by design, not an issue;
2. ``_apply_ai_verdict`` deterministically demotes divider/seam-only issues
   to WARNINGS when ``expect_matt_background`` is set — the gate can never
   FAIL a sheet for its own by-design grid.
"""

from __future__ import annotations

from brandly_cli import quality_gate


def _verdict(**overrides):  # type: ignore[no-untyped-def]
    base = {
        "quality_score": 90,
        "slop": 1,
        "distortion": 1,
        "drift": None,
        "matte_background": True,
        "identity_bleed": False,
        "identity_bleed_detail": "",
        "issues": [],
        "verdict": "pass",
        "notes": "clean multi-view sheet",
    }
    base.update(overrides)
    return base


def _apply(verdict, *, expect_matt=True):  # type: ignore[no-untyped-def]
    result = quality_gate.GateResult(element="sheet.png", kind="image")
    quality_gate._apply_ai_verdict(
        result,
        verdict,
        expect_matt_background=expect_matt,
        has_reference=False,
    )
    result.finalize()
    return result


class TestDividerIssuesDemoted:
    def test_by_design_divider_lines_do_not_fail_the_sheet(self) -> None:
        """The sheet's own panel dividers must never FAIL the gate (#309)."""
        verdict = _verdict(
            issues=[
                "Thin faint grid/seam lines visible on the background "
                "dividing the panels"
            ]
        )
        result = _apply(verdict)
        assert result.status != quality_gate.FAIL, (
            f"a by-design divider line must not fail the sheet: "
            f"{result.issues}"
        )
        assert any("dividing the panels" in w for w in result.warnings), (
            f"the divider observation should be demoted to a warning: "
            f"{result.warnings}"
        )

    def test_demotion_only_applies_when_matte_check_is_active(self) -> None:
        """Videos (no matte expectation) keep divider issues as issues."""
        verdict = _verdict(
            issues=["Seam lines dividing the panels"],
            matte_background=None,
        )
        result = _apply(verdict, expect_matt=False)
        assert result.status == quality_gate.FAIL

    def test_real_issues_still_fail_the_sheet(self) -> None:
        """Non-divider problems are untouched by the demotion (#309)."""
        verdict = _verdict(issues=["Product silhouette is warped and melted"])
        result = _apply(verdict)
        assert result.status == quality_gate.FAIL
        assert any("warped" in i for i in result.issues)

    def test_mixed_real_and_divider_keeps_the_real_issue(self) -> None:
        verdict = _verdict(
            issues=[
                "Seam lines dividing the panels",
                "Face is distorted beyond recognition",
            ]
        )
        result = _apply(verdict)
        assert result.status == quality_gate.FAIL
        assert any("distorted" in i for i in result.issues)
        assert not any("seam" in i.lower() for i in result.issues), (
            f"the seam observation must have been demoted: {result.issues}"
        )


class TestVisionPromptGuidance:
    def test_sheet_prompt_marks_dividers_as_by_design(self) -> None:
        """The judge is told up front that dividers are by design (#309)."""
        prompt = quality_gate._vision_user_prompt(
            description="earbuds product sheet",
            expect_matt_background=True,
            has_reference=False,
            kind="image",
        )
        assert "divider" in prompt.lower()
