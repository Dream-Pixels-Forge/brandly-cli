"""Prevention layer: the governance docs must not drift from the code.

AGENTS.md §4 and the frozen design spec both carried stale claims about the
Brandly Studio screens:

* AGENTS.md said "Artboards 05/06 are empty in Paper — those screens are out of
  scope", while the design spec lists them as designed and
  ``tests/test_web_panels_wired.py`` pins ``ReviewQueuePanel`` and
  ``AgnesPanel`` as real, wired components.
* The design spec said the 05/06 code contract tests were "still pending" and
  the pass was "design-only" — both were true when written and false once the
  panels shipped.

An agent that trusts those notes would either refuse to touch implemented
panels or re-implement them over working code. These tests pin the facts.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_MD = REPO_ROOT / "AGENTS.md"
DESIGN_SPEC = REPO_ROOT / "dev-notes" / "DESIGN-STUDIO-SHELL.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestDesignSourceOfTruthDoc:
    def test_agents_md_does_not_declare_implemented_screens_out_of_scope(self) -> None:
        """AGENTS.md must not call the designed 05/06 screens empty/out of scope."""
        content = _read(AGENTS_MD)
        assert "Artboards **05/06 are empty**" not in content, (
            "AGENTS.md §4 still declares artboards 05/06 empty, but they are "
            "designed (DESIGN-STUDIO-SHELL.md §7) and implemented "
            "(tests/test_web_panels_wired.py pins ReviewQueuePanel/AgnesPanel)"
        )

    def test_agents_md_artboard_range_covers_05_to_07(self) -> None:
        """AGENTS.md must point at the full artboard range 01-07."""
        content = _read(AGENTS_MD)
        assert re.search(r"artboards?\s+`?01`?.\s*.?`?07`?", content), (
            "AGENTS.md §4 must cite artboards 01-07 (the design spec §7 lists "
            "01,02,03,04,05,06,07 — the Preview Player split added 07)"
        )

    def test_design_spec_does_not_claim_panel_code_is_pending(self) -> None:
        """The spec must not still say the 05/06 code contract is outstanding."""
        content = _read(DESIGN_SPEC)
        assert "still pending" not in content, (
            "DESIGN-STUDIO-SHELL.md still says the 05/06 SPA contract tests are "
            "pending — they shipped (tests/test_web_agnes_panel.py, "
            "tests/test_web_panels_wired.py)"
        )
