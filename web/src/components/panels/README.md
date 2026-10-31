# panels

## Overview
Studio panel components for editing and monitoring.

## Interface
- AgnesPanel.tsx, AudioMixerPanel.tsx, ClipInspectorPanel.tsx, ColorGradingPanel.tsx, PhaseStepper.tsx, PipelineStepper.tsx, PreviewPanel.tsx, ProductionMonitorPanel.tsx, PropsInspectorPanel.tsx, RenderDispatchPanel.tsx, ReviewQueuePanel.tsx, ShotListPanel.tsx, TransportControls.tsx

## Invariants
- Panels are presentational
- State lifted to Shell

## Side Effects
- Dispatch actions to backend

## Verification
- Run: `npm --prefix web run lint`
