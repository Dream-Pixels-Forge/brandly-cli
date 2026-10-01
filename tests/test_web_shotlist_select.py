"""Contract tests for Shot List bulk selection (Paper design §7, artboard 02).

RED test: the frozen design requires a checkbox on every shot row plus a
contextual Selection Bar (count + bulk actions) driven by store state.

Source-level contract (repo convention, see test_web_panels_wired.py / #61).
"""

from __future__ import annotations

from pathlib import Path

WEB_SRC = Path(__file__).resolve().parent.parent / "web" / "src"


def _read(name: str) -> str:
    return (WEB_SRC / name).read_text(encoding="utf-8")


class TestSelectionState:
    def test_store_exposes_multi_selection_state(self) -> None:
        store = _read("store.ts")
        assert "selectedClipIds" in store, (
            "store.ts has no multi-selection state for bulk actions"
        )

    def test_store_exposes_selection_actions(self) -> None:
        store = _read("store.ts")
        for action in ("toggleClipSelected", "clearSelection"):
            assert action in store, f"store.ts is missing selection action `{action}`"


class TestShotListBulkUi:
    def test_shot_list_renders_row_checkbox(self) -> None:
        panel = _read("components/panels/ShotListPanel.tsx")
        assert "toggleClipSelected" in panel, (
            "ShotListPanel.tsx rows are not wired to multi-selection"
        )

    def test_shot_list_renders_selection_bar(self) -> None:
        panel = _read("components/panels/ShotListPanel.tsx")
        assert "Selection Bar" in panel, (
            "ShotListPanel.tsx missing the contextual Selection Bar (design §7)"
        )

    def test_selection_bar_reports_count_and_actions(self) -> None:
        panel = _read("components/panels/ShotListPanel.tsx")
        assert "selectedClipIds.length" in panel, (
            "Selection Bar does not report the selection count"
        )
