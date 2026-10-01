"""Contract tests for the Brandly Studio shell (Paper design, artboards 01-04).

RED test: the frozen design in ``dev-notes/DESIGN-STUDIO-SHELL.md`` requires a
Toolbar + Status Bar shell, a restructured sidebar (no telemetry block, footer
CTA, shortcut hints), and the design tokens that the components already
*reference* but which were never defined.

These pin the contract at the source level, matching the established repo
convention (see ``test_web_panels_wired.py`` / ``test_web_shell_boot.py``:
"no JS test runner in CI yet — see #61").
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
WEB_SRC = WEB / "src"

# Shortcut keys required by the design (P/T/A/I/R/M/Q/G).
SHORTCUT_KEYS = ["P", "T", "A", "I", "R", "M", "Q", "G"]

# Tokens the components reference but which must be *defined* in :root.
REQUIRED_TOKENS = [
    "--md-radius-sm",
    "--md-radius-md",
    "--md-radius-lg",
    "--md-transition-fast",
    "--md-font-display-lg",
    "--md-font-code-inline",
    "--md-font-body-md",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestShellLayout:
    """The shell must compose Header + Toolbar + Body + Status Bar."""

    def test_toolbar_component_exists(self) -> None:
        assert (WEB_SRC / "Toolbar.tsx").is_file(), (
            "web/src/Toolbar.tsx missing — design requires a 40px context toolbar"
        )

    def test_status_bar_component_exists(self) -> None:
        assert (WEB_SRC / "StatusBar.tsx").is_file(), (
            "web/src/StatusBar.tsx missing — design requires a 28px status bar"
        )

    def test_shell_renders_toolbar_and_status_bar(self) -> None:
        shell = _read(WEB_SRC / "Shell.tsx")
        assert "Toolbar" in shell, "Shell.tsx does not render <Toolbar />"
        assert "StatusBar" in shell, "Shell.tsx does not render <StatusBar />"

    def test_shell_preserves_boot_contract(self) -> None:
        # Guard against regression of test_web_shell_boot.py (issue #58).
        assert "fetchProjects" in _read(WEB_SRC / "Shell.tsx")

    def test_main_uses_design_grid(self) -> None:
        css = _read(WEB_SRC / "Shell.css")
        assert "14px" in css, "Shell.css main padding must be 14px per design"


class TestSidebarRestructure:
    """Telemetry leaves the sidebar; footer CTA + shortcut hints arrive."""

    def test_engine_status_telemetry_removed(self) -> None:
        sidebar = _read(WEB_SRC / "SidebarNav.tsx")
        assert "Engine Status" not in sidebar, (
            "SidebarNav.tsx still renders the Engine Status telemetry block — "
            "the design moves it to the Status Bar"
        )

    def test_sidebar_footer_cta_present(self) -> None:
        sidebar = _read(WEB_SRC / "SidebarNav.tsx")
        assert "New Project" in sidebar, (
            "SidebarNav.tsx has no footer 'New Project' CTA (design footer)"
        )

    def test_shortcut_hints_defined_for_every_panel(self) -> None:
        # The keys are defined once in panelLabels.ts (single source of truth)
        # so the nav and any future shortcut help agree.
        labels = _read(WEB_SRC / "panelLabels.ts")
        missing = [k for k in SHORTCUT_KEYS if f"'{k}'" not in labels and f'"{k}"' not in labels]
        assert not missing, f"panelLabels.ts is missing shortcut keys: {missing}"

    def test_sidebar_renders_shortcut_chips(self) -> None:
        sidebar = _read(WEB_SRC / "SidebarNav.tsx")
        assert "PANEL_SHORTCUTS" in sidebar, "SidebarNav.tsx no longer binds shortcut keys"
        assert "{p.key}" in sidebar, (
            "SidebarNav.tsx nav rows do not render the shortcut chip"
        )

    def test_sidebar_keeps_loading_and_error_surfacing(self) -> None:
        # Guard against regression of test_web_shell_boot.py (issue #58).
        sidebar = _read(WEB_SRC / "SidebarNav.tsx")
        assert "loading" in sidebar and "error" in sidebar


class TestDesignTokensDefined:
    """Tokens referenced across the app must actually be defined."""

    def test_index_html_defines_missing_tokens(self) -> None:
        html = _read(WEB / "index.html")
        missing = [t for t in REQUIRED_TOKENS if f"{t}:" not in html]
        assert not missing, (
            f"web/index.html :root is missing token definitions: {missing} "
            "(referenced by components, currently falling back to browser defaults)"
        )
