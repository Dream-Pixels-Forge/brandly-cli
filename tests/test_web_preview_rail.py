"""Contract tests for the Preview screen (Paper design §7, artboard 01).

RED test: the frozen design requires (a) the transport controls to become an
overlay *inside* the video frame, and (b) a 300px Clip Inspector rail beside
the viewport — the dead space each side of the 16:9 frame.

Source-level contract (repo convention, see test_web_panels_wired.py / #61).
"""

from __future__ import annotations

from pathlib import Path

WEB_SRC = Path(__file__).resolve().parent.parent / "web" / "src"


def _read(name: str) -> str:
    return (WEB_SRC / name).read_text(encoding="utf-8")


class TestClipInspectorRail:
    def test_clip_inspector_component_exists(self) -> None:
        path = WEB_SRC / "components" / "panels" / "ClipInspectorPanel.tsx"
        assert path.is_file(), (
            "ClipInspectorPanel.tsx missing — design requires a 300px Clip "
            "Inspector rail beside the viewport"
        )

    def test_shell_renders_clip_inspector_with_preview(self) -> None:
        shell = _read("Shell.tsx")
        assert "ClipInspectorPanel" in shell, (
            "Shell.tsx does not render ClipInspectorPanel for the preview panel"
        )

    def test_preview_workspace_rail_layout_defined(self) -> None:
        css = (WEB_SRC / "Shell.css").read_text(encoding="utf-8")
        assert ".preview-workspace" in css, (
            "Shell.css missing .preview-workspace rail layout (viewport + 300px rail)"
        )
        assert "300px" in css, "Clip Inspector rail must be 300px wide per design §7"


class TestTransportOverlay:
    def test_transport_controls_support_overlay_mode(self) -> None:
        transport = _read("components/panels/TransportControls.tsx")
        assert "overlay" in transport, (
            "TransportControls.tsx has no `overlay` prop — design moves the "
            "transport into the video frame as an overlay"
        )

    def test_preview_renders_transport_as_overlay(self) -> None:
        preview = _read("components/panels/PreviewPanel.tsx")
        assert "<TransportControls" in preview, (
            "PreviewPanel.tsx no longer renders transport controls"
        )
        assert "overlay" in preview, (
            "PreviewPanel.tsx renders the transport as a separate row instead of "
            "the in-frame overlay required by design §7"
        )
