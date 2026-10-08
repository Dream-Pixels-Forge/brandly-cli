"""P6 (#253 close-out): the remaining web data-honesty contract tests.

RED-first source-contract tests for the #253 findings that survived the P1
fix (the CFG->volume data bug, the no-op M/S buttons, the fabricated seed /
checkbox values are already fixed and pinned by the earlier contract tests):

- #4: the "Update Shot Props (Hot Reload)" footer button writes the current
  field values back to themselves (every field already persists via
  ``onChange`` -> PATCH) — a no-op action, banned by the data-honesty
  convention
- #6: the command search is a decorative ``div`` carrying an unimplemented
  ``Cmd+K`` badge — it must be honestly labelled non-interactive instead
- #7: the "?" help button is a dead clickable (no ``onClick``, no
  ``disabled``) — it must be ``disabled`` with an honest title
- #8: the AudioMixerPanel fabricates a "De-esser engaged · 6kHz shelf
  -2.4dB" state the store does not have
"""

from __future__ import annotations

from pathlib import Path

WEB_SRC = Path(__file__).resolve().parent.parent / "web" / "src"


def _read(name: str) -> str:
    return (WEB_SRC / name).read_text(encoding="utf-8")


class TestPropsInspectorHonesty:
    def test_no_noop_write_back_footer(self) -> None:
        """#4: no button writes the current values back to themselves."""
        panel = _read("components/panels/PropsInspectorPanel.tsx")
        assert "prompt: clip.prompt" not in panel, (
            "the footer write-back is a no-op — every field already persists "
            "via onChange -> PATCH"
        )

    def test_no_dead_help_button(self) -> None:
        """#7: the "?" help button is disabled with an honest title."""
        toolbar = _read("Toolbar.tsx")
        assert 'title="Keyboard shortcuts"' not in toolbar, (
            "the dead help button must be disabled with an honest title, "
            "not a dead clickable"
        )

    def test_no_unimplemented_cmdk_badge(self) -> None:
        """#6: no unimplemented Cmd+K badge on the decorative search div."""
        toolbar = _read("Toolbar.tsx")
        assert "⌘K" not in toolbar, (
            "the Cmd+K badge promises an unimplemented shortcut — remove it "
            "until search is real"
        )

    def test_search_labelled_non_interactive(self) -> None:
        """#6: the search affordance is honestly labelled non-interactive."""
        toolbar = _read("Toolbar.tsx")
        assert "not interactive" in toolbar.lower() or "not implemented" in toolbar.lower(), (
            "the search div must carry an honest non-interactive label"
        )


class TestAudioMixerHonesty253:
    def test_no_fabricated_deesser_state(self) -> None:
        """#8: no fabricated de-esser/EQ telemetry the store does not have."""
        panel = _read("components/panels/AudioMixerPanel.tsx")
        assert "6kHz shelf" not in panel, (
            "the panel fabricates de-esser state the store does not have"
        )
        assert "De-esser engaged" not in panel, (
            "the panel claims an engaged de-esser that is not implemented"
        )
