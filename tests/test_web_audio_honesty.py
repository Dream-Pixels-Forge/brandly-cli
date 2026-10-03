"""Contract tests: the Audio Mixer must not fabricate telemetry.

RED test: the panel simulated its VU meter with a ``setInterval`` +
``Math.random`` idle loop and hardcoded a ``-3.2`` dB peak, and its
"Audition Voice" button was a no-op that re-saved the unchanged clip prompt.
Both violate the data-honesty rule (DESIGN-STUDIO-SHELL.md §5).
"""

from __future__ import annotations

from pathlib import Path

WEB_SRC = Path(__file__).resolve().parent.parent / "web" / "src"
PANEL = "components/panels/AudioMixerPanel.tsx"


def _read(name: str) -> str:
    return (WEB_SRC / name).read_text(encoding="utf-8")


class TestAudioMixerHonesty:
    def test_no_simulated_vu(self) -> None:
        panel = _read(PANEL)
        assert "Math.random" not in panel, "the VU meter must not be simulated with random values"
        assert "setInterval" not in panel, "no idle metering loop"

    def test_vu_labelled_honest_idle(self) -> None:
        panel = _read(PANEL)
        assert "No live metering" in panel, "the VU section must be labelled honest (no simulated levels)"

    def test_no_noop_audition(self) -> None:
        panel = _read(PANEL)
        assert "updateClip(clip.id, { prompt: clip.prompt })" not in panel, "no no-op save actions"

    def test_audition_carries_honest_title(self) -> None:
        panel = _read(PANEL)
        assert "No audio audition endpoint" in panel, "the Audition action must carry an honest disabled title"
