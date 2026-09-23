"""Contract tests for issue #59: every sidebar panel renders a real component.

RED test: Shell.tsx mapped 6 of 8 panels to demo Placeholder stubs while
real panel components exist on disk. These tests pin the wiring contract
at the source level (no JS test runner in CI yet — see #61).
"""

from __future__ import annotations

import re
from pathlib import Path

WEB_SRC = Path(__file__).resolve().parent.parent / "web" / "src"

# panel kind -> real component file that must back it
PANEL_WIRING: dict[str, str] = {
    "timeline": "TimelinePanel",
    "asset_manifest": "ShotListPanel",
    "props": "PropsInspectorPanel",
    "color": "ColorGradingPanel",
    "audio": "AudioMixerPanel",
    "render": "RenderDispatchPanel",
}


def _shell() -> str:
    return (WEB_SRC / "Shell.tsx").read_text(encoding="utf-8")


class TestRealPanelsWired:
    def test_no_placeholder_stubs_for_real_panels(self) -> None:
        shell = _shell()
        for kind in PANEL_WIRING:
            stub = re.search(rf"{kind}:\s*\(\)\s*=>\s*<\w*Placeholder", shell)
            assert stub is None, (
                f"Shell.tsx panel '{kind}' still renders a demo Placeholder (issue #59)"
            )

    def test_each_real_panel_imported_and_mapped(self) -> None:
        shell = _shell()
        for kind, component in PANEL_WIRING.items():
            assert component in shell, (
                f"Shell.tsx does not reference real component {component} "
                f"for panel '{kind}' (issue #59)"
            )

    def test_real_panel_files_exist(self) -> None:
        missing = [
            c
            for c in set(PANEL_WIRING.values())
            if not (WEB_SRC / "components" / "panels" / f"{c}.tsx").exists()
            and not (WEB_SRC / "components" / "timeline" / f"{c}.tsx").exists()
        ]
        assert not missing, f"Real panel files missing: {missing}"
