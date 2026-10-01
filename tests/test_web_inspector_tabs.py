"""Contract tests for the Shot Inspector tabs (Paper design §7, artboard 02).

RED test: the frozen design requires the inspector beside the Shot List to
expose Overview / Prompt / Gate tabs rather than one undifferentiated scroll.

Source-level contract (repo convention, see test_web_panels_wired.py / #61).
"""

from __future__ import annotations

from pathlib import Path

WEB_SRC = Path(__file__).resolve().parent.parent / "web" / "src"


def _read(rel: str) -> str:
    return (WEB_SRC / rel).read_text(encoding="utf-8")


class TestInspectorTabs:
    def test_clip_inspector_exposes_tabs(self) -> None:
        panel = _read("components/panels/ClipInspectorPanel.tsx")
        for tab in ("Overview", "Prompt", "Gate"):
            assert tab in panel, f"ClipInspectorPanel.tsx is missing the '{tab}' tab"

    def test_clip_inspector_tab_is_stateful(self) -> None:
        panel = _read("components/panels/ClipInspectorPanel.tsx")
        assert "useState" in panel, (
            "ClipInspectorPanel.tsx tabs are not interactive (no tab state)"
        )

    def test_shell_renders_the_rail_beside_the_shot_list(self) -> None:
        shell = _read("Shell.tsx")
        assert "shot-workspace" in shell, (
            "Shell.tsx does not wrap the Shot List in a workspace row with the "
            "Clip Inspector rail (design §7, artboard 02)"
        )

    def test_gate_tab_does_not_fabricate_scores(self) -> None:
        panel = _read("components/panels/ClipInspectorPanel.tsx")
        # The store carries no per-clip gate score — the Gate tab must say so
        # rather than invent one.
        assert "no gate score" in panel.lower() or "monitor" in panel.lower(), (
            "Gate tab must disclose that gate scores are not available from the "
            "clip record (data honesty)"
        )
