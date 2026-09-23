"""Contract tests for issue #58: Shell must boot with project data.

RED test: the studio SPA mounts with an empty project list because
``fetchProjects()`` is never called from any component. These tests pin
the boot contract at the source level (the repo has no JS test runner
wired into CI yet — see #61):

1. ``Shell.tsx`` must reference ``fetchProjects`` (mount effect).
2. ``SidebarNav.tsx`` must surface ``loading`` and ``error`` states
   (the store already exposes both; the sidebar must consume them).
"""

from __future__ import annotations

from pathlib import Path

WEB_SRC = Path(__file__).resolve().parent.parent / "web" / "src"


def _read(name: str) -> str:
    return (WEB_SRC / name).read_text(encoding="utf-8")


class TestShellBootContract:
    def test_shell_calls_fetch_projects_on_mount(self) -> None:
        shell = _read("Shell.tsx")
        assert "fetchProjects" in shell, (
            "Shell.tsx never calls fetchProjects() — the sidebar "
            "mounts with an empty project list (issue #58)"
        )

    def test_sidebar_surfaces_loading_state(self) -> None:
        sidebar = _read("SidebarNav.tsx")
        assert "loading" in sidebar, (
            "SidebarNav.tsx ignores store.loading — no boot feedback (issue #58)"
        )

    def test_sidebar_surfaces_error_state(self) -> None:
        sidebar = _read("SidebarNav.tsx")
        assert "error" in sidebar, (
            "SidebarNav.tsx ignores store.error — boot failures are silent (issue #58)"
        )
