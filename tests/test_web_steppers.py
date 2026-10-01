"""Contract tests for the Render/Monitor steppers (Paper design §7, artboards 03-04).

RED test: the frozen design requires a PipelineStepper on the Render panel, a
Director PhaseStepper on the Production Monitor panel, and a 440px settings
column so the render controls do not stretch full-bleed.

Source-level contract (repo convention, see test_web_panels_wired.py / #61).
"""

from __future__ import annotations

from pathlib import Path

WEB_SRC = Path(__file__).resolve().parent.parent / "web" / "src"


def _read(rel: str) -> str:
    return (WEB_SRC / rel).read_text(encoding="utf-8")


class TestSteppers:
    def test_pipeline_stepper_component_exists(self) -> None:
        path = WEB_SRC / "components" / "panels" / "PipelineStepper.tsx"
        assert path.is_file(), (
            "PipelineStepper.tsx missing — design §7 requires it on the Render panel"
        )

    def test_phase_stepper_component_exists(self) -> None:
        path = WEB_SRC / "components" / "panels" / "PhaseStepper.tsx"
        assert path.is_file(), (
            "PhaseStepper.tsx missing — design §7 requires it on the Production Monitor"
        )

    def test_render_panel_renders_pipeline_stepper(self) -> None:
        panel = _read("components/panels/RenderDispatchPanel.tsx")
        assert "PipelineStepper" in panel, (
            "RenderDispatchPanel.tsx does not render <PipelineStepper />"
        )

    def test_monitor_panel_renders_phase_stepper(self) -> None:
        panel = _read("components/panels/ProductionMonitorPanel.tsx")
        assert "PhaseStepper" in panel, (
            "ProductionMonitorPanel.tsx does not render <PhaseStepper />"
        )

    def test_render_settings_column_constrained(self) -> None:
        panel = _read("components/panels/RenderDispatchPanel.tsx")
        assert "440" in panel, (
            "RenderDispatchPanel.tsx does not constrain its settings column "
            "to 440px (design §7, artboard 03)"
        )

    def test_steppers_do_not_fabricate_state(self) -> None:
        # Data honesty: steppers must read real store state, never invent it.
        pipeline = _read("components/panels/PipelineStepper.tsx")
        assert "exportDone" in pipeline or "useAppStore" in pipeline, (
            "PipelineStepper must derive its state from the store"
        )
        phase = _read("components/panels/PhaseStepper.tsx")
        assert "current_phase" in phase or "useAppStore" in phase, (
            "PhaseStepper must derive its state from the store"
        )
