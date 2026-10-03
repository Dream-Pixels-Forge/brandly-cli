"""Contract tests for the Agnes AI Synthesizer panel (design §6, screen 06).

RED test: ``Shell.tsx`` mapped ``agnes_ai`` to the ``ShotListPanel`` stand-in,
so the frozen design's dedicated generation console had no real component.
These tests pin the wiring + data-honesty contract at the source level (no JS
test runner in CI yet — see #61).

Design §6 screen 06: generation console (prompt box, style-preset chips,
aspect/fit/seed params, credit-budget bar, Synthesize/Queue actions) + 2×2
results grid (one selected variant) + run-summary footer.

Data-honesty rule (DESIGN-STUDIO-SHELL.md §5): the panel must render from real
store/clip data and must not fabricate telemetry (no simulated values, no mock
control-strip object, no invented GPU/cost metrics).
"""

from __future__ import annotations

import re
from pathlib import Path

WEB_SRC = Path(__file__).resolve().parent.parent / "web" / "src"
PANEL = "components/panels/AgnesPanel.tsx"


def _read(name: str) -> str:
    return (WEB_SRC / name).read_text(encoding="utf-8")


class TestAgnesPanelWiring:
    def test_agnes_panel_file_exists(self) -> None:
        assert (WEB_SRC / PANEL).exists(), "AgnesPanel.tsx missing (screen 06 has no real component)"

    def test_shell_maps_agnes_ai_to_real_panel(self) -> None:
        shell = _read("Shell.tsx")
        assert re.search(r"agnes_ai:\s*\(\)\s*=>\s*<AgnesPanel", shell), (
            "Shell.tsx must map agnes_ai to <AgnesPanel />"
        )
        assert not re.search(r"agnes_ai:\s*\(\)\s*=>\s*<ShotListPanel", shell), (
            "agnes_ai must not reuse the ShotListPanel stand-in"
        )

    def test_agnes_panel_imported_in_shell(self) -> None:
        assert "AgnesPanel" in _read("Shell.tsx"), "Shell.tsx does not import AgnesPanel"


class TestAgnesPanelDataHonesty:
    def test_reads_real_store(self) -> None:
        panel = _read(PANEL)
        assert "useAppStore" in panel, "AgnesPanel must read the app store"
        assert any(k in panel for k in ("timeline", "selectedClipId", "activeProject")), (
            "AgnesPanel must render from real project/clip data"
        )

    def test_synthesize_wired_to_real_action(self) -> None:
        panel = _read(PANEL)
        assert "regenerateClip" in panel, (
            "the Synthesize action must call the real regenerateClip store action"
        )

    def test_no_fabricated_telemetry(self) -> None:
        panel = _read(PANEL)
        assert "Math.random" not in panel, "AgnesPanel must not simulate values"
        assert "PREVIEW" not in panel, "AgnesPanel must not carry the mock control-strip object"
        assert "1.8k GPU" not in panel, "AgnesPanel must not fabricate a GPU metric"

    def test_honest_results_grid(self) -> None:
        panel = _read(PANEL)
        assert "not generated" in panel or "No result" in panel, (
            "the 2x2 results grid must label un-generated variants honestly"
        )

    def test_honest_empty_state(self) -> None:
        panel = _read(PANEL)
        assert "Select a clip" in panel or "No project" in panel, (
            "AgnesPanel must have an honest standby/empty state"
        )

    def test_no_noop_handlers(self) -> None:
        panel = _read(PANEL)
        assert "onClick={() => {}}" not in panel and "onClick={() => undefined}" not in panel, (
            "AgnesPanel must not wire no-op click handlers"
        )
